# PolyNexus 文档索引

这个目录存放项目规划、阶段台账、验收记录和维护说明。运行时使用说明仍以根目录 `README.md` 为入口。

## 目录结构

- `plans/`
  - 总体规划、开发路线图、阶段任务清单和专题修复清单。
  - 适合回答“下一步做什么”和“某条技术线为什么这么设计”。
- `baselines/`
  - 各番外阶段的当前基线台账。
  - 适合在修改分析算法前确认既有行为和验收基线。
- `acceptance/`
  - 阶段收口总结、实施验收与合并说明。
  - 适合在合并、回顾或交接时查看。
- `patch-bundles/`
  - 可审阅或应用的补丁包及其 README。
  - 补丁包 README 中应保留应用顺序、验证命令和适用前提。
- `superpowers/`
  - agent 协作产生的规格和实施计划。
  - 适合追踪近期设计决策和拆分任务。

## 常用入口

- [开发路线图](plans/PolyNexus%20开发路线图.md)
- [统一框架方案 v4.0](plans/PolyNexus%20统一框架方案%20v4.0.md)
- [智能调参 Agent 与评测体系方案 v4.1](plans/PolyNexus%20智能调参%20Agent%20与评测体系方案%20v4.1.md)
- [核心与物理可信度矫正总体规划](plans/PolyNexus%20核心与物理可信度矫正总体规划.md)
- [工程质量与深层物理模型增强实施计划](plans/PolyNexus%20工程质量与深层物理模型增强实施计划.md)
- [核心与物理可信度矫正实施验收与合并说明](acceptance/PolyNexus%20核心与物理可信度矫正实施验收与合并说明.md)
- [维护说明](maintenance.md)
- [维护边界清单](maintenance-boundaries.md)

## 放置规则

- 新的规划、路线图、任务清单放入 `plans/`。
- 新的“当前基线台账”放入 `baselines/`。
- 阶段验收、收口总结、合并说明放入 `acceptance/`。
- 补丁包目录放入 `patch-bundles/`，并包含独立 README。
- 不再新增根目录 `方案` 或单数 `doc` 目录。
