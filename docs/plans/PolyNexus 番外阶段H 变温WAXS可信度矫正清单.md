# PolyNexus 番外阶段 H 变温 WAXS 可信度矫正清单

## 0. 当前问题定位

这份专项清单针对 `waxs.temperature`，也就是原位变温广角 WAXS。它不是静态 WAXS 清单的简单复制，因为变温 WAXS 多了一个关键维度：

**每一帧 WAXS 拟合要可信，整条温度序列的趋势也要可信。**

当前代码已经具备最小主流程：

1. `waxs.temperature` 子模块已经注册到 GUI 和评测体系。
2. `WAXSTempResult` 已经能记录：
   - `temperatures`
   - `Xc_vs_T`
   - `D_Scherrer_vs_T`
   - `peak_positions_vs_T`
   - `transitions`
3. `waxs_temperature.py` 已经能生成：
   - `Fig-WT1_2D_patterns`
   - `Fig-WT2_waterfall`
   - `Fig-WT3_temperature_parameters`
   - `Fig-WT4_peak_tracking`
   - `waxs_temperature_parameters.csv`
4. 真实评测 case 已经存在：
   - `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_w_0_00000.json`
   - `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_220_w_0_00000.json`
   - `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_205_w_0_00000.json`
   - `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_195_w_0_00000.json`
   - `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_185_w_0_00001.json`
   - `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_170_w_0_00002.json`

但当前可信度链还不够完整：

1. **温度轴只是被使用，还没有被充分审计**
   - 如果温度来自文件名、导入记录或默认递增序列，可信度不同。
   - 当前 `get_parameters()` 只给出 `T_range_C` 和 `n_temperatures`，还不够说明温度轴是否可靠。

2. **峰位追踪按峰序号记录，容易发生峰族身份交换**
   - `peak_positions_vs_T` 现在用 `enumerate(r.peaks)` 记录第 1 峰、第 2 峰。
   - 但温度升高时峰会消失、合并、偏移，单纯按列表序号可能把不同峰族串成同一条线。

3. **Xc / D 随温度变化还缺少物理约束**
   - `Xc_vs_T` 可能因为非晶背景变化被推高或压低。
   - `D_Scherrer_vs_T` 可能只是峰宽拟合副产物，不一定代表真实晶粒尺寸变化。
   - 熔融、冷结晶、重结晶等转变不应只靠 `Xc` 梯度突然变化判断。

4. **转变点检测还偏数值化**
   - 当前 `_detect_crystal_transitions()` 主要看 `dXc/dT`。
   - 但真实变温 WAXS 的转变应同时看峰族消失/出现、晶型峰比例、Xc 趋势、残差和温度轴。

5. **AI 调参还没有温变 WAXS 专属目标**
   - 静态 WAXS 的动作可以修峰位、峰数、背景和峰形。
   - 变温 WAXS 还要保证调参后整条趋势更可信，而不是某一帧更好看。


## 1. 专项目标

番外阶段 H 只解决一个问题：

**让 PolyNexus 在处理原位变温 WAXS 时，不只是生成 Xc-T、D-T 和峰位追踪图，而是能判断这些趋势是否由可靠的温度轴、峰族追踪和物理证据共同支撑。**

本专项希望完成 5 件事：

1. 把温度轴恢复、温度顺序、样品序列完整性纳入 evidence。
2. 把单帧 WAXS 可信度和温变序列趋势可信度拆开。
3. 建立峰族追踪证据，避免峰序号交换导致假趋势。
4. 让 AI 调参优先修“整条序列的证据链”，而不是追逐单帧高分。
5. 让 GUI 明确告诉用户：
   - 哪些图可以用于论文展示
   - 哪些趋势可以用于科研结论
   - 哪些结果只能作为诊断线索


## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕 `waxs.temperature` 建立专属可信度证据链
- 冻结真实变温 WAXS 样本基线
- 补温度轴 evidence
- 补峰族追踪 evidence
- 补 Xc / D / transition 趋势的物理约束
- 补变温 WAXS 专属 residual / symptom / action / rollback
- 让 GUI 把“单帧拟合可信”和“温度趋势可信”分开展示
- 保证论文图导出不带诊断水印，诊断信息在 GUI 和报告层呈现

### 2.2 本专项暂时不做什么

