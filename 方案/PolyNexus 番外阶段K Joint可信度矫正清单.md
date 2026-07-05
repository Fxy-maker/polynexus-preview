# PolyNexus 番外阶段 K Joint 可信度矫正清单

## 0. 当前问题定位

这份专项清单针对 `joint`，也就是跨技术联合分析和一致性复核。

当前代码已经具备 Joint 主流程：

1. `sample_db` 能收集样品、批次和分析运行记录。
2. `joint.dataset` 能收集同一批次下的 DSC/SAXS/WAXS/IR/NMR 最新结果。
3. `detect_joint_opportunities()` 能识别结晶度一致性、结构-热力学、SAXS-WAXS 多尺度、IR/DSC 标定机会。
4. `validate_joint_row()` 已经调用 `run_all_cross_validations()` 做跨技术检查。
5. `build_joint_hub_report()` 已经输出 summary rows、validations 和 `ai_context`。
6. GUI 里已经有 Joint Hub 和 Joint diagnostics。

但当前 Joint 可信度链还不够完整：

1. 有冲突提醒，但缺少“每个技术输入本身是否可信”的权重。
2. IR/NMR 的指数和结晶度估计可能被误当成同等级 `Xc` 来源。
3. Joint AI context 目前偏 issue 统计，缺少证据层级和结论可用性。
4. 导出包还需要明确区分“跨技术冲突”“单技术低可信”“缺少标定”。
5. Joint 不应替用户裁决科学结论，只应把冲突和证据呈现清楚。

## 1. 专项目标

番外阶段 K 只解决一个问题：

**让 PolyNexus 的 Joint 分析从“把多技术结果放在一起比较”升级为“按每条技术证据可信度加权解释跨技术一致性与冲突”。**

本专项希望完成 6 件事：

1. 冻结 Joint 当前基线台账。
2. 建立 Joint confidence context。
3. 把单技术 evidence 接入 Joint row。
4. 把跨技术冲突按族群、严重度和输入可信度分层。
5. 让 AI 调参知道当前应该优先修单技术证据，还是处理跨技术不一致。
6. 让 GUI/导出能表达 Joint 结果的可用层级。

## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕 `joint` 建立独立可信度证据链。
- 扩展 `build_joint_hub_report()` 的 `ai_context`。
- 让 Joint row 看到各技术的 `analysis_evidence` 摘要。
- 区分：
  - 单技术低可信。
  - 跨技术真实冲突。
  - 条件轴/批次对齐问题。
  - 缺少标定或归属导致的弱证据。
- 让 GUI 和导出明确显示 Joint 当前能支持什么结论。

### 2.2 本专项暂时不做什么

- 不做全自动跨技术联合拟合平台。
- 不让 AI 替用户决定哪个技术“最终正确”。
- 不一次性重写 Joint GUI。
- 不把 IR band index 和 NMR assignment-limited Xc 强行当作绝对结晶度。
- 不在 Joint 里修各单技术算法，单技术问题回到对应阶段处理。

## 3. 最小闭环

本专项最小可交付闭环如下：

1. Joint report 能输出：
   - row completeness
   - technique evidence status
   - condition alignment status
   - cross-tech validation issue families
   - recommended next review target
2. Joint confidence context 能回答：
   - 当前冲突来自哪里。
   - 是单技术低可信，还是多技术真实不一致。
   - 哪些技术结果可以进入论文结论，哪些只能做诊断。
3. AI 调参能根据 Joint context 决定：
   - 先修 SAXS/WAXS/DSC/IR/NMR 单技术证据。
   - 还是提示用户进入 Joint compare。
4. 导出包能留下跨技术判断依据。

## 4. 任务清单

### K-T1. Joint 当前基线台账冻结

目标：冻结当前 Joint Hub 和 Joint AI context 表现。

主要落点：
- `polynexus/core/joint/dataset.py`
- `polynexus/core/joint/validation.py`
- `tests/test_joint_hub_dataset.py`
- `方案/PolyNexus 番外阶段K-T1 Joint当前基线台账.md`

最小输出：
- 当前 Joint row 支持的技术。
- 当前 opportunities。
- 当前 validations。
- 当前 `ai_context` 字段。
- 当前 GUI/导出会怎样表达 Joint。

