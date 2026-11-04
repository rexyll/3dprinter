# 任务状态机测试规格（SIL）

- **状态**：测试设计规格；尚未实现测试代码、执行测试或产生运行报告
- **版本**：0.1
- **日期**：2026-11-04
- **关联任务**：01-03
- **状态契约**：[任务状态转换契约](../architecture/task-state-transition-contract.md)
- **需求依据**：[系统需求规格](../requirements/system-requirements.md) SYS-009、SYS-013、SYS-014；SIL-008、SIL-009、SIL-010
- **接口依据**：[接口控制文档](../architecture/interface-control.md)

## 1. 目的与范围

把 STM-NEG-001 至 STM-NEG-028 转成可直接映射到自动化测试框架的用例规格，并通过 STM-POS-001 至 STM-POS-012 补足合法流程与恢复路径。请求载荷规范化、摘要与幂等身份规则见[请求载荷规范化文档](../architecture/request-payload-canonicalization.md)。每个用例均规定前置状态、输入事件序列、预期状态、结果/诊断及副作用断言。

本文件是测试设计，不代表测试代码已存在或用例已通过。它只验证逻辑状态和虚拟输出事件；不能证明真实电机、加热器、驱动器或断连后的物理设备已进入安全状态。

## 2. 通用测试夹具

### 2.1 最小夹具

每个测试实例至少提供以下可控对象：

| 对象 | 必需能力 |
|---|---|
| Connection fixture | 设置连接状态、当前 session_id、会话代际及同步完成标志 |
| Job fixture | 建立指定 task_id 和初始 Job State；读取当前状态及活动任务 |
| Event injector | 按指定顺序注入请求、设备确认、故障、遥测和通信事件；支持重复、乱序、延迟及旧会话事件 |
| Request ledger | 记录 request_id、correlation_id、session_id、task_id、接受/执行结果及 Unknown 状态 |
| Diagnostic sink | 捕获拒绝结果、协议错误、非法转换、过期事件和重新同步请求 |
| Side-effect recorder | 记录运动使能/步进、挤出、加热使能/功率请求等虚拟输出命令；区分“请求发出”与“模型输出变化” |
| Clock / sequence source | 提供可控逻辑顺序或单调序号；不依赖墙钟精度或未批准的超时常数 |

### 2.2 标准事件记录

测试适配器应将输入/输出归一化为以下逻辑记录。字段可映射到未来协议，不要求当前实现采用相同 JSON 或线上编码。

```json
{
  "event_id": "test-local-unique-id",
  "event_type": "StartRequested",
  "session_id": "session-generation-id",
  "task_id": "job-id-or-null",
  "request_id": "request-id-or-null",
  "correlation_id": "correlation-id-or-null",
  "sequence": 1,
  "source": "HOST|TASK|COMM|SAFETY|VDEV",
  "logical_time": 0,
  "payload": {},
  "device_confirmed": false
}
```

约束：
- `event_id` 在单次测试记录中唯一；`sequence` 的作用域由夹具显式配置，不假定跨会话全局单调。
- 旧会话/旧任务事件必须保留其原始标识，不得在注入时改写成当前标识。
- `device_confirmed` 仅表示测试事件来源/语义明确为设备侧确认；主机本地发送成功不能伪装为设备确认。
- `logical_time` 用于可重复排序，不可据此推断跨时钟域的物理时间。
- 空值、缺失字段、未知枚举和非法边均应作为可注入输入。

### 2.3 每个用例的公共断言

除用例另有说明外，执行后均检查：
1. 当前连接状态与 Job State 符合用例预期，连接状态不得被隐式合并进 Job State。
2. 活动 task_id 不被旧任务或未授权事件替换。
3. 所有拒绝/诊断可关联到适用的 session_id、task_id、request_id 或 event_id。
4. 不出现未被授权的运动、挤出或加热副作用事件。
5. 事件日志可还原输入顺序、处理结果及状态变化；测试失败时输出实际/期望差异。

## 3. 负向测试用例

### STM-NEG-001：Idle 状态下控制请求拒绝

- **目的/关联**：验证无活动作业时不能暂停、恢复或取消；SYS-009。
- **前置条件**：连接状态为 Connected；Job State 为 Idle；无活动 task_id；虚拟输出初始记录已清空。
- **事件序列**：依次发送 Pause、Resume、Cancel 请求；每个请求使用独立 request_id。
- **预期状态**：始终为 Idle；连接状态不变。
- **结果/诊断**：每个请求返回 INVALID_STATE 或接口定义的等价明确拒绝，且可关联各自 request_id。
- **副作用断言**：无运动、挤出、加热输出请求；无任务被创建。