- 不重写整个 WAXS 拟合算法
- 不把静态 WAXS、拉伸 WAXS 和变温 WAXS 混成一个清单
- 不让 AI 自动替用户判定最终晶型机理
- 不为了让曲线更平滑而压低风险提示
- 不把 DSC / SAXS / WAXS 联合判据一次性做成最终版本
- 不在论文导出图上叠加 `low confidence` 之类水印


## 3. 最小闭环

本专项最小可交付闭环如下：

1. `core` 输出每一帧 WAXS 的拟合、峰、背景、结构证据。
2. `core` 输出整条温度序列的温度轴、峰族、Xc 趋势、D 趋势和转变证据。
3. 系统识别当前主要风险：
   - 温度轴缺失或混乱
   - 峰族追踪身份交换
   - 背景漂移驱动 Xc 假变化
   - 峰宽不稳导致 D 假趋势
   - 转变点缺少峰族支撑
4. `orchestrator` 只在白名单范围内做小步调参，并要求新候选同时改善单帧证据和序列证据。
5. GUI 把结果拆成：
   - 单帧拟合状态
   - 温度趋势状态
   - 主要风险
   - 可用于论文图的输出
   - 可用于科研结论的输出


## 4. 任务清单

### H-T1. 真实变温 WAXS 基线台账冻结

目标：
先把当前真实变温 WAXS case 的状态冻结下来，作为后续每次修正的对照基线。

主要落点：

- `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_w_0_00000.json`
- `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_pa6_250_170_w_0_00002.json`
- `D:\PolyNexus\polynexus\core\waxs.py`
- `D:\PolyNexus\polynexus\core\waxs_engine\waxs_temperature.py`
- 建议新增：`D:\PolyNexus\docs\baselines\PolyNexus 番外阶段H-T1 变温WAXS当前基线台账.md`

最小输出：

- 当前帧数、温度范围、温度来源
- 当前每帧 `r_squared / quality_score / n_peaks / Xc_pct / D_Scherrer_nm`
- 当前 `Xc_vs_T` 和 `D_Scherrer_vs_T` 的波动范围
- 当前峰族数量、峰位追踪是否连续
- 当前转变点数量和转变类型
- 当前 GUI 会如何解读这组结果

建议记录字段：

- `n_temperatures`
- `temperature_values`
- `temperature_source`
- `temperature_axis_confidence`
- `frame_pass_count`
- `frame_low_conf_count`
- `peak_family_count`
- `peak_family_identity_swap_count`
- `Xc_trend_support_score`
- `D_trend_support_score`
- `transition_support_score`
- `paper_figure_candidate`
- `paper_conclusion_candidate`

验收标准：

- 不看图也能知道这组变温 WAXS 当前坏在哪
- 后续每次修正都能和这份基线做对照

推荐模型：`mini`

当前状态：

- 已完成温度轴证据初版，温变结果对象和 `analysis_evidence` 现在能看见 `condition_source / condition_confidence / condition_continuity_score / temperature_axis_confidence`
- 已补回代表帧峰证据，不会因为序列摘要而把峰信息挤掉
- 已新增并通过回归测试：
  - `tests/test_waxs_temperature.py`
  - `tests/test_waxs_residual_analyzer.py`
  - `tests/test_analysis_evidence.py -k waxs`
  - `tests/test_orchestrator.py -k waxs`

当前状态：

- 基线台账已冻结，见 [PolyNexus 番外阶段 H-T1 变温WAXS当前基线台账.md](<D:/PolyNexus/docs/baselines/PolyNexus 番外阶段H-T1 变温WAXS当前基线台账.md>)
- 这份基线显示当前温变 WAXS 仍以 `peak_count_underfit` 为主，`physical_support_pass=False`，因此后续修复应从峰族和背景证据链入手，而不是先追图面顺眼度


### H-T2. 温度轴 evidence 补强

目标：
让系统知道温度轴是从哪里来的、是否连续、是否单调、是否可能混入了不同样品或不同升降温路径。

主要落点：

- `D:\PolyNexus\polynexus\core\waxs.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\tests\eval\runner.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\waxs_temperature_evidence.py`

建议 evidence 字段：

- `condition_label`
- `condition_unit`
- `temperature_values`
- `temperature_range_C`
- `temperature_source`
- `temperature_source_key`
- `temperature_missing_count`
- `temperature_duplicate_count`
- `temperature_monotonic`
- `temperature_step_median`
- `temperature_step_spread`
- `sequence_direction`
- `mixed_direction_risk`
- `condition_axis_confidence`

