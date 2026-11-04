"""Tests for the experimental canonicalization reference profile."""
from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from tests.support.payload_canonicalization_reference import (
    CanonicalizationError,
    canonicalize_envelope,
    parse_strict_json,
    payload_sha256,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "payload-canonicalization-vectors.json"


class PayloadCanonicalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(FIXTURE.read_text(encoding="utf-8"))["vectors"]

    def test_golden_vectors_match_bytes_and_sha256(self) -> None:
        for vector in self.vectors:
            with self.subTest(vector=vector["id"]):
                actual = canonicalize_envelope(vector["input"])
                self.assertEqual(actual.decode("utf-8"), vector["canonical_utf8"])
                self.assertEqual(hashlib.sha256(actual).hexdigest(), vector["sha256"])
                self.assertEqual(payload_sha256(vector["input"]), vector["sha256"])

    def test_object_key_order_does_not_change_canonical_bytes(self) -> None:
        original = self.vectors[0]["input"]
        reordered = {
            "payload_schema_version": original["payload_schema_version"],
            "payload": {"feedrate_um_s": 50000},
            "operation": original["operation"],
            "interface_version": original["interface_version"],
            "canonicalization_profile": original["canonicalization_profile"],
            "payload_schema_id": original["payload_schema_id"],
        }
        self.assertEqual(canonicalize_envelope(original), canonicalize_envelope(reordered))

    def test_array_order_remains_significant(self) -> None:
        envelope = dict(self.vectors[0]["input"])
        envelope["payload"] = {"sequence": [1, 2, 3]}
        reversed_envelope = dict(envelope)
        reversed_envelope["payload"] = {"sequence": [3, 2, 1]}
        self.assertNotEqual(
            canonicalize_envelope(envelope),
            canonicalize_envelope(reversed_envelope),
        )

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaises(CanonicalizationError):
            parse_strict_json('{"operation":"A","operation":"B"}')

    def test_floats_and_non_finite_numbers_are_rejected(self) -> None:
        envelope = dict(self.vectors[0]["input"])
        envelope["payload"] = {"value": 1.25}
        with self.assertRaises(CanonicalizationError):
            canonicalize_envelope(envelope)
        with self.assertRaises(CanonicalizationError):
            parse_strict_json('{"value":NaN}')

    def test_unknown_or_missing_envelope_fields_are_rejected(self) -> None:
        envelope = dict(self.vectors[0]["input"])
        envelope["unversioned_extra"] = 1
        with self.assertRaises(CanonicalizationError):
            canonicalize_envelope(envelope)


if __name__ == "__main__":
    unittest.main()