### STM-NEG-002：校验失败后不得启动

- **目的/关联**：验证 ValidationFailed 不能绕过校验进入 Running；SYS-009。
- **前置条件**：Connected；建立 task_id=T1；Job State 为 Validating；夹具配置作业校验失败。
- **事件序列**：注入 ValidationFailed(T1)；随后对 T1 注入 Start。
- **预期状态**：校验失败后活动 Job State 回到 Idle，T1 仅保留为拒绝/失败记录；后续 Start 不得进入 Running。
- **结果/诊断**：ValidationFailed 结果记录具体失败类别；对已关闭/无效 T1 的 Start 明确拒绝。
- **副作用断言**：不产生 T1 的运动、挤出或加热输出。

### STM-NEG-003：Ready 状态下未显式 Start 的执行事件

- **目的/关联**：验证校验通过不等于获准执行；SYS-009。
- **前置条件**：Connected；task_id=T1；Job State 为 Ready；无 Start 请求或确认。
- **事件序列**：直接注入属于 T1 的 MotionStep/ExtrusionStep 执行事件。
- **预期状态**：不得进入 Running；保持 Ready，或按已定义的协议错误策略进入 Fault（若该输入被判定为致命）。
- **结果/诊断**：记录未授权执行事件及其来源；不得静默接受。
- **副作用断言**：虚拟运动/挤出输出记录无新增动作。

### STM-NEG-004：Running 状态下重复 Pause

- **目的/关联**：验证重复控制请求不会造成重复副作用；SYS-009。
- **前置条件**：Connected；T1 为 Running；尚未进入 Pausing；无已生效暂停。
- **事件序列**：发送 Pause(request=P1)，随后在 P1 仍未完成时再次发送 Pause(request=P2)；再注入一次重复 P1。
- **预期状态**：最多存在一个有效暂停流程；不得因重复请求重复进入暂停副作用或生成多个互相冲突的暂停上下文。
- **结果/诊断**：P2 和重复 P1 按接口幂等策略返回原结果、明确拒绝或显式去重结果；不得静默重复执行。具体返回策略待协议冻结。
- **副作用断言**：暂停生效动作至多发生一次；无重复运动/挤出/加热控制副作用。

### STM-NEG-005：缺少 PauseEffective 却报告 Paused

- **目的/关联**：验证请求接受不能冒充暂停完成；SYS-009。
- **前置条件**：Connected；T1 已由 Running 接受 Pause 并处于 Pausing；尚未收到 PauseEffective。
- **事件序列**：注入设备状态事件 Paused(T1)，但不注入 PauseEffective。
- **预期状态**：不得进入 Paused；保持 Pausing，或按非法设备事件策略进入 Fault。
- **结果/诊断**：记录非法状态边/协议不一致；触发规定的拒绝或重新同步流程。
- **副作用断言**：不得把该事件当作暂停安全点证据；不得据此恢复队列或报告已暂停。

### STM-NEG-006：故障锁存期间从 Paused 恢复

- **目的/关联**：验证 Fault 锁存优先于 Resume；SYS-014。
- **前置条件**：T1 为 Paused；Safety fixture 准备一个仍存在的致命故障源。
- **事件序列**：先注入 FatalFault，使 Job State 按状态契约转为 Fault 并保留 prior_state=Paused 的诊断上下文；再发送 Resume(T1)。
- **预期状态**：保持 Fault 锁存；不得进入 Running。
- **结果/诊断**：返回故障拒绝并关联故障标识。
- **副作用断言**：无运动、挤出或加热使能请求。

### STM-NEG-007：缺少 CancelEffective 却报告 Cancelled

- **目的/关联**：验证取消请求接受不等于取消完成；SYS-009。
- **前置条件**：Connected；T1 为 Cancelling；尚未满足停止条件/队列处置条件；未收到 CancelEffective。
- **事件序列**：注入设备状态事件 Cancelled(T1)，但不注入 CancelEffective。
- **预期状态**：不得进入 Cancelled；保持 Cancelling，或按非法状态事件策略进入 Fault。
- **结果/诊断**：记录非法状态边；取消结果不得报告成功。
- **副作用断言**：不得把未确认停止当作停止完成；不得启动新任务。

