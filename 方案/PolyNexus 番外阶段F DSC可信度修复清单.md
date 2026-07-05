# PolyNexus 番外阶段F DSC可信度修复清单

## 0. 当前问题定位

这份专项清单不是为了把 DSC 再“调得更好看”，而是先把 DSC 当前到底靠什么站住、哪些结果只是拟合产物、哪些结论还不够稳这几件事讲清楚，再把 `core -> residual -> analysis_evidence -> orchestrator -> GUI` 这条链补齐。

当前 DSC 这条线已经有基础，但可信度链仍然偏薄：

1. `core` 已经能跑标准 DSC、等温、非等温的主流程，也能输出 `Tg / Tm / Tc / Xc / DHm / DHc / DHcc / quality_score / r_squared / peak_components`
2. `analysis_evidence.py` 里 DSC 目前还是偏“结果型”，还没有像 WAXS / IR 那样把证据层拆细
3. `DSCResidualAnalyzer` 现在只会分 `random / baseline_drift / peak_shift`，对真实热流问题还不够贴近
4. `orchestrator` 的 DSC 交叉检查目前仍然偏浅，更多是“有没有 Tm / Xc”，还不是“这些值是否真的站得住”
5. `config_bridge` 已经有一部分 DSC 白名单，但像 `exo_up`、`Tg_search_low_C`、`Tg_search_high_C` 这类关键控制项还没完全进入可调链
6. GUI 还没有把 DSC 的“测得值 / 推断值 / 可直接写论文的结论”拆开
7. 当前 `tests/eval/cases/real` 里还没有单独的 DSC real case，后续需要先补一个可冻结的真实样本基线

所以这次 DSC 专项要解决的核心问题不是“分数更高”，而是：

**让 PolyNexus 在处理 DSC 时，能诚实地区分测得事件、拟合结果、热力学结论和论文级结论。**

## 1. 专项目标

番外阶段 F 只解决一个问题：

**让 PolyNexus 在 DSC 上形成一条更可信的证据链，让 agent 围绕真实热流问题做受控调参，而不是围绕一个看起来不错的分数打转。**

这一阶段完成后，DSC 板块至少要做到：

1. 用户能看懂这次结果到底是测得的、拟合出来的，还是推断出来的
2. 系统能判断当前主要问题是基线、温区、峰检测、极性、还是跨扫描不一致
3. agent 只能在白名单内做小步受控尝试，不能乱改结论
4. GUI 能明确告诉用户当前结果适不适合直接用于论文

## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕 **标准 DSC** 先把可信度链补齐
- 把 evidence 分层做出来
- 把残差语义做得更贴近真实 DSC 问题
- 把症状到参数动作的桥接做成受控闭环
- 把接收 / 回滚规则从“分数更高”升级成“证据更稳”
- 把 GUI 语义拆成“测得值 / 推断值 / 论文可用性”
- 先补一条真实样本基线，再继续迭代

### 2.2 本专项不做什么

- 不重写整条 DSC 物理引擎
- 不把 mDSC / flash / 复杂动力学一次性全拉进来
- 不让 AI 直接替用户拍最终热力学结论
- 不用“分数更高”掩盖掉基线、极性、温区、事件支撑不稳的问题
- 不做独立聊天式 agent 主界面

## 3. 最小闭环

本专项的最小闭环是：

1. `core` 输出完整的 DSC 事件与质量证据
2. `analysis_evidence` 把测得值、推断值、支撑值拆开
3. `residual_analyzer` 能说清当前是基线问题、事件问题、极性问题，还是噪声问题
4. `orchestrator` 只围绕白名单里的 DSC 参数做小步受控尝试
5. 接收 / 回滚规则按证据变化决定，而不是按单一 `r_squared` 决定
6. GUI 清楚标出哪些结果能出图，哪些结果还能再试，哪些结果暂不适合直接下结论

只要这条链打通，DSC 板块就会更像一个诚实的专业分析工作台。

## 4. 任务清单

### F-T1. 真实样本基线台账冻结

目标：
先冻结 1 条代表性的 DSC 真实样本，把当前状态做成后续每次修正的对照基线。

主要落点：
- `D:\PolyNexus\测试数据\dsc\标准DSC数据格式一\FXY-PA6.txt`
- `D:\PolyNexus\测试数据\dsc\标准DSC数据格式二\30.xls`
- `D:\PolyNexus\tests\eval\cases\real\dsc_real_standard_pa6.json`（如还没有，先补一个）
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\dsc_residual_analyzer.py`
- `D:\PolyNexus\polynexus\orchestrator.py`

最小输出：
- 当前 `Tg_C / Tm_peak_C / Tc_peak_C / Tcc_peak_C / DHm_Jg / DHc_Jg / DHcc_Jg / Xc_pct`
- 当前 `quality_score / scan_r_squared / n_peaks / peak_components`
- 当前残差类型与最大残差区域
- 当前峰数量、峰位、峰宽是否稳定
- 当前 GUI 会如何解读这组结果

建议记录字段：
- `scan_mode`
- `event_count`
- `significant_event_count`
- `dominant_event_type`
- `quality_score`
- `scan_r_squared`
- `baseline_corr`
- `Tg_method`
- `paper_ready_candidate`

验收标准：
- 不看图也能说清这条 DSC 现在主要稳不稳
- 后续每一次修正都能和这份基线对比

推荐模型：`mini`


### F-T2. DSC evidence 分层补强

目标：
把当前 DSC 还偏薄的 evidence 层，补成真正能支撑可信度判断的分层结构。

主要落点：
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\orchestrator.py`

