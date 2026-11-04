# 文档导航

本目录按“单一事实源、可追溯证据、版本化决策、可复现验证”组织。项目总任务状态以根目录 `TaskPlan.md` 为准，各章节任务状态以对应 `docs/TaskPlan/*.md` 为准。

## 第一阶段工程文档

| 领域 | 路径 | 权威内容 |
|---|---|---|
| 需求基线 | [phase1/requirements/requirements-baseline.md](phase1/requirements/requirements-baseline.md) | 用户场景、需求 ID、验收边界和未决项 |
| 系统需求规格 | [phase1/requirements/system-requirements.md](phase1/requirements/system-requirements.md) | SYS 级行为要求、任务状态、故障响应、SIL 验收和追踪矩阵 |
| 技术路线评估 | [phase1/architecture/technology-route-assessment.md](phase1/architecture/technology-route-assessment.md) | FFF、SLA、PBF 等工艺路线的项目适配性比较 |
| 系统逻辑架构 | [phase1/architecture/system-architecture.md](phase1/architecture/system-architecture.md) | 系统分层、数据流、时序域和故障隔离 |
| 系统上下文图 | [phase1/architecture/system-context.mmd](phase1/architecture/system-context.mmd) | 系统组件与主要控制/反馈流 |
| 接口控制文档 | [phase1/architecture/interface-control.md](phase1/architecture/interface-control.md) | IF-001 至 IF-009 逻辑接口契约和错误语义 |
| 需求—组件—接口追踪 | [phase1/architecture/requirements-component-interface-trace.md](phase1/architecture/requirements-component-interface-trace.md) | SYS/SIL 到逻辑组件和接口的覆盖关系及待关闭缺口 |
| 任务状态转换契约 | [phase1/architecture/task-state-transition-contract.md](phase1/architecture/task-state-transition-contract.md) | 连接/作业正交状态、状态转换守卫、非法转换和 SIL 断言 |
| 来源规范 | [sources/README.md](sources/README.md) | 来源登记字段、证据类型和引用规则 |
| 来源台账 | [sources/register.md](sources/register.md) | 外部资料及项目输入的来源记录 |
| 架构决策 | [decisions/README.md](decisions/README.md) | ADR 状态、模板和索引 |
| 已批准范围决策 | [decisions/ADR-0001-reference-printer-baseline.md](decisions/ADR-0001-reference-printer-baseline.md) | 第一阶段参考打印机范围 |
| 风险 | [risks/register.md](risks/register.md) | 工程风险及控制方向 |
| 问题与假设 | [risks/open-issues.md](risks/open-issues.md) | 未决问题、暂定假设和关闭条件 |
| 变更 | [changes/README.md](changes/README.md) | 变更登记规则与模板 |

## 维护规范

- [贡献指南](CONTRIBUTING.md)：工作流、任务状态、提交和审查要求。
- [写作规范](STYLE_GUIDE.md)：命名、结构、表格、图表、代码和版本规则。
- [术语表](GLOSSARY.md)：项目术语的统一定义。
- [章节任务计划](TaskPlan/)：各章节的任务拆分、依赖和验收标准。

## 事实源优先级

1. 用户明确批准的项目约束：来源台账 + 对应 ADR + 需求基线。
2. 外部技术事实：来源台账登记的原始资料及其适用版本。
3. 项目设计决定：已接受 ADR；暂定 ADR 不能覆盖已批准约束。
4. 实际软件行为：版本化源代码、自动化测试和测试报告。
5. 当前执行状态：根 TaskPlan 与对应章节 TaskPlan。

若不同文件出现矛盾，应先登记问题并修正权威事实源，再更新引用处；不要在多个位置维护互相独立的参数副本。
