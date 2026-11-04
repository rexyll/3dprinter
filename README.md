# 3D Printer Knowledge Base

本仓库按两阶段建设：**第一阶段先从零构建并在仿真环境中运行一台完整的 3D 打印机；第二阶段在第一阶段通过验收后整理行业全景知识库。**

## 当前状态
- 当前阶段：第一阶段（工程实现优先）
- 当前任务：01-03 系统分层与接口架构
- 状态：正在进行中
- 总任务计划：[TaskPlan.md](TaskPlan.md)

## 第一阶段当前工作
- [第一阶段需求基线（已确认参考规格）](docs/phase1/requirements/requirements-baseline.md)
- [系统需求规格与 SIL 验收追踪](docs/phase1/requirements/system-requirements.md)
- [技术路线比较](docs/phase1/architecture/technology-route-assessment.md)
- [系统逻辑架构](docs/phase1/architecture/system-architecture.md)
- [系统上下文图](docs/phase1/architecture/system-context.mmd)
- [接口控制文档（ICD）](docs/phase1/architecture/interface-control.md)
- [系统需求—组件—接口追踪矩阵](docs/phase1/architecture/requirements-component-interface-trace.md)

## 文档维护规范
- [文档导航](docs/README.md)
- [贡献指南](docs/CONTRIBUTING.md)
- [写作规范](docs/STYLE_GUIDE.md)
- [项目术语表](docs/GLOSSARY.md)

## 工程规范与基线
- [来源登记与证据规范](docs/sources/README.md)
- [来源台账](docs/sources/register.md)
- [ADR 决策记录](docs/decisions/README.md)
- [ADR-0002：FFF 材料挤出工艺路线](docs/decisions/ADR-0002-fff-material-extrusion.md)
- [风险登记表](docs/risks/register.md)
- [问题与假设登记表](docs/risks/open-issues.md)
- [变更记录](docs/changes/README.md)

## 章节任务计划
- [00 项目治理与知识库规范](docs/TaskPlan/00-governance.md)
- [01 需求与系统架构](docs/TaskPlan/01-requirements-architecture.md)
- [02 机械系统](docs/TaskPlan/02-mechanics.md)
- [03 电气与硬件平台](docs/TaskPlan/03-electronics-hardware.md)
- [04 BSP、驱动与嵌入式基础](docs/TaskPlan/04-bsp-drivers.md)
- [05 打印机固件与运动控制](docs/TaskPlan/05-firmware-motion.md)
- [06 主机、切片与 App 软件](docs/TaskPlan/06-host-slicer-app.md)
- [07 仿真与虚拟硬件](docs/TaskPlan/07-simulation.md)
- [08 集成、验证与发布](docs/TaskPlan/08-integration-validation.md)
- [09 第二阶段行业知识体系（门禁后启动）](docs/TaskPlan/09-industry-knowledge.md)

## 重要规则
根目录 [TaskPlan.md](TaskPlan.md) 中的 Guide、Limit、阶段门禁和状态规则具有全局约束力。章节计划必须与根计划同步。没有可复现证据，不得标记任务完成。