### STM-NEG-008：仅发送/排队完成不得报告 Completed

- **目的/关联**：验证 Completed 必须依赖设备侧执行完成证据；SYS-009。
- **前置条件**：Connected；T1 为 Running；作业包含至少一个尚无设备完成确认的动作。
- **事件序列**：将主机发送计数/固件接收计数/队列提交计数推进至总量；不注入动作执行完成确认；尝试注入 Completed。
- **预期状态**：不得进入 Completed；保持 Running，或在确认设备报告矛盾事实时进入 Fault/重新同步路径。
- **结果/诊断**：Completed 报告被拒绝或标记为未验证；指出缺少执行完成证据。
- **副作用断言**：不产生“任务已完成”业务事件；不得仅因发送/排队计数清零而允许终态后续操作。

### STM-NEG-009：Fault 状态拒绝所有危险动作

- **目的/关联**：验证故障锁存期间禁止新运动/加热动作；SYS-014、SIL-010。
- **前置条件**：Safety fixture 锁存致命故障；Job State 为 Fault；虚拟输出事件记录已清空。
- **事件序列**：分别发送 Start、Resume、运动、挤出、加热请求。
- **预期状态**：故障保持锁存；Job State 不进入 Running 或其他可执行状态。
- **结果/诊断**：每个请求均返回故障拒绝并可关联故障源。
- **副作用断言**：不出现新的运动/挤出/加热使能或增功率请求。故障输出应达到何种具体安全值由 01-05 安全概念定义，本用例不虚构数值或物理安全结论。

### STM-NEG-010：普通重连/刷新不得清除故障

- **目的/关联**：验证故障只能通过显式复位流程退出；SYS-014。
- **前置条件**：Fault 已锁存；故障源仍存在；记录当前 fault_id。
- **事件序列**：模拟连接丢失；建立新 session 并完成普通能力/状态刷新；注入普通遥测更新。
- **预期状态**：故障仍锁存；Job State 不因重连或遥测刷新回到 Idle/Ready/Running。
- **结果/诊断**：故障标识与原因继续可读；任何隐式清除企图均被记录。
- **副作用断言**：无危险动作输出；没有 ClearFaultAndReset 事件时不得产生复位副作用。

### STM-NEG-011：旧 session 迟到成功响应不得覆盖新会话

- **目的/关联**：验证会话代际隔离；SYS-013。
- **前置条件**：旧会话 S1 有未决请求 R1；连接丢失后建立新会话 S2；S2 已完成同步并建立当前权威状态快照。
- **事件序列**：先记录 S2 当前状态；再注入 S1 对 R1 的迟到成功响应（包括成功确认和状态快照变更）。
- **预期状态**：S2 当前连接/任务状态保持不变；R1 仍按旧会话归档或标记为旧会话结果，不得映射成 S2 的成功结果。
- **结果/诊断**：记录 stale-session 事件及其原 session_id；必要时触发诊断，不得把旧事件静默改写。
- **副作用断言**：旧响应不触发新会话的运动/挤出/加热输出。

### STM-NEG-012：旧 task_id 终态事件不得改变新任务

- **目的/关联**：验证任务代际隔离；SYS-009、SYS-013。
- **前置条件**：T1 已终结；当前活动任务为 T2，且 T2 处于 Running 或测试指定的非终态。
- **事件序列**：注入旧 T1 的 Completed、Cancelled 事件；再注入 T1 的进度/故障关联事件。
- **预期状态**：T2 状态、进度及活动 task_id 均保持不变。
- **结果/诊断**：旧任务事件归档至 T1 或拒绝；不得关联到 T2。
- **副作用断言**：旧任务事件不触发 T2 的运动/挤出/加热控制。

### STM-NEG-013：ConnectionLost 时本地发送成功不得视为设备接受

- **目的/关联**：验证未知执行结果语义；SYS-013、SIL-009。
- **前置条件**：Connected；准备一个具有潜在非幂等副作用的请求 R1；测试传输适配器可区分本地写入完成与设备确认。
- **事件序列**：本地发送 R1 成功；在收到设备确认前注入 ConnectionLost；不注入设备响应。
- **预期状态**：连接状态为 ConnectionLost；R1 结果为 Unknown；不得报告 Accepted、Running 或 Completed。
- **结果/诊断**：记录发送事实、未收到确认和未知结果；后续恢复必须通过查询/同步判定结果。
- **副作用断言**：不自动重发 R1；若未来协议定义相同幂等键的安全重试，必须由单独测试覆盖。