建议拆分为：
- `scan_evidence`
- `event_evidence`
- `baseline_evidence`
- `crystallinity_evidence`
- `validation_evidence`
- `calibration_evidence`

建议至少补齐的字段：
- `scan_mode`
- `is_heating`
- `is_cooling`
- `isothermal_segment`
- `baseline_corr`
- `smooth_window`
- `Tg_method`
- `Tg_search_low_C`
- `Tg_search_high_C`
- `Tm_search_low_C`
- `Tm_search_high_C`
- `Tc_search_low_C`
- `Tc_search_high_C`
- `peak_prominence_ratio`
- `min_event_enthalpy_Jg`
- `max_melting_peak_width_C`
- `n_detected_events`
- `n_significant_events`
- `peak_components_count`
- `quality_flags`
- `scan_r_squared`
- `quality_score`
- `DHm0_source`
- `DHm0_value`

验收标准：
- `analysis_evidence` 不再只是“有几个结果值”
- GUI 和 agent 都能看懂“这个结果是靠什么支撑的”

推荐模型：`mini`


### F-T3. DSC 物理约束升级

目标：
把当前只偏结果分数的 DSC 约束，升级成能贴近真实热流问题的可信度门槛。

主要落点：
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\tests\test_analysis_evidence.py`
- 如有必要再补 `D:\PolyNexus\tests\test_dsc_engine.py`

建议新增约束：
- `baseline_sensitive_result`
- `Tg_without_DCp_step`
- `Tg_outside_supported_window`
- `melting_without_supported_event`
- `cold_crystallization_conflicts_with_melting`
- `event_polarity_conflict`
- `peak_components_too_sparse`
- `peak_width_nonphysical`
- `multi_scan_inconsistent`
- `crystallinity_without_event_support`
- `quality_score_without_event_support`

建议保留并强化：
- `quality_score`
- `scan_r_squared`

验收标准：
- 高分结果不能再越过明显的事件支撑不足
- 结论低可信时，系统会保守保留，不硬抬

推荐模型：`mini`


### F-T4. DSC 残差语义细化

目标：
把当前过于粗的残差分类，改成更贴近 DSC 真实问题的症状层。

主要落点：
- `D:\PolyNexus\polynexus\core\dsc_residual_analyzer.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\dsc_symptom_detector.py`

建议新增或细化的残差类型：
- `baseline_drift_low_T`
- `baseline_drift_high_T`
- `Tg_step_missing`
- `melting_peak_shift`
- `cold_crystallization_overlap`
- `event_window_too_narrow`
- `event_window_too_wide`
- `exo_up_down_confusion`
- `noise_dominant`
- `segment_split_issue`
- `multi_event_underfit`

当前可保留为兜底：
- `random`

验收标准：
- 系统能区分“是基线问题，还是事件窗口问题，还是极性/噪声问题”
- 不再只会说“残差不太对”

推荐模型：`mini`


### F-T5. 症状到参数动作桥接

目标：
让 DSC 的真实问题稳定映射到白名单动作，而不是让 AI 自由试参数。

主要落点：
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\config_bridge.py`
- 如有必要新增：`D:\PolyNexus\polynexus\core\dsc_action_registry.py`

建议优先级：
1. 基线 / 噪声问题
   - `baseline_corr`
   - `smooth_window`
2. 极性 / 方向问题
   - `exo_up`
3. Tg 不稳
   - `Tg_method`
   - `Tg_search_low_C`
   - `Tg_search_high_C`
4. Tm / Tc 温区不稳
   - `Tm_search_low_C`
   - `Tm_search_high_C`
   - `Tc_search_low_C`
   - `Tc_search_high_C`
5. 弱事件 / 误检
   - `peak_prominence_ratio`
   - `min_event_enthalpy_Jg`
6. 多峰熔融 / 事件过宽
   - `peak_function`
   - `max_melting_peak_width_C`

建议先补齐但当前未完全进入白名单的 DSC 控制项：
- `exo_up`
- `Tg_search_low_C`
- `Tg_search_high_C`

动作约束：
- 每轮只改 1-2 个参数
- 先修基线和噪声，再动事件阈值，再动温区
- 不允许把“只是更顺眼”的结果当成真正变可信