验收标准：
- 不看 GUI 也能知道 Joint 当前能做哪些交叉验证，不能做哪些可信度判断。

### K-T2. Joint row evidence summary

目标：让 Joint row 不只看参数，还能看到每个技术的证据状态。

建议字段：
- `technique_evidence_status`
- `technique_confidence_level`
- `technique_risk_flags`
- `technique_constraint_status`
- `paper_conclusion_ready_by_technique`

主要落点：
- `polynexus/core/joint/dataset.py`
- `tests/test_joint_hub_dataset.py`

验收标准：
- Joint 可以区分“数值冲突”和“输入本身低可信”。

### K-T3. 结晶度一致性可信度加权

目标：DSC/WAXS/SAXS/IR/NMR 的 `Xc` 比较必须尊重来源语义。

规则：
- DSC/WAXS 可作为强结晶度来源，但仍受各自 evidence 约束。
- SAXS 未绝对标定时，`Xc_SAXS` 作为形态学/相对结晶度。
- IR 未标定时，作为 band index，不直接等价绝对结晶度。
- NMR assignment-limited 时，不作为强结晶度来源。

验收标准：
- Joint 不会把弱来源与强来源等权比较。
- `ai_context` 能说明某个 `Xc` 冲突是否被弱证据放大。

### K-T4. 条件轴和批次对齐可信度

目标：Joint 比较必须先确认这些结果属于同一样品、同一批次和可比条件。

建议字段：
- `row_condition_type`
- `row_condition_values`
- `condition_alignment_status`
- `mixed_condition_risk`
- `missing_condition_count`

验收标准：
- 条件不一致时，Joint 不直接给出强一致性结论。

### K-T5. Joint issue families 扩展

目标：把跨技术问题从简单 WARN/ERROR 变成可行动族群。

建议 issue families：
- `phi_c inconsistency`
- `Tm bidirectional gap`
- `L consistency unstable`
- `SAXS-WAXS scale mismatch`
- `IR calibration weak`
- `NMR assignment limited`
- `condition alignment weak`
- `single-tech evidence weak`

验收标准：
- `ai_context.issue_families` 能指导下一步优先修哪条线。

### K-T6. Joint AI / orchestrator 对齐

目标：单技术优化时能使用 Joint context，但不被 Joint context 盲目盖过。

主要落点：
- `polynexus/orchestrator.py`
- `rag/prompt_builder.py`
- `polynexus/gui/main_window.py`

验收标准：
- 若 Joint 冲突来自单技术低可信，AI 优先修单技术证据。
- 若单技术都可信但冲突仍在，AI 建议进入 Joint compare 或人工复核。

### K-T7. GUI / 导出可信度摘要

目标：让 Joint Hub、工作记忆和导出包留下跨技术可信度判断。

主要落点：
- `polynexus/gui/widgets/joint_analysis_hub.py`
- `polynexus/gui/main_window.py`
- `polynexus/core/report.py`

最小输出：
- Joint confidence summary。
- 主要 issue families。
- 推荐下一步复核目标。
- 不可直接作为论文结论的来源说明。

验收标准：
- 用户能看懂当前 Joint 是“整体一致”“局部冲突”“输入低可信”还是“条件不可比”。

### K-T8. 回归测试和导出验证

目标：保证 Joint 可信度链稳定。

建议测试：
- `test_joint_hub_report_surfaces_technique_evidence_status`
- `test_joint_context_downgrades_assignment_limited_nmr_xc`
- `test_joint_context_distinguishes_weak_single_tech_from_cross_tech_conflict`
- `test_joint_context_recommends_next_review_target`

验收标准：
- Joint targeted tests 通过。
- 不破坏现有 `test_joint_hub_dataset.py`、`test_orchestrator.py`、GUI persistence tests。

## 5. 推荐执行顺序

1. `K-T1` 冻结基线台账。
2. `K-T2` 接入单技术 evidence summary。
3. `K-T3` 修正结晶度一致性语义。
4. `K-T4` 补条件轴/批次对齐证据。
5. `K-T5` 扩展 issue families。
6. `K-T6` 接入 AI / orchestrator。
7. `K-T7` 补 GUI / 导出。
8. `K-T8` 回归收口。

这一阶段完成后，Joint 才能成为跨技术可信复核层，而不是只把多个结果放在同一张表里。