### STM-NEG-014：Synchronizing 阶段禁止 Start

- **目的/关联**：验证同步完成前控制操作受限；SYS-002、SYS-009。
- **前置条件**：连接状态为 Synchronizing；能力、任务状态或故障状态至少一项尚未完成同步。
- **事件序列**：发送 Start（无论是否携带已知 task_id）。
- **预期状态**：连接状态保持 Synchronizing；不得因 Start 自动进入 Connected 或 Running。
- **结果/诊断**：返回连接未就绪/同步中明确拒绝，并关联 request_id。
- **副作用断言**：不向运动、挤出或加热控制路径派发启动动作。

### STM-NEG-015：未知枚举、非法边与乱序事件

- **目的/关联**：验证事件流健壮性和状态单调性保护；SYS-009、SYS-013。
- **前置条件**：建立已知 session/task 状态快照；记录当前 Job State、连接状态和最后接受的序号/因果位置。
- **事件序列**：分组注入：(a) 未知状态枚举；(b) 状态图中未定义的边；(c) 已处理事件的重复副本；(d) 与当前事件流冲突的乱序事件；每组独立重置夹具。
- **预期状态**：不得跳转到 Completed、Cancelled、Paused 等未经合法前置条件确认的“成功”状态；保持最后可信状态或进入定义的 Fault/受限同步路径。
- **结果/诊断**：未知枚举、非法边、重复和乱序必须被区分记录；按接口策略拒绝、去重或触发重新同步。
- **副作用断言**：异常事件不得产生新的运动/挤出/加热动作；重复事件不得重复执行副作用。

## 4. 正向测试补充映射

以下用例不是 STM-NEG 负向集合的替代项，而是确保负向测试夹具本身不把合法流程误判为错误：

| 正向用例 ID | 主要序列 | 需求映射 | 关键断言 |
|---|---|---|---|
| STM-POS-001 | Idle → Validating → Ready → Running | SYS-009 / SIL-008 | 显式 Start 后才进入 Running |
| STM-POS-002 | Running → Pausing → Paused → Running | SYS-009 / SIL-008 | PauseEffective 与 Resume 分别确认 |
| STM-POS-003 | Ready/Running/Paused → Cancelling → Cancelled | SYS-009 / SIL-008 | CancelEffective 后才进入 Cancelled |
| STM-POS-004 | Running → Completed | SYS-009 / SIL-008 | 所有动作有设备侧完成证据 |
| STM-POS-005 | Connected → ConnectionLost → Synchronizing → Connected | SYS-002、SYS-013 / SIL-009 | 重连后重新同步，不沿用旧会话未决结果 |
| STM-POS-006 | 非终态 → Fault → 显式复位 → Idle | SYS-014 / SIL-010 | 故障源清除且复位守卫满足才退出 Fault |

## 5. 需求与接口覆盖核对

| 需求/场景 | 覆盖用例 | 验证重点 |
|---|---|---|
| SYS-009 / SIL-008 | STM-NEG-001～008、012、014、015；STM-POS-001～004 | 生命周期、状态守卫、任务唯一性、终态证据 |
| SYS-013 / SIL-009 | STM-NEG-011～015；STM-POS-005 | 超时/断连、Unknown、会话代际、事件顺序 |
| SYS-014 / SIL-010 | STM-NEG-006、009、010；STM-POS-006 | 故障锁存、危险动作拒绝、显式复位 |
| IF-002 / IF-003 | STM-NEG-001～008、011～015 | 请求关联、状态裁决、重复/乱序、重连 |
| IF-005 / IF-006 | STM-NEG-003、006、009、010 | 安全控制边界和虚拟输出事件隔离 |

核对结论：SYS-009、SYS-013、SYS-014 的需求语义均有负向测试规格覆盖；SIL-008、SIL-009、SIL-010 的正向主路径有独立映射。该结论是测试设计覆盖，不代表测试已执行。

## 6. 当前不可冻结项与后续责任

