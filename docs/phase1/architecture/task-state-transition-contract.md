# 任务生命周期状态转换契约与 SIL 断言

- **状态**：逻辑状态机设计基线草案；安全策略和传输事件编码待后续节点冻结
- **版本**：0.1
- **日期**：2026-11-04
- **关联任务**：01-03
- **需求依据**：[系统需求规格](../requirements/system-requirements.md) SYS-002、SYS-009、SYS-013、SYS-014
- **接口依据**：[接口控制文档](interface-control.md)
- **追踪依据**：[需求—组件—接口追踪矩阵](requirements-component-interface-trace.md)

## 1. 目的与边界

将需求级任务生命周期转换为可审查、可测试的状态转换契约。本文定义逻辑状态、触发事件、守卫条件、结果和负向断言，不定义具体 API、消息编码、数值超时、暂停安全点、取消时队列处理或加热策略。

本文只描述 SIL 可验证的软件状态语义，不构成真实机器安全认证或硬件行为证明。

## 2. 正交状态域

不得把连接状态与打印任务状态混成一个枚举。两者相互关联，但表达不同事实。

### 2.1 连接状态（Connection State）

| 状态 | 含义 | 允许报告的事实 |
|---|---|---|
| Disconnected | 当前无有效通信会话 | 设备实时状态不可确认 |
| Connecting | 正在建立会话 | 尚未证明设备可用 |
| Synchronizing | 会话已建立，正在读取能力、任务和设备状态 | 连接已建立，但控制操作受限 |
| Connected | 会话有效且必要状态同步完成 | 可按能力和任务状态提交允许的请求 |
| ConnectionLost | 已检测到既有会话丢失 | 未完成请求结果可能未知；设备状态不可确认 |

ConnectionLost 是运行时的明确失联状态；完成重新连接后进入 Synchronizing，而不是直接回到 Connected。同步失败应保持受限或回到 Disconnected，不能伪装为同步成功。

### 2.2 作业状态（Job State）

| 状态 | 含义 | 是否终态 |
|---|---|---|
| Idle | 当前没有活动作业 | 否 |
| Validating | 正在检查作业格式、能力和启动前置条件 | 否 |
| Ready | 校验通过，等待显式开始 | 否 |
| Running | 作业执行正在推进 | 否 |
| Pausing | 暂停请求已接受，正在达到定义的暂停生效条件 | 否 |
| Paused | 暂停已生效，执行上下文保留 | 否 |
| Cancelling | 取消请求已接受，正在完成停止与队列处置 | 否 |
| Completed | 作业全部执行完成 | 是 |
| Cancelled | 取消停止条件已满足，任务终止 | 是 |
| Fault | 致命故障已锁存，正常作业执行被禁止 | 是（本任务实例） |

Disconnected/ConnectionLost 不属于 Job State。通信丢失时任务可能仍在设备侧执行，也可能已停止；主机不能仅凭连接状态推断设备侧 Job State。此时应保留最后确认状态并标记其可信度为 Unknown/Stale，直至重新同步。

## 3. 状态转换矩阵

说明：
- “请求接受”表示请求通过初步校验并进入处理，不等于目标状态已经生效。
- 所有状态转换均由设备侧 TASK 状态裁决；HOST/UI 只能展示已确认的状态或明确的未知状态。
- 未列出的转换一律拒绝，且不得产生对应的运动、挤出或加热副作用。
- 连接失联、进程重启等外部事件不能被伪装为 Completed 或 Cancelled。

| 当前状态 | 事件/请求 | 守卫条件（概念级） | 结果状态 | 失败/拒绝结果 |
|---|---|---|---|---|
| Idle | SubmitJob | 会话已同步；无其他活动任务 | Validating | 保持 Idle；报告连接/忙碌/输入错误 |
| Validating | ValidationPassed | 作业、能力和启动前置条件均通过 | Ready | — |
| Validating | ValidationFailed | 校验发现错误 | Idle（任务实例拒绝并关闭） | 保留可追踪拒绝结果，不创建可运行任务 |
| Ready | Start | 显式开始；会话同步；无锁存故障；启动前置条件通过 | Running | 保持 Ready；报告拒绝原因 |
| Running | Pause | 暂停请求被接受 | Pausing | 保持 Running；报告拒绝原因 |
| Pausing | PauseEffective | 设备侧声明的暂停生效条件满足 | Paused | 仍为 Pausing 或转 Fault；不得提前报告 Paused |
| Paused | Resume | 显式恢复；会话同步；无锁存故障；恢复前置条件通过 | Running | 保持 Paused；报告拒绝原因 |
| Ready / Running / Paused | Cancel | 取消请求被接受 | Cancelling | 保持原状态；报告拒绝原因 |
| Cancelling | CancelEffective | 停止条件和队列处置条件满足 | Cancelled | 仍为 Cancelling 或转 Fault；不得提前报告 Cancelled |
| Running | JobExecutionComplete | 所有作业动作均已确认完成且无未处理致命错误 | Completed | 保持 Running 或转 Fault；不得以发送/排队完成代替 |
| 任一非终态 | FatalFault | 故障判定条件成立 | Fault | 故障锁存；拒绝新的危险动作 |
| Fault | ClearFaultAndReset | 故障源已清除且安全设计规定的复位条件全部满足 | Idle（新任务上下文） | 保持 Fault；报告未满足条件 |
| Completed / Cancelled | NewJob | 旧任务已终结且新任务输入合法 | Validating | 保持终态；拒绝原因可追踪 |
| 任意状态 | 未列出的事件/请求 | 不适用 | 不变 | INVALID_STATE 或相应明确错误 |