建议新增约束：

- `temperature_axis_missing`
- `temperature_axis_low_confidence`
- `temperature_sequence_nonmonotonic`
- `temperature_duplicate_frames`
- `temperature_step_irregular`
- `mixed_heating_cooling_sequence`
- `mixed_sample_temperature_series`

验收标准：

- 温度轴缺失时，不允许把 `Xc_vs_T` 解释成真实温度趋势
- 温度轴只是默认递增时，必须降级为诊断图
- 混合升温/降温时，不能直接拿一条曲线解释相变先后

推荐模型：`mini`


### H-T3. 单帧 WAXS evidence 复用与序列汇总

目标：
复用番外阶段 D 已经建立的静态 WAXS evidence，但把它汇总成 frame-level 序列质量。

主要落点：

- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\waxs_engine\core.py`
- `D:\PolyNexus\polynexus\core\waxs_engine\waxs_temperature.py`

最小输出：

- `frame_evidence`
- `frame_quality_distribution`
- `frame_constraint_summary`
- `low_conf_frame_indices`
- `low_conf_temperature_values`
- `dominant_frame_failure_type`

建议汇总字段：

- `frame_count`
- `valid_frame_count`
- `failed_frame_count`
- `median_r_squared`
- `median_peak_count`
- `median_structure_support_score`
- `peak_visibility_pass_ratio`
- `background_stability_pass_ratio`
- `physical_support_pass_ratio`

验收标准：

- 系统能区分“某一帧不好”和“整条温变序列都不稳”
- 只有少数坏帧时，后续动作可以考虑标记 outlier
- 多数帧坏时，不能靠平滑趋势来假装可信

推荐模型：`mini`


### H-T4. 峰族追踪 evidence 设计

目标：
让 `peak_positions_vs_T` 从“第几个峰的位置”升级成“同一物理峰族随温度的追踪”。

主要落点：

- `D:\PolyNexus\polynexus\core\waxs_engine\waxs_temperature.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\waxs_peak_tracker.py`

建议 evidence 字段：

- `peak_family_count`
- `peak_family_tracks`
- `peak_family_assignment_method`
- `peak_family_continuity_score`
- `peak_family_missing_frame_count`
- `peak_family_identity_swap_count`
- `peak_position_drift_per_family`
- `peak_width_drift_per_family`
- `peak_area_drift_per_family`
- `new_peak_birth_temperatures`
- `peak_disappearance_temperatures`

建议新增约束：

- `peak_family_identity_swap`
- `peak_family_track_fragmented`
- `peak_family_missing_too_many_frames`
- `peak_position_drift_unphysical`
- `peak_width_trend_unstable`
- `phase_transition_without_peak_family_support`

判据建议：

- 峰族追踪不能只按 `r.peaks` 列表序号。
- 应优先按 2θ 邻近、d-spacing 连续、峰宽连续、峰面积连续做匹配。
- 若两个峰族交叉或合并，应标记为 `identity_ambiguous`，不要强行串线。

验收标准：

- `Fig-WT4_peak_tracking` 中的每条线都有峰族证据支撑
- 峰族身份不稳时，峰位追踪图仍可出，但结论必须降级

推荐模型：`5.4`


### H-T5. Xc-T 趋势物理约束

目标：
判断 `Xc_vs_T` 是真实结晶度趋势，还是背景扣除、峰数变化、温度轴或拟合不稳造成的假趋势。

主要落点：

- `D:\PolyNexus\polynexus\core\waxs_engine\waxs_temperature.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\waxs_residual_analyzer.py`

建议 evidence 字段：

- `Xc_values`
- `Xc_initial_pct`
- `Xc_final_pct`
- `Xc_range_pct`
- `Xc_slope_distribution`
- `Xc_trend_monotonicity`
- `Xc_background_sensitivity`
- `Xc_peak_support_ratio`
- `Xc_transition_candidates`
- `Xc_trend_support_score`

建议新增约束：

- `crystallinity_trend_without_peak_support`
- `crystallinity_jump_single_frame`
- `crystallinity_background_driven`
- `crystallinity_trend_conflicts_with_peak_area`
- `crystallinity_outside_physical_range`
- `melting_trend_without_peak_disappearance`
- `cold_crystallization_without_new_peak_support`

判据建议：

- 熔融趋势不应只看 `Xc` 下降，还应看到主要晶峰面积下降或消失。
- 冷结晶趋势不应只看 `Xc` 上升，还应看到峰面积增强或新峰出现。
- 单帧突跳只能先标记为 anomaly，不能直接标记为 phase transition。

验收标准：

- `Xc-T` 图可以直接告诉用户“趋势可信 / 仅供诊断 / 不建议解释”
- AI 不能通过改背景参数把 `Xc` 曲线调顺后就自动提升置信度

推荐模型：`5.4`


### H-T6. D-Scherrer-T 趋势物理约束

目标：
判断 `D_Scherrer_vs_T` 是否代表真实晶粒尺寸变化，还是峰宽拟合、仪器展宽、峰重叠或噪声造成的副产物。

主要落点：

- `D:\PolyNexus\polynexus\core\waxs_engine\waxs_temperature.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\waxs_residual_analyzer.py`

建议 evidence 字段：

- `D_values_nm`
- `D_range_nm`
- `D_slope_distribution`
- `D_support_peak_count`
- `D_support_family_count`
- `FWHM_values_by_family`
- `instrument_broadening_present`
- `D_trend_support_score`
- `D_confidence_by_frame`

建议新增约束：

- `scherrer_trend_without_multi_peak_support`
- `scherrer_jump_single_frame`
- `scherrer_dominated_by_peak_width_noise`
- `scherrer_instrument_broadening_unresolved`
- `scherrer_conflicts_with_peak_family_tracking`
- `scherrer_unphysical_temperature_trend`

判据建议：

- 如果只有一个弱峰支撑 `D`，D-T 只能作为诊断趋势。
- 如果峰宽随温度的变化和残差类型强相关，应优先怀疑拟合而不是真实晶粒变化。
- 没有仪器展宽信息时，绝对 D 值要保守，趋势解释也要降级。

验收标准：

- 用户不会把一条漂亮的 `D-T` 线直接当成晶粒尺寸真实演化
- GUI 能明确区分“D 图可画”和“D 结论可写”

推荐模型：`mini`


### H-T7. 相变 / 晶型转变 evidence 升级

目标：
让 `transitions` 从单纯 `dXc/dT` 触发，升级为多证据共同支撑的候选转变点。

主要落点：

- `D:\PolyNexus\polynexus\core\waxs_engine\waxs_temperature.py`
- `D:\PolyNexus\polynexus\data\polymers.json`
- `D:\PolyNexus\rag\polymer_knowledge.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议 evidence 字段：