| 项目 | 当前处理 | 关闭责任节点 |
|---|---|---|
| 重复请求返回原结果还是拒绝 | 测试接受接口定义的三种明确策略，但必须无重复副作用 | 01-04 |
| sequence 作用域、回绕、乱序缓存窗口 | 由测试夹具注入，数值和协议规则不预设 | 01-04 |
| 会话代际标识与重连同步协议 | 逻辑隔离断言已定义，具体消息流程待定 | 01-04 |
| PauseEffective 的安全点及暂停期间输出策略 | 只测试确认先后，不指定物理动作策略 | 01-05、05 |
| CancelEffective、队列清理及热端/热床策略 | 只测试未确认前不得报告 Cancelled | 01-05、05 |
| Fault 状态的输出安全值、复位权限与复位条件 | 本文件只断言禁止新增危险动作；具体策略待安全分析 | 01-05 |
| 超时预算、重试次数、退避策略 | 使用可控事件注入，不写入臆测数值 | 01-04、07 |
| 虚拟模型精度与物理设备对应关系 | 不在本测试规格中声称已验证 | 07、08 |

## 7. 执行与通过规则

每次执行报告至少记录：
- 测试 ID、关联 SYS/SIL/IF、测试代码 commit、固件/主机/模拟器版本；
- 夹具配置、初始连接/任务状态、事件输入序列；
- 期望状态与实际状态、期望结果与实际结果；
- 副作用事件清单及其来源；
- 诊断/日志关联标识；
- 通过/失败/阻塞状态、失败复现输入和报告生成时间。

单个用例只有在状态、结果/诊断和副作用三类断言全部通过时才通过。测试未运行、测试环境缺失或安全策略尚未定义的断言必须标记为“未执行/阻塞”，不得计为通过。


## 8. 请求/事件/会话一致性扩展用例

本组用例细化 [请求、事件与会话一致性语义](../architecture/request-event-session-semantics.md)。所有测试均使用虚拟设备和可控事件注入；不证明物理设备动作安全。

### STM-NEG-016：相同 request_id、不同载荷

- **前置条件**：Connected；请求 R1（request_id=R1）已被设备 Accepted；保存原请求摘要和 ledger。
- **事件序列**：再次提交 request_id=R1，但改变动作类型或参数。
- **预期状态**：原请求状态/摘要保持不变；当前 Job State 不因冲突请求改变。
- **结果/诊断**：返回请求标识冲突/PROTOCOL_ERROR；诊断关联 session_id 与 R1。
- **副作用断言**：冲突载荷不执行；原请求副作用计数不增加。

### STM-NEG-017：重复事件标识但载荷冲突

- **前置条件**：已应用 event_id=E1、sequence=N、payload=P1 的事件。
- **事件序列**：在同一事件流注入 event_id=E1、sequence=N、payload=P2（P2 与 P1 不同）。
- **预期状态**：不应用冲突事件；不得回滚或推进 Job State。
- **结果/诊断**：记录 PROTOCOL_ERROR，并触发受控重新同步。
- **副作用断言**：冲突事件不产生运动/挤出/加热副作用。

### STM-NEG-018：事件序号缺口期间不得推进终态

- **前置条件**：T1 为 Running；同一事件流已应用 sequence=N；完成事件预期依赖 N+1。
- **事件序列**：先注入 sequence=N+2 的 Completed/JobExecutionComplete；暂不注入 N+1。
- **预期状态**：不得进入 Completed；记录缺口并暂缓依赖事件或进入受限重新同步状态。
- **结果/诊断**：报告 EVENT_GAP，保留缺失序号区间。
- **副作用断言**：不得发布任务完成业务事件，不得开始下一任务。

### STM-NEG-019：重连快照水位之前的迟到事件

- **前置条件**：新 session S2 同步快照已建立，事件流 watermark=W；当前任务 T2 状态已记录。
- **事件序列**：在 S2 下迟到注入 sequence≤W 的非重复旧事件，尝试改变任务状态。
- **预期状态**：快照水位之前的事件不应用于当前状态；T2 状态保持不变。
- **结果/诊断**：标记过期/已被快照覆盖；若 event_id/sequence 冲突则报告协议错误。
- **副作用断言**：不产生任何新控制输出。

### STM-NEG-020：同步快照与增量事件不一致

- **前置条件**：连接状态为 Synchronizing；模拟器可分别控制快照 watermark 和增量事件。
- **事件序列**：注入互相矛盾的快照/增量，或注入无法补齐的 sequence gap。
- **预期状态**：保持 Synchronizing 或退回 Disconnected；不得进入 Connected 并发布不一致状态。
- **结果/诊断**：报告 SYNC_INCONSISTENT 或 EVENT_GAP；记录两侧证据及 watermark。
- **副作用断言**：同步未完成时不接受 Start/Resume/运动/挤出/加热请求。

### STM-NEG-021：设备重启后无法查询未决请求结果