验收标准：
- 调参路径更像“针对问题修”，而不是“看到分数不高就试试”
- 被拒绝的参数组合能形成清晰历史，不会来回打转

推荐模型：`5.4`


### F-T6. 接收 / 回滚规则升级

目标：
让 DSC 的收敛规则从“分数更高就更好”，升级成“事件支撑、基线稳定、跨扫描一致共同改善才算更好”。

主要落点：
- `D:\PolyNexus\polynexus\orchestrator.py`
- `D:\PolyNexus\polynexus\core\analysis_evidence.py`
- `D:\PolyNexus\polynexus\core\joint\validation.py`

建议新增比较项：
- `quality_score`
- `scan_r_squared`
- `triggered_constraint_count`
- `event_support_score`
- `baseline_stability_score`
- `thermal_consistency_score`
- `crystallinity_support_score`
- `cross_validation_summary`

建议新增回滚条件：
- `event_support_weakened`
- `baseline_became_less_stable`
- `temperature_window_conflict_worsened`
- `crystallinity_claim_without_event_support`
- `multi_scan_consistency_broke`
- `cross_validation_conflict_worsened`

建议顺手补强的交叉检查：
- `phi_c` 三重验证（DSC / WAXS / SAXS）
- `Tm` 与 SAXS 的双向校验
- `Xc` 与 WAXS / SAXS 的一致性摘要

验收标准：
- 新结果必须在证据上也更可信，才允许替换当前推荐结果
- “更好看但更空”的结果会自动回滚

推荐模型：`5.4`


### F-T7. GUI 结果语义拆分

目标：
让用户一眼看懂当前 DSC 页里，什么是测得的，什么是推断的，什么还不适合直接写进论文。

主要落点：
- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`

最小界面结构建议：
- 当前检测到的热事件
- 当前基线可信度
- 当前结晶度估计
- 当前主要风险
- 当前是否适合论文出图
- 当前是否还需要人工复核

建议文案语义：
- `Measured thermal events`
- `Baseline support`
- `Crystallinity estimate`
- `Conclusion pending`
- `Figure usable, conclusion pending`

验收标准：
- 用户不会把“有 Tm / Xc”自动理解成“结论已经完全稳了”
- GUI 不再只是把数值堆出来，而是能讲清楚当前证据状态

推荐模型：`mini`


### F-T8. 真实样本回归验证

目标：
让这条 DSC 修复链不只在合成 case 上成立，也能解释真实样本为什么可信或为什么不可信。

主要落点：
- `D:\PolyNexus\tests\test_dsc_engine.py`
- `D:\PolyNexus\tests\test_dsc_bridge.py`
- `D:\PolyNexus\tests\test_analysis_evidence.py`
- 如有必要新增：
  - `D:\PolyNexus\tests\test_dsc_residual_analyzer.py`
  - `D:\PolyNexus\tests\test_dsc_confidence_contract.py`
  - `D:\PolyNexus\tests\eval\cases\real\dsc_real_standard_pa6.json`

最小验证内容：
- 真实样本当前为何低可信 / 中可信
- evidence 是否已拆成多层
- symptom 是否能稳定命中
- orchestrator 是否优先修基线、温区、事件阈值
- GUI 是否明确区分“可出图”和“可下结论”

验收标准：
- 即使结果暂时还不能完全修好，系统也能把原因讲对
- 若后续某轮真的修好，系统能明确证明“比基线更可信”

推荐模型：`mini`


## 5. 推荐推进顺序

建议按这个顺序做：

1. `F-T1` 先冻结一条真实 DSC 基线
2. `F-T2` 再把 evidence 分层补起来
3. `F-T3` 接着补物理约束门槛
4. `F-T4` 然后细化残差语义
5. `F-T5` 再做症状到动作桥接
6. `F-T6` 收紧接收 / 回滚规则
7. `F-T7` 最后把 GUI 语义拆清楚
8. `F-T8` 用真实样本回归收口

## 6. 完成后的产品变化

做完这份清单后，DSC 板块应该更像一个可靠的专业分析工作台，而不是一套只会报数的分析器：

1. 用户能看懂当前结果是怎么来的
2. agent 能围绕真实热流问题调参，而不是围绕分数打转
3. GUI 能把测得值、推断值、论文结论拆开
4. 遇到不够好的数据时，系统会保守保留低可信，而不是硬抬
5. 后面如果要和 WAXS / SAXS 联动，这条证据链也能直接复用

## 7. 我对 DSC 这条线的判断

DSC 的核心问题不是“出不出数”，而是：

**当前这组数到底是一个已经站稳的热力学结论，还是一个还需要基线、极性、温区和跨扫描一致性一起站稳的中间结果。**

所以这份清单的优先级不是先把 agent 做得更会说，而是先把：

- 事件证据
- 基线证据
- 结晶度证据
- 交叉一致性证据

这四层真正搭起来。