- `transition_candidates`
- `transition_type`
- `transition_temperature_C`
- `transition_support_frames`
- `transition_support_peak_families`
- `phase_marker_peak_changes`
- `Xc_change_support`
- `D_change_support`
- `polymer_reference_window`
- `transition_support_score`

建议新增约束：

- `transition_single_frame_only`
- `transition_without_peak_family_support`
- `transition_temperature_outside_reference_window`
- `phase_claim_without_marker_peaks`
- `polymorph_transition_without_peak_ratio_change`
- `melting_claim_without_Xc_and_peak_loss_agreement`

判据建议：

- PA6 这类材料如果要谈 alpha/gamma 晶型变化，应优先看特征峰族和峰面积比例，而不是只看总 Xc。
- 转变点至少需要相邻多帧支撑。
- 超出已知材料参考窗口时，不应自动给出明确相变结论。

验收标准：

- GUI 中的转变点不再只是“Xc 梯度异常”
- AI 输出必须说清楚这个转变由哪些峰族、哪些温度点支撑

推荐模型：`5.4`


### H-T8. 变温 WAXS 症状到动作桥接

目标：
让 agent 能针对变温 WAXS 的真实问题做受控调参，而不是照搬静态 WAXS 的参数动作。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\saxs_action_registry.py`
- `D:\PolyNexus\polynexus\config_bridge.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\waxs_temperature_action_registry.py`

建议动作：

1. `recover_temperature_axis`
   - 目标症状：`temperature_axis_missing`, `temperature_axis_low_confidence`
   - 预期改善：温度缺失减少，`condition_axis_confidence` 上升

2. `split_temperature_series`
   - 目标症状：`mixed_heating_cooling_sequence`, `mixed_sample_temperature_series`
   - 预期改善：每条序列内部温度方向一致，样品一致

3. `stabilize_peak_family_tracking`
   - 目标症状：`peak_family_identity_swap`, `peak_family_track_fragmented`
   - 可调方向：峰匹配容差、峰族最小连续帧数、峰位漂移阈值

4. `rebalance_temperature_background`
   - 目标症状：`crystallinity_background_driven`, `amorphous_background_bias`
   - 可调参数：`background_method`, `amorphous_subtraction`, `amorphous_n_peaks`

5. `stabilize_temperature_peak_shape`
   - 目标症状：`scherrer_dominated_by_peak_width_noise`, `peak_width_trend_unstable`
   - 可调参数：`peak_function`, `smooth_window`

6. `mark_temperature_frame_outlier`
   - 目标症状：`crystallinity_jump_single_frame`, `scherrer_jump_single_frame`
   - 预期改善：趋势连续性上升，但不应隐藏真实转变点

动作约束：

- 每轮只改 1-2 个参数或一个序列操作。
- 优先修温度轴和峰族追踪，再修 Xc / D 趋势。
- 若新候选只改善单帧拟合，却破坏序列趋势，必须回滚。
- 不允许为了让曲线平滑而删除真实转变帧。

验收标准：

- agent 的建议能明确说明“修的是温度轴、峰族、背景、峰宽，还是异常帧”
- 每个动作都有对应 evidence 变化目标

推荐模型：`5.4`


### H-T9. 接受 / 回滚规则升级

目标：
让变温 WAXS 的候选结果必须同时满足单帧可信度和序列可信度，才能替换当前推荐结果。

主要落点：

- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

建议比较项：

- `frame_low_conf_count`
- `median_structure_support_score`
- `condition_axis_confidence`
- `peak_family_continuity_score`
- `peak_family_identity_swap_count`
- `Xc_trend_support_score`
- `D_trend_support_score`
- `transition_support_score`
- `triggered_constraint_count`

建议新增回滚条件：

- `temperature_axis_confidence_worsened`
- `peak_family_tracking_worsened`
- `Xc_trend_support_collapsed`
- `D_trend_support_collapsed`
- `transition_support_weakened`
- `frame_fit_improved_but_sequence_worsened`
- `trend_smoothed_by_outlier_suppression`

验收标准：

- 新结果必须能说明比基线强在哪里
- 只让图更平滑、但削弱物理证据的候选会被拒绝
- 被拒绝的候选会留下清楚的原因，方便用户复核

推荐模型：`5.4`


### H-T10. GUI 结果语义拆分

目标：
让用户在变温 WAXS 页面上清楚理解这组数据到底能支持什么，不能支持什么。

主要落点：

- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\convergence_viewer.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

建议界面区块：

- 温度序列
  - 帧数、温度范围、温度来源、温度轴可信度
- 单帧拟合
  - 通过帧数、低置信帧、主要残差类型
- 峰族追踪
  - 峰族数量、连续性、身份交换风险
- 趋势可信度
  - Xc-T 可信度、D-T 可信度、转变点支撑
- 论文输出状态
  - 图可用于展示
  - 趋势仅供诊断
  - 结论需要人工复核

建议文案语义：

- `Temperature axis verified`
- `Peak family tracking limited`
- `Xc trend supported`
- `Scherrer trend diagnostic only`
- `Transition candidate, not final phase assignment`
- `Figure export ready`
- `Conclusion pending review`

验收标准：

- 用户不会把 waterfall 图和趋势图自动理解成“结果已经可信”
- 诊断提示不压在论文图上，而是在 GUI / 报告 / convergence 面板里解释
- 用户能一眼知道下一步该修温度轴、峰族、背景还是峰宽

推荐模型：`mini`


### H-T11. 真实样本回归验证

目标：
确保变温 WAXS 可信度链能解释真实 PA6 原位变温广角数据，而不是只在合成数据上成立。

主要落点：

- `D:\PolyNexus\tests\eval\cases\real\waxs_real_temperature_*.json`
- `D:\PolyNexus\tests\test_analysis_evidence.py`
- `D:\PolyNexus\tests\test_orchestrator.py`
- `D:\PolyNexus\tests\test_waxs_residual_analyzer.py`
- 建议新增：
  - `D:\PolyNexus\tests\test_waxs_temperature_evidence.py`
  - `D:\PolyNexus\tests\test_waxs_temperature_orchestrator.py`
  - `D:\PolyNexus\tests\test_waxs_temperature_confidence_contract.py`

最小验证内容：

- 真实变温 WAXS case 能稳定识别为 `waxs.temperature`
- 温度轴 evidence 可用
- 单帧 evidence 能汇总成序列 evidence
- 峰族追踪能识别连续、缺失和身份交换
- Xc / D 趋势约束能稳定命中
- orchestrator 能优先修温度轴和峰族问题
- GUI 能区分“图可出”和“结论可写”

验收标准：

- 即使结果暂时不能完全修好，系统也能把原因讲对
- 如果后续某轮真的变好，系统能明确证明“比基线更可信”
- 真实样本回归不破坏静态 WAXS、温变 SAXS、IR、DSC 已有可信度链

推荐模型：`mini`


### H-T12. DSC / SAXS 联合校验预留

目标：
为后续 joint 分析预留变温 WAXS 的跨技术可信度接口，但不在本专项里一次性完成全量 joint。

主要落点：

- `D:\PolyNexus\polynexus\core\joint\comparators.py`
- `D:\PolyNexus\polynexus\data\polymers.json`
- `D:\PolyNexus\rag\polymer_knowledge.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`

预留字段：

- `waxs_transition_temperatures_C`
- `waxs_melting_candidate_C`
- `waxs_cold_crystallization_candidate_C`
- `waxs_Xc_trend`
- `waxs_peak_family_transition_support`
- `dsc_transition_overlap_score`
- `saxs_long_period_overlap_score`

验收标准：

- WAXS 不单独硬判最终热转变
- DSC / SAXS 可在后续作为外部证据确认或反驳 WAXS 趋势

推荐模型：`mini`


## 5. 推荐推进顺序

建议按这个顺序推进：

1. `H-T1` 真实变温 WAXS 基线台账冻结
2. `H-T2` 温度轴 evidence 补强
3. `H-T3` 单帧 WAXS evidence 复用与序列汇总
4. `H-T4` 峰族追踪 evidence 设计
5. `H-T5` Xc-T 趋势物理约束
6. `H-T6` D-Scherrer-T 趋势物理约束
7. `H-T7` 相变 / 晶型转变 evidence 升级
8. `H-T8` 变温 WAXS 症状到动作桥接
9. `H-T9` 接受 / 回滚规则升级
10. `H-T10` GUI 结果语义拆分
11. `H-T11` 真实样本回归验证
12. `H-T12` DSC / SAXS 联合校验预留

这样排的原因：

- 前三项先让数据和证据说真话。
- `H-T4` 到 `H-T7` 再补变温 WAXS 独有的物理判据。
- `H-T8` 和 `H-T9` 再让 AI 进入受控调参闭环。
- 最后用 GUI 和真实样本回归收口，避免只停留在算法层。


## 6. 模型使用建议

适合 `mini` 的任务：

- `H-T1` 基线台账
- `H-T2` 温度轴字段和基础约束
- `H-T3` 单帧 evidence 汇总
- `H-T6` D-T 趋势基础约束
- `H-T10` GUI 文案和展示结构
- `H-T11` 测试补齐和回归验证
- `H-T12` joint 字段预留

更适合 `5.4` 的任务：

- `H-T4` 峰族追踪身份匹配
- `H-T5` Xc-T 趋势和背景耦合判据
- `H-T7` 相变 / 晶型转变多证据判据
- `H-T8` 症状到动作桥接
- `H-T9` 接受 / 回滚规则

简单说：

- 字段、台账、GUI、测试，可以继续用 `mini`。
- 一旦涉及“峰族身份追踪、趋势物理约束、调参接受规则”，建议用 `5.4`。


## 7. 这一阶段完成后的产品变化

完成番外阶段 H 后，PolyNexus 的变温 WAXS 不应该只是：

> 生成一张 waterfall 图、一张 Xc-T 图、一张 D-T 图和一张 peak tracking 图。

而应该升级成：

> 这组原位变温 WAXS 的温度轴可信；12 帧中 10 帧单帧拟合可靠；主峰族连续性良好；Xc 下降由峰面积衰减支撑；D-T 目前仍受峰宽噪声影响，只能作为诊断趋势；220-250 C 的转变是候选熔融区间，建议结合 DSC 确认。

也就是说，软件要能把三件事分开讲清楚：

1. **图能不能出**
2. **趋势能不能解释**
3. **结论能不能写进论文**

这条线做好后，变温 WAXS 才能真正和前面的温变 SAXS、静态 WAXS、DSC、IR 可信度链接起来，成为你想要的“带 agent 行为的专业分析工作台”的一部分。