- **前置条件**：R1 为可能产生副作用的未决请求；发送后断连；模拟设备重启且请求去重记录不可恢复。
- **事件序列**：建立新 session；查询 R1；设备返回无法确定或不存在足够证据。
- **预期状态**：R1 保持 Unknown；不得把“查无记录”解释为“确定未执行”；连接保持 Synchronizing/受限态，不得进入可接受危险控制请求的 Connected 状态，直至完成明确的安全处置/人工裁决。
- **结果/诊断**：记录 RESULT_UNKNOWN、设备重启/账本不可用事实。
- **副作用断言**：不得自动重放 R1；无新运动/挤出/加热输出。

### STM-POS-007：同请求重复提交返回原结果且只执行一次

- **前置条件**：Connected；设备请求账本启用；构造确定可安全验证的虚拟请求。
- **事件序列**：提交 R1；设备 Accepted；在执行中重复提交相同 session_id/request_id/载荷；再重复查询。
- **预期状态**：返回同一请求的已知阶段/结果；状态转换只发生一次。
- **结果/诊断**：所有响应关联到同一 request_id/correlation_id。
- **副作用断言**：对应虚拟副作用只执行一次。

### STM-POS-008：事件缺口补齐后按序应用

- **前置条件**：T1 Running；事件流已应用 sequence=N。
- **事件序列**：先收到 N+2 并缓冲；后收到 N+1；再处理 N+2。
- **预期状态**：按 N+1、N+2 的因果顺序应用；最终状态与连续有序投递一致。
- **结果/诊断**：缺口关闭记录可审计，不留下未解释丢弃。
- **副作用断言**：每个有效事件的副作用恰好一次，不重复。

### STM-POS-009：重连查询确认旧请求已执行

- **前置条件**：S1 中 R1 已被设备接受并执行，但主机在收到终态前断连；新会话 S2 已建立。
- **事件序列**：S2 同步握手后，使用原始 session_id=S1 与 request_id=R1 查询；设备返回 Completed 并关联原 task_id。
- **预期状态**：HOST 更新原请求 ledger 为 Completed；不创建重复任务；当前设备状态与权威快照一致。
- **结果/诊断**：保留 S1 原请求标识及 S2 查询证据的关联链。
- **副作用断言**：不重放 R1，不产生第二次运动/挤出/加热动作。

## 9. 扩展覆盖映射

| 语义主题 | 用例 | 主要接口/需求 |
|---|---|---|
| request_id 冲突、去重 | STM-NEG-016、STM-POS-007 | IF-002、IF-003；SYS-009、SYS-013 |
| event_id 冲突、sequence 缺口/补齐 | STM-NEG-017、018；STM-POS-008 | IF-002、IF-003；SYS-013 |
| 重连 watermark 与同步一致性 | STM-NEG-019、020 | IF-002、IF-003；SYS-002、SYS-013 |
| 重启后 Unknown 处理 | STM-NEG-021 | IF-002、IF-003；SYS-013、SYS-014 |
| 查询原请求结果而不重放 | STM-POS-009 | IF-002、IF-003；SYS-009、SYS-013 |

以上为新增测试设计，不代表用例已实现或执行。

### STM-NEG-022：动作可能已开始，但重启后账本丢失

- **前置条件**：R1 是可能产生物理副作用的请求；设备侧已进入动作开始边界，但尚未向 HOST 返回终态；随后模拟设备重启，且设备侧请求记录不可恢复。
- **事件序列**：新 session 建立；HOST 使用原始 session_id + request_id 查询 R1；设备只能返回记录不可用/结果未知，当前物理位置或输出状态也不足以证明动作是否发生。
- **预期状态**：R1 保持 Unknown；设备连接不得进入允许危险动作的完全 Connected 状态，直至完成安全处置/人工裁决；不得创建“未执行”推断。
- **结果/诊断**：记录重启代际、原请求身份、账本不可恢复事实及 RESULT_UNKNOWN。
- **副作用断言**：不自动重放 R1；同步期间不产生新运动、挤出或加热输出。

### STM-NEG-023：快照缺少一致性 watermark

- **前置条件**：连接状态为 Synchronizing；设备快照包含任务/故障状态，但未提供对应事件流 watermark，或明确声明快照与事件流不是同一一致性切面。
- **事件序列**：HOST 尝试将快照与已缓存增量事件合并并请求完成同步。
- **预期状态**：不得进入 Connected；保持 Synchronizing 或退回重新取快照流程。
- **结果/诊断**：报告 SYNC_INCONSISTENT，并记录缺失的 stream identity/watermark。
- **副作用断言**：不得放行 Start/Resume/运动/挤出/加热请求。

