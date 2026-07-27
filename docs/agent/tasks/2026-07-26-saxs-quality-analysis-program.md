# SAXS 质量与分析体系路线任务卡

## Goal

建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系，先完成变温 1D Guinier 纵向闭环，再扩展到 1D 方法族、静态/变温/应变、2D、AI 救援及 Workbench/Figure/Manifest/Export。

设计文档：`docs/superpowers/specs/2026-07-26-saxs-quality-analysis-program-design.md`

## Non-goals

- 第一阶段不重写所有 SAXS 算法。
- 不自动生成缺失帧的伪实测数据。
- 不把 Guinier 判据套用于不满足其物理假设的层片/Bragg 主导场景。
- 不在没有证据时提升主结论或 paper figure 角色。

## Acceptance criteria

- [x] 每个阶段都有独立任务卡、设计/计划、focused tests 和实际 verifier 证据。
- [x] 原始数据不被覆盖；清洗和救援动作可追溯、可重放。
- [x] 每帧和每个指标支持 `Quantitative`、`Trend`、`Diagnostic`、`Unusable` 分级。
- [x] AI 候选不能绕过确定性重算、物理门槛和序列证据验证。
- [x] 缺失温度帧保持缺失，不被静默插值成实验事实。
- [x] 最终结果能贯穿 Workbench、Figure、Manifest、Export 和 History。

## 路线审计状态（2026-07-27）

总路线的自动化 contract/consumer 验收已由阶段任务卡、设计/计划文件、
focused 回归、结构化 verifier 和显式 allowlist checkpoint 覆盖。完整的
阶段映射、实际证据和剩余门槛见：
`docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md`。

当前 head 的 SAXS 文件矩阵为 `364 passed, 4 warnings in 31.08s`；real
SAXS walkthrough 为 `3 passed, 12 deselected`，Workbench/figure profile
矩阵为 `29 passed`。既有外部真实 bundle 的保守证据保持不变：static 的
Guinier/Porod/Kratky/invariant/lamellar 为 `Diagnostic`；temperature
sequence Guinier 为 `Unusable`（`guinier_sequence_no_valid_frames`）；strain
保留五个 `Trend` frame。没有因为图像能渲染而提升证据或 publication role。

自动化验收完成不等于发布完成。以下门槛仍保持打开：重启 GUI 后的真实
交互/视觉检查、温变与应变真实科学意义复核、raw 2D detector/geometry 与
mask propagation 的真实验收，以及最终人工 release/publication approval。

## Affected boundaries

- `polynexus/readers/` 与 `polynexus/core/saxs_engine/io.py`：输入、q 轴和图像质量。
- `polynexus/core/saxs_engine/preprocess.py`：确定性清洗、积分和背景处理。
- `polynexus/core/saxs_engine/core.py` 与温度/应变模块：物理指标与序列证据。
- `polynexus/core/preprocess_optimization/`：AI 候选、硬门槛和决策审计。
- SAXS result、figure eligibility、Workbench、Manifest、Gallery、Editor、Export、History。
- `tests/`、`docs/acceptance/`、`docs/agent/memory/`：回归、验收和 durable state。

## Implementation plan

1. 建立最小质量契约、原因码、可信等级和故障注入夹具。
2. 打通变温 1D Guinier 的清洗、拟合、证据、序列分级和结果消费闭环。
3. 将同一证据结构扩展到 Porod、Kratky、不变量和现有层片方法。
4. 覆盖静态/变温/应变模式，以及 2D 探测器质量和取向分析。
5. 增加序列级救援和相变感知验证，再接入 AI shadow/confirm/安全自动化。
6. 完成 Workbench、Figure、Manifest、Export、History、真实数据和人工科学验收。

## Scope

- SAXS 数据质量报告、物理指标证据、救援候选和验证结果。
- 变温 1D q-I Guinier 试点及其序列级证据。
- 后续 Porod、Kratky、不变量、层片、2D、序列和 AI 阶段的任务分解与验收。
- 与现有 SAXS result、figure eligibility、preprocess optimization 和 GUI 发布边界对接。

## Non-goals

- 第一阶段不重写所有 SAXS 算法。
- 不自动生成缺失帧的伪实测数据。
- 不把 Guinier 判据套用于不满足其物理假设的层片/Bragg 主导场景。
- 不在没有证据时提升主结论或 paper figure 角色。

## Verification

阶段任务使用：

```bash
python scripts/verify.py --task docs/agent/tasks/<stage-task>.md --changed --types
```

发布阶段追加：

```bash
python scripts/verify.py --changed --types --full --boundary
```

本路线的详细执行、阶段映射、验证矩阵和 checkpoint allowlist 见：
`docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md`。

## Checkpoint allowlist

- `docs/superpowers/plans/2026-07-26-saxs-quality-analysis-program.md`
- 本任务卡
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Known risks

- `qRg < 1.3` 只能作为适用场景内的判据，不能单独证明 Rg 有物理意义。
- 温度相变可能是真实突变，序列连续性规则必须阶段感知。
- 现有 SAXS 质量、温度可靠性和预处理决策逻辑分散，第一阶段需要谨慎复用而不是复制。
- 真实数据、重启 GUI、导出和人工科学审查不能由合成测试替代。

## Pre-existing workspace changes

本任务建立设计/任务文档时，不修改或清理工作区已有的未跟踪诊断输出、草稿和运行目录。
