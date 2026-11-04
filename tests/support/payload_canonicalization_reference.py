"""Experimental reference canonicalizer for test vectors only.

This is NOT the printer's production protocol implementation.
Profile: json-int-prototype-0.1
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


PROFILE = "json-int-prototype-0.1"
REQUIRED_ENVELOPE_KEYS = {
    "canonicalization_profile",
    "interface_version",
    "operation",
    "payload",
    "payload_schema_id",
    "payload_schema_version",
}


class CanonicalizationError(ValueError):
    """Input cannot be represented unambiguously by this test profile."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalizationError(f"duplicate object key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise CanonicalizationError(f"non-JSON numeric constant: {value}")


def parse_strict_json(raw: str) -> Any:
    """Parse JSON while rejecting duplicate keys and NaN/Infinity tokens."""
    try:
        return json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except CanonicalizationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CanonicalizationError(str(exc)) from exc


def _validate_value(value: Any, path: str = "$") -> None:
    # bool must be checked before int because bool subclasses int in Python.
    if value is None or isinstance(value, (str, bool)):
        if isinstance(value, str):
            try:
                value.encode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise CanonicalizationError(f"invalid Unicode string at {path}") from exc
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalizationError(f"floating-point value forbidden by {PROFILE}: {path}")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError(f"non-string object key at {path}")
            _validate_value(key, f"{path}.<key>")
            _validate_value(item, f"{path}.{key}")
        return
    raise CanonicalizationError(f"unsupported value type at {path}: {type(value).__name__}")


def canonicalize_envelope(envelope: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 bytes for the explicitly versioned test profile."""
    if not isinstance(envelope, dict):
        raise CanonicalizationError("envelope must be an object")
    keys = set(envelope)
    if keys != REQUIRED_ENVELOPE_KEYS:
        missing = sorted(REQUIRED_ENVELOPE_KEYS - keys)
        extra = sorted(keys - REQUIRED_ENVELOPE_KEYS)
        raise CanonicalizationError(f"envelope key mismatch; missing={missing}, extra={extra}")
    if envelope["canonicalization_profile"] != PROFILE:
        raise CanonicalizationError("unsupported canonicalization profile")
    for field in (
        "interface_version",
        "operation",
        "payload_schema_id",
        "payload_schema_version",
    ):
        if not isinstance(envelope[field], str) or not envelope[field]:
            raise CanonicalizationError(f"{field} must be a non-empty string")
    if not isinstance(envelope["payload"], dict):
        raise CanonicalizationError("payload must be an object")

    _validate_value(envelope)
    try:
        return json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise CanonicalizationError(str(exc)) from exc


def payload_sha256(envelope: dict[str, Any]) -> str:
    return hashlib.sha256(canonicalize_envelope(envelope)).hexdigest()