注：ValidationFailed 后任务记录可以保留为“拒绝/失败记录”，但不可把它作为活动作业；活动 Job State 回到 Idle。具体持久化记录状态由主机任务服务设计确定。

## 4. 连接状态与任务状态交互

| 连接事件 | 连接状态变化 | 任务状态处理 | 主机必须执行的行为 |
|---|---|---|---|
| 建立会话 | Disconnected → Connecting → Synchronizing | 不得因连接建立自动改变设备任务状态 | 获取能力、任务状态、故障状态和必要遥测 |
| 同步完成 | Synchronizing → Connected | 采用设备侧重新确认的状态 | 使旧会话未决请求失效或标记结果未知 |
| 连接丢失 | Connected → ConnectionLost | 设备侧任务状态未知；不得擅自设为 Cancelled/Fault/Completed | 冻结危险控制请求；标记状态/遥测 Stale 或 Unknown；记录未决请求 |
| 重新连接 | ConnectionLost → Synchronizing | 以设备侧权威状态重新同步 | 比较 task_id/session_id/事件序号；识别新旧任务与结果 |
| 同步失败 | Synchronizing → Disconnected（或保持受限态） | 任务状态继续标记未知 | 禁止自动续跑；保留诊断信息 |

**重要约束**：通信丢失时，不得推断设备已经停止运动或加热。实际断连安全动作属于后续安全概念和硬件/固件策略，SIL 只能验证所定义软件行为和虚拟模型响应。

## 5. 状态机不变量

1. 同一设备最多存在一个活动任务；活动状态为 Validating、Ready、Running、Pausing、Paused、Cancelling。
2. Completed、Cancelled、Fault 对当前任务实例是终态；新任务必须有新的 task_id/任务上下文。
3. Completed 必须有设备侧执行完成证据；发送成功、接收成功、接受成功或队列为空均不足以单独证明 Completed。
4. Paused 只能由 Pausing 经 PauseEffective 进入；接受暂停请求不构成暂停生效证据。
5. Cancelled 只能由 Cancelling 经 CancelEffective 进入；接受取消请求不构成取消完成证据。
6. Fault 锁存期间，Start、Resume 以及任何会产生运动/挤出/加热副作用的请求必须被拒绝。
7. Fault 退出必须经过显式清故障/复位流程；普通开始、恢复或重新连接不得隐式清除故障。
8. 连接丢失时主机必须将设备状态和遥测标记为 Unknown/Stale；不得继续显示为实时可信值。
9. 旧 session 的响应/事件不得覆盖新 session 已同步的状态；旧 task_id 的事件不得改变新任务状态。
10. 未知、重复、乱序或非法状态事件不得使状态机跳转到更“成功”的状态；必须记录并按接口规则拒绝、去重或触发重新同步。
11. 任何状态拒绝均应产生可关联的错误结果或诊断事件；不得静默忽略。
12. 状态变化和对应事件必须有可关联的 task_id、session_id（适用时）及单调顺序信息。

## 6. 非法转换与负向断言矩阵

以下是最低负向测试集合；测试应同时断言“状态未发生非法变化”和“未产生危险副作用”。