### STM-NEG-024：HOST 与 TASK 请求账本证据矛盾

- **前置条件**：HOST ledger 将 R1 记录为 Accepted/InProgress；TASK 对同一原始 session_id + request_id 返回冲突终态、不同载荷摘要，或与主机已保存的设备确认矛盾的结果。
- **事件序列**：执行重连查询并接收冲突证据；随后注入普通状态刷新尝试。
- **预期状态**：保持 Synchronizing/受限状态；不得用任一未经解释的冲突结果覆盖另一方审计记录。
- **结果/诊断**：报告 PROTOCOL_ERROR 或 SYNC_INCONSISTENT，保留双方原始响应、摘要和关联 ID。
- **副作用断言**：不重放 R1；不因冲突结果放行新的危险动作。

### STM-POS-010：设备持久记录证明旧请求已完成

- **前置条件**：S1 中 R1 已完成；设备侧请求记录在重启后仍可查询，且记录包含原 session_id、request_id、载荷摘要、task_id 和 Completed 结果。
- **事件序列**：设备重启并建立 S2；HOST 查询原始 S1 + R1；TASK 返回可验证的原始完成记录；随后完成当前任务/故障快照与事件 watermark 同步。
- **预期状态**：HOST 将 R1 的当前视图更新为 Completed，同时保留重启前 Unknown 的历史时间线；当前连接仅在其他同步条件均满足时进入 Connected。
- **结果/诊断**：查询结果与原始请求摘要、task_id 和设备记录代际一致。
- **副作用断言**：不重放 R1，不产生第二次运动/挤出/加热动作。

## 10. 扩展覆盖映射补充

| 语义主题 | 用例 | 主要接口/需求 |
|---|---|---|
| 重启后动作边界与账本丢失 | STM-NEG-022 | IF-002、IF-003；SYS-013、SYS-014 |
| 快照一致性切面/watermark | STM-NEG-023 | IF-002、IF-003；SYS-002、SYS-013 |
| HOST/TASK 账本矛盾 | STM-NEG-024 | IF-002、IF-003；SYS-013 |
| 设备持久记录恢复 | STM-POS-010 | IF-002、IF-003；SYS-009、SYS-013 |

### STM-NEG-025：同一请求身份出现不同载荷摘要

- **前置条件**：TASK 已为 S1/R1 保存操作 OP-A 与载荷指纹 D1。
- **事件序列**：HOST 在同一 device_id + S1 + R1 下提交 OP-B 或摘要 D2，且 D2 != D1。
- **预期状态**：拒绝请求并保持原账本记录不变；不得将新载荷覆盖旧记录。
- **结果/诊断**：返回 REQUEST_ID_PAYLOAD_CONFLICT，记录原/新 schema 标识与摘要元数据。
- **副作用断言**：不产生第二次运动、挤出、加热或任务控制副作用。

### STM-NEG-026：规范化配置或 schema 版本不兼容

- **前置条件**：设备仅支持 profile P1/schema V1，收到使用 P2/V2 的同身份请求；不存在经过验证的兼容映射。
- **事件序列**：TASK 尝试比较请求指纹并处理请求。
- **预期状态**：明确拒绝或报告不可比较；不得将不同 profile 的摘要直接比较后推断载荷相同/不同。
- **结果/诊断**：CANONICALIZATION_VERSION_MISMATCH 或 UNSUPPORTED_SCHEMA_VERSION。
- **副作用断言**：不接受请求、不执行副作用、不覆盖旧账本。

### STM-NEG-027：规范化输入包含重复键或非法数值

- **前置条件**：请求编码包含重复对象键、NaN/Infinity、数值溢出或 schema 禁止的未知字段。
- **事件序列**：解析器接收并尝试规范化请求。
- **预期状态**：在载荷指纹比较及请求接受之前拒绝输入；不得采用“最后一个重复键覆盖前一个”等解析器差异行为。
- **结果/诊断**：INVALID_ARGUMENT 或明确的协议/schema 错误，并记录失败字段/位置。
- **副作用断言**：不得创建可执行的 Accepted 请求记录，不产生任何设备副作用。

### STM-NEG-028：旧规范化规则被静默替换