| 测试 ID | 初始状态 | 非法输入/条件 | 必须断言 |
|---|---|---|---|
| STM-NEG-001 | Idle | 无作业时 Pause / Resume / Cancel | 返回 INVALID_STATE；无运动/加热动作 |
| STM-NEG-002 | Validating | 校验未通过时 Start | 不进入 Running；拒绝结果可关联任务 |
| STM-NEG-003 | Ready | 未显式 Start 即注入运动执行事件 | 不执行运动；状态不变或进入定义的故障路径 |
| STM-NEG-004 | Running | 重复 Pause 或不支持的状态请求 | 不产生重复暂停副作用；返回明确结果 |
| STM-NEG-005 | Pausing | 尚无 PauseEffective 却上报 Paused | 丢弃/拒绝非法跃迁并记录协议/状态错误 |
| STM-NEG-006 | Paused | 故障锁存时 Resume | 返回故障拒绝；不进入 Running |
| STM-NEG-007 | Cancelling | 尚无 CancelEffective 却上报 Cancelled | 不报告取消完成；保留 Cancelling 或进入 Fault |
| STM-NEG-008 | Running | 仅发送/排队计数达到总量即报告 Completed | 不进入 Completed；要求设备侧完成证据 |
| STM-NEG-009 | Fault | Start / Resume / 运动 / 加热请求 | 全部拒绝；输出维持安全设计定义的故障状态 |
| STM-NEG-010 | Fault | 普通连接恢复或普通状态刷新 | 不清除故障锁存；仍需显式复位 |
| STM-NEG-011 | 任意新 session | 收到旧 session 的迟到成功响应 | 不覆盖新 session 状态；旧响应归档/丢弃并诊断 |
| STM-NEG-012 | 新 task_id | 收到旧 task_id 的完成/取消事件 | 不改变当前任务状态 |
| STM-NEG-013 | ConnectionLost | 主机收到本地发送成功但无设备确认 | 结果保持 Unknown；不得报告 Accepted/Completed |
| STM-NEG-014 | Synchronizing | 尚未完成能力/状态同步时提交 Start | 拒绝控制请求；保持受限连接状态 |
| STM-NEG-015 | 任意状态 | 未知状态枚举、非法状态边或乱序事件 | 不跳转到成功状态；记录诊断并触发规定的同步/错误流程 |

## 7. 正向状态转换 SIL 断言映射

| SIL 用例/断言 | 覆盖转换或不变量 | 正向检查 |
|---|---|---|
| SIL-008-A | Idle → Validating → Ready | 提交有效作业；校验通过；task_id 稳定且状态顺序正确 |
| SIL-008-B | Ready → Running | 显式 Start 后收到设备侧 Running 确认 |
| SIL-008-C | Running → Pausing → Paused | 请求接受与暂停生效分别可观察；只有 PauseEffective 后进入 Paused |
| SIL-008-D | Paused → Running | 故障清除且恢复守卫满足后显式 Resume |
| SIL-008-E | Ready/Running/Paused → Cancelling → Cancelled | 请求接受与取消完成分别可观察；只有 CancelEffective 后进入 Cancelled |
| SIL-008-F | Running → Completed | 全部作业动作完成确认后进入 Completed；终态不再接受同任务执行推进 |
| SIL-009-A | Connected → ConnectionLost → Synchronizing → Connected | 断连后状态 stale/unknown；重连后重新同步设备侧状态 |
| SIL-009-B | 未决命令结果 | 响应丢失时标记 Unknown；状态查询/同步后确定结果，不盲目重发非幂等动作 |
| SIL-010-A | 任一非终态 → Fault | 故障锁存事件触发 Fault，故障源可追踪 |
| SIL-010-B | Fault 拒绝动作 | Start/Resume/运动/加热请求均拒绝，且无相应危险输出事件 |
| SIL-010-C | Fault → 显式复位 → Idle | 故障源清除、复位条件满足后才退出 Fault；普通请求不能复位 |

## 8. 测试报告字段与通过规则

每个 STM 测试执行至少记录：
- STM 测试 ID、关联 SIL ID、代码 commit、测试环境和配置；
- 初始连接状态、初始任务状态、task_id、session_id；
- 输入事件/请求序列及其顺序；
- 预期状态、实际状态、错误结果及副作用观测；
- 日志/报告路径、通过/失败/阻塞及未覆盖范围。

通过规则：
- 状态转换与预期完全一致；
- 非法转换没有导致状态越权或危险副作用；
- 请求确认、状态生效、执行完成没有混淆；
- 事件关联和顺序可审计；
- 无报告、无可复现输入或仅凭 UI 视觉观察的测试不得判定通过。

## 9. 待后续节点冻结的参数与策略

| 项目 | 当前处理 | 关闭节点 |
|---|---|---|
| PauseEffective 的具体安全点及运动队列处理 | 只定义事件语义，不指定策略 | 01-05、05 |
| CancelEffective 的停止/清队列/挤出处理 | 只定义终止完成条件，不指定硬件动作 | 01-05、05 |
| 暂停时热端/热床保持或关闭策略 | 不在本状态机臆定 | 01-05、05、07 |
| Fault 分级、锁存范围、清故障与复位授权 | 仅定义必须显式且不可绕过 | 01-05、05 |
| 会话 ID、事件序号宽度、去重窗口、乱序缓存 | 定义语义约束，不选协议编码 | 01-04 |
| 连接、请求、完成、遥测新鲜度超时数值 | 不填无依据常数 | 01-04、07 |
| 作业验证失败记录的持久化模型 | 活动状态回到 Idle，记录留给 HOST | 01-04、06 |

## 10. 审查结论

该状态转换契约将连接状态与作业状态正交建模，明确了请求接受与状态生效/执行完成的差异，并提供正向转换、非法转换及 SIL 断言映射。它补齐了 01-03 的状态机可测试性设计，但不代表测试代码已实现，也不关闭暂停/取消安全策略、协议编码、时序预算等接口缺口。01-03 继续保持“正在进行中”。