- **前置条件**：账本中存在按 profile P1 保存的请求记录；软件升级后当前实现只剩 P2，且未提供 P1 验证器或兼容映射。
- **事件序列**：新版本尝试查询或重试旧请求。
- **预期状态**：保持原记录和原摘要；结果不可比较时保持 Unknown/受限同步或明确拒绝，不得按 P2 重算并覆盖 P1。
- **结果/诊断**：CANONICALIZATION_VERSION_MISMATCH，并记录软件/profile 版本。
- **副作用断言**：不重放旧请求，不执行任何副作用。

### STM-POS-011：对象字段顺序变化得到相同规范化指纹

- **前置条件**：同一 schema/profile 下，两份请求仅对象字段排列不同，字段值、数组顺序及所有语义字段完全相同。
- **事件序列**：分别规范化两份请求并比较规范化字节和摘要。
- **预期状态**：规范化字节与摘要完全相同；第二次以相同请求身份提交时返回原请求阶段/结果。
- **结果/诊断**：测试报告记录 profile、规范化字节向量和摘要算法标识。
- **副作用断言**：设备动作最多执行一次。

### STM-POS-012：传输/诊断元数据变化不改变载荷指纹

- **前置条件**：两条请求的 operation、schema/profile 和业务 payload 相同，仅 message_id、correlation_id、发送时间或重试计数不同。
- **事件序列**：分别计算载荷指纹并验证账本请求身份仍使用原 session_id + request_id。
- **预期状态**：载荷指纹相同；元数据仍各自保留在传输/审计记录中，不参与业务载荷等价判断。
- **结果/诊断**：测试报告区分请求身份字段、载荷字段和诊断元数据。
- **副作用断言**：相同请求身份只允许一次副作用；不同 request_id 不得因此被自动合并。

## 11. 规范化原型自动化测试映射

载荷规范化逻辑测试已从设计规格进入独立 Python 原型测试（当前 7 项测试方法），具体 profile 和边界见[请求载荷规范化文档](../architecture/request-payload-canonicalization.md)第 10 节。

| 测试实现 | 对应规格 | 当前覆盖 |
|---|---|---|
| `test_golden_vectors_match_bytes_and_sha256` | STM-POS-011，并扩展跨实现黄金向量要求 | 比较规范化 UTF-8 字节及 SHA-256 |
| `test_object_key_order_does_not_change_canonical_bytes` | STM-POS-011 | 对象键顺序不影响规范化结果 |
| `test_array_order_remains_significant` | 规范化数组顺序规则 | 数组顺序变化导致字节变化 |
| `test_transport_metadata_outside_envelope_is_not_hashed` | STM-POS-012 | message_id、correlation_id、发送时间和重试计数位于业务封装之外，不改变载荷摘要 |
| `test_duplicate_json_keys_are_rejected` | STM-NEG-027 | 重复 JSON 键拒绝 |
| `test_floats_and_non_finite_numbers_are_rejected` | STM-NEG-027 | 浮点数及 NaN 拒绝 |
| `test_unknown_or_missing_envelope_fields_are_rejected` | STM-NEG-027 / STM-NEG-026 | 原型封装字段严格校验 |

实现位置：`tests/support/payload_canonicalization_reference.py`、`tests/fixtures/payload-canonicalization-vectors.json`、`tests/unit/test_payload_canonicalization.py`。GitHub Actions 工作流：`.github/workflows/python-unit-tests.yml`。

**证据状态**：测试代码和 CI 工作流已提交；必须以对应提交的 Actions 运行结果为准。代码存在或工作流文件存在，不等于 CI 已运行/通过。该原型仅验证测试 profile，不验证设备账本、持久化原子性、真实通信协议或物理安全。

## 12. 版本记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-11-04 | 0.1 | 将 STM-NEG-001～015 展开为测试规格，定义通用夹具、事件记录、正向补充映射及未冻结项。 |
| 2026-11-04 | 0.2 | 增加请求 ID 冲突、事件冲突/缺口、重连快照水位、设备重启后 Unknown 和原请求查询测试。 |
| 2026-11-04 | 0.3 | 增加动作开始后重启账本丢失、快照 watermark 缺失、HOST/TASK 账本矛盾和设备持久记录恢复测试。 |
| 2026-11-04 | 0.4 | 增加载荷摘要冲突、规范化版本不兼容、严格解析及黄金向量正向测试。 |
| 2026-11-04 | 0.5 | 增加实验性规范化原型的自动化测试映射与 CI 证据边界。 |
