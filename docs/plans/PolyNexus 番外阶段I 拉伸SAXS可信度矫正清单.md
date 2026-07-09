# PolyNexus 番外阶段 I 拉伸SAXS可信度矫正清单

## 0. 当前问题定位

这份专项清单针对 `saxs.strain`，也就是原位拉伸 SAXS。

它不是温变 SAXS 清单的简单平移，因为拉伸小角多了几层更容易混淆的物理语义：

1. 同一组数据里，`低 q 空穴散射`、`层状长周期 Bragg 峰`、`取向增强后的各向异性变化` 可能同时出现。
2. 曲线看起来“更顺”不等于层状参数真的更可信，很多时候只是把空穴上翘、beamstop 污染或窗口选择问题抹平了。
3. 对拉伸序列来说，`L_nm`、`lc_nm`、`la_nm`、`Xc`、`Q_star_rel`、`phase` 并不都属于同一层语义：
   - 有的是直接测得值
   - 有的是相对校准后的有效值
   - 有的是诊断值
4. 如果这几层语义混在一起，AI 和用户都容易误以为：
   - “图已经平滑了，所以层状厚度趋势可信”
   - “phase 已经切出来了，所以空穴/微纤化判断就成立”

当前代码已经具备拉伸 SAXS 的主流程，但可信度链还不够完整：

1. `saxs.strain` 已在 [D:\PolyNexus\polynexus\core\saxs.py](D:\PolyNexus\polynexus\core\saxs.py) 注册，能自动识别拉伸目录并进入专属分支。
2. `_parse_strain_from_filename()` 当前主要依赖文件名模式 `-(数字)-S_`，默认只给到中等置信度。
3. `_run_strain_pipeline()` 已经会写出：
   - `strain_pct`
   - `L_nm`
   - `lc_nm`
   - `la_nm`
   - `Xc`
   - `Q_star`
   - `Q_rel`
   - `lc_confidence`
   - `lc_method`
4. [D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py](D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py) 已经具备：
   - 四阶段识别 `detect_strain_phase()`
   - 空穴检测 `detect_voids()`
   - Herman 取向因子
   - 拉伸序列逐帧分析 `analyze_strain_series()`
5. 但现在最需要补的，不是“再多出几张图”，而是把下面这条证据链补完整：

**应变轴是否可信 -> 低 q 是否被空穴/beamstop 主导 -> 长周期锚点是否仍代表层状结构 -> `lc/Xc` 属于测得值还是有效值 -> phase 是否真有足够证据支撑**


## 1. 专项目标

番外阶段 I 只解决一个问题：

**让 PolyNexus 在处理原位拉伸 SAXS 时，能够清楚区分“测到了什么”“推断了什么”“哪些趋势还不能拿来下科研结论”，并让 AI 的调参动作优先修物理证据链，而不是先修图面平滑度。**

本专项希望完成 5 件事：

1. 把 `strain axis` 从“被使用”升级到“被审计”。
2. 把 `raw / effective / diagnostic` 三层参数语义拆开。
3. 把“空穴低 q 信号误判为层状长周期”变成系统可识别的专项症状。
4. 把四阶段识别从“有结果”升级到“有证据支撑的结果”。
5. 让 GUI、AI 调参闭环和最终导出都能诚实表达这组拉伸 SAXS 数据当前究竟可信到哪一步。


## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕 `saxs.strain` 建立独立的可信度证据链
- 冻结真实拉伸 SAXS 基线样本
- 补强应变轴恢复与应变序列完整性 evidence
- 拆分 `L / lc / la / Xc / Q* / Q*_rel` 的语义层次
- 增加“空穴/低 q 上翘 vs 层状峰锚点混淆”专项症状
- 增加四阶段识别的证据与回退规则
- 约束 AI 先修低 q、峰锚点和序列语义，再考虑接受层状参数趋势
- 让 GUI 明确区分：
  - 论文可直接用的图
  - 可作为科研趋势参考的图
  - 仅可作为诊断线索的图和参数

### 2.2 本专项暂时不做什么

- 不重写整条 SAXS 基础算法
- 不把拉伸 SAXS 和温变 SAXS 混成一份清单
- 不为了让结果“好看”去硬抬 `Low Confidence`
- 不让 AI 替用户做最终科研判断
- 不在论文导出图上叠加诊断水印
- 不把拉伸 WAXS、DSC、IR 的联动判断一次性并进这一阶段


## 3. 最小闭环

本专项最小可交付闭环如下：

1. `core` 输出拉伸序列逐帧证据：
   - 应变轴来源与置信度
   - 长周期锚点来源
   - 低 q / 空穴风险
   - 相对不变量变化
   - 原始层状参数与有效层状参数
   - phase 支撑证据
2. `symptom` 能明确识别当前主要风险：
   - 应变轴缺失或不可信
   - 低 q 空穴/beamstop 主导
   - 长周期锚点已偏离层状峰
   - `Q_star_rel` 只适合做相对有序度解释
   - phase 结论缺少足够支撑
3. `orchestrator` 只做小范围、白名单式修正：
   - 先修应变轴
   - 再修低 q / Bragg / correlation 窗口
   - 再判断是否接受 `lc/Xc` 趋势
4. 系统按证据改善而不是按曲线是否平滑来决定接受或回滚。
5. GUI 最终能让用户一眼看懂：
   - 哪些值是测得的
   - 哪些值是相对/有效值
   - 哪些值现在还不能直接当论文结论


## 4. 任务清单

### I-T1. 真实拉伸 SAXS 基线台账冻结

目标：
先冻结一条真实 `saxs.strain` case 的当前状态，作为后续每次修正的对照基线。

主要落点：
- 已新增真实 case：`D:\PolyNexus\tests\eval\cases\real\saxs_real_strain_pad8_series.json`
- `D:\PolyNexus\polynexus\core\saxs.py`
- `D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py`
- 已补台账：`D:\PolyNexus\docs\baselines\PolyNexus 番外阶段I-T1 拉伸SAXS当前基线台账.md`

最小输出：

- 当前帧数、应变范围、应变来源、应变轴置信度
- 当前 `L_nm / lc_nm / la_nm / Xc / Q_star / Q_rel / lc_confidence / lc_method`
- 当前 phase 分布与 phase 边界
- 当前 `has_voids / phi_void / f_herman`
- 当前 GUI 会如何解读这组结果

建议记录字段：

- `n_strains`
- `strain_values`
- `strain_source`
- `strain_axis_confidence`
- `strain_missing_count`
- `strain_duplicate_count`
- `frame_low_conf_count`
- `void_dominant_frame_count`
- `phase_ambiguous_frame_count`
- `effective_param_ratio`
- `paper_figure_candidate`
- `paper_conclusion_candidate`

验收标准：

- 不看图也能知道这组拉伸 SAXS 当前到底坏在“轴”“低 q”“锚点”“phase”还是“参数语义”
- 后续每次修正都能和这份基线逐项比较

推荐模型：`mini`


### I-T2. 应变轴 evidence 补强

目标：
让系统知道这条拉伸序列的应变轴是从哪里来的、是否单调、是否缺帧、是否混入了不同样品或错误顺序。

主要落点：
- [D:\PolyNexus\polynexus\core\saxs.py](D:\PolyNexus\polynexus\core\saxs.py)
- [D:\PolyNexus\polynexus\core\analysis_evidence.py](D:\PolyNexus\polynexus\core\analysis_evidence.py)
- [D:\PolyNexus\tests\test_import_suggestions.py](D:\PolyNexus\tests\test_import_suggestions.py)
- 如有必要新增：`D:\PolyNexus\polynexus\core\saxs_condition_recovery.py`

建议 evidence 字段：

- `condition_label`
- `condition_unit`
- `strain_values`
- `strain_range_pct`
- `strain_source`
- `strain_source_key`
- `strain_map_used`
- `strain_missing_count`
- `strain_duplicate_count`
- `strain_monotonic`
- `strain_step_median`
- `strain_step_spread`
- `condition_axis_confidence`
- `mixed_sample_risk`

建议新增约束：

- `condition_axis_missing`
- `condition_axis_unstable`
- `strain_sequence_nonmonotonic`
- `strain_duplicate_frames`
- `mixed_sample_strain_batch`
- `strain_source_low_confidence`

验收标准：

- 应变轴只靠文件名弱匹配时，系统会明确降级，不再假装趋势完全可信
- 应变缺帧、重复帧或混样时，不能直接把整条曲线当作正常拉伸序列

推荐模型：`mini`


### I-T3. Raw / Effective / Diagnostic 三层参数拆分

目标：
把拉伸 SAXS 里最容易混淆的三层语义彻底拆开，避免 `lc/Xc` 被“看上去合理”的有效值覆盖掉真实诊断值。

主要落点：
- [D:\PolyNexus\polynexus\core\saxs.py](D:\PolyNexus\polynexus\core\saxs.py)
- [D:\PolyNexus\polynexus\core\analysis_evidence.py](D:\PolyNexus\polynexus\core\analysis_evidence.py)
- [D:\PolyNexus\docs\plans\PolyNexus 统一框架方案 v4.0.md](D:/PolyNexus/docs/plans/PolyNexus%20统一框架方案%20v4.0.md)

建议最小输出：

- `L_nm_measured`
- `q_star_nm1_measured`
- `lc_nm_raw`
- `la_nm_raw`
- `Xc_raw`
- `Q_star_abs`
- `Q_star_rel`
- `lc_nm_effective`
- `la_nm_effective`
- `Xc_effective`
- `lamellar_interpretation_mode`
- `effective_param_reason`

建议语义规则：

- `L_nm` 只表示当前层状锚点追踪结果，不自动等同于“所有结构变化都还是层状主导”
- `Q_star_rel` 只用于相对有序度/有效参数解释，不直接冒充原始层厚测量
- `lc_raw_nm / Xc_raw` 保留为诊断值
- `lc_nm_effective / Xc_effective` 作为相对校准后的工作值
- GUI 和 CSV 必须能看出两者差异

验收标准：

- 不再出现“raw 证据不稳，但 final 参数看起来异常稳定”的语义冲突
- AI 在调参时能明确知道它是在修“测量链”还是在修“有效解释链”

推荐模型：`mini`


### I-T4. 空穴/低 q 污染 vs 层状长周期混淆症状化

目标：
把“当前长周期其实被空穴低 q 或 beamstop 影响带偏了”升级成可驱动动作和回滚的明确症状。

主要落点：
- [D:\PolyNexus\polynexus\core\saxs_symptom_detector.py](D:\PolyNexus\polynexus\core\saxs_symptom_detector.py)
- [D:\PolyNexus\polynexus\core\analysis_evidence.py](D:\PolyNexus\polynexus\core\analysis_evidence.py)
- [D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py](D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py)

建议新增症状：

- `strain_void_lamellar_conflict`
- `low_q_void_dominant`
- `lamellar_anchor_lost_under_strain`
- `qstar_rel_without_lamellar_support`
- `orientation_shift_breaks_lamellar_comparison`

建议关联证据：

- `Q_star_rel`
- `Q_star_valid`
- `has_voids`
- `void_Rg`
- `porod_slope`
- `beam_stop_contaminated`
- `mask_truncated`
- `q_peak_snr`
- `q_peak_diff_pct`
- `L_bragg / L_corr / L_best` 分歧

验收标准：

- 系统能明确告诉用户：现在是“层状链不稳”，不是简单的“图有点噪”
- 当低 q 被空穴主导时，`L/lc/Xc` 趋势会被自动降级处理

推荐模型：`mini`


### I-T5. 四阶段识别 evidence 补强

目标：
让 `elastic / voiding / microfibrillation / fracture` 的阶段判断变成“有多路证据支撑的结果”，而不是单靠 `Q*` 或低 q 斜率一次拍板。

主要落点：
- [D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py](D:\PolyNexus\polynexus\core\saxs_engine\saxs_strain.py)
- [D:\PolyNexus\polynexus\core\analysis_evidence.py](D:\PolyNexus\polynexus\core\analysis_evidence.py)

建议 evidence 字段：

- `phase_name`
- `phase_confidence`
- `phase_support_channels`
- `phase_boundary_candidates`
- `Q_star_change_pct`
- `low_q_power_law_alpha`
- `orientation_change_score`
- `lamellar_anchor_consistency`
- `void_support_score`

建议规则方向：

- `phase` 不再只由一条规则直接给最终结论
- phase 至少要同时参考：
  - `Q_star_rel`
  - 低 q 上翘/幂律斜率
  - 取向变化
  - 长周期锚点是否仍稳定
- 当支撑证据冲突时，输出 `phase_ambiguous`

验收标准：

- 阶段识别不再“有名字但没证据”
- phase 边界不稳时，GUI 会明确告诉用户这是诊断推断，不是最终结论

推荐模型：`5.4`


### I-T6. 拉伸SAXS专属动作闭环

目标：
让 orchestrator 面对拉伸 SAXS 时，优先修真实问题，而不是沿用静态/温变那套宽泛策略。

主要落点：
- [D:\PolyNexus\polynexus\orchestrator.py](D:\PolyNexus\polynexus\orchestrator.py)
- [D:\PolyNexus\polynexus\core\saxs_action_registry.py](D:\PolyNexus\polynexus\core\saxs_action_registry.py)
- `D:\PolyNexus\polynexus\config_bridge.py`

建议优先动作顺序：

1. `rerun_condition_recovery`
2. `split_batch_by_sample`
3. `adjust_q_crop`
4. `adjust_peak_window`
5. `adjust_corr_window`
6. `adjust_idf_smoothing`
7. `switch_lorentz_method`

建议新增拉伸专属动作语义：

- 优先恢复应变轴和样品序列完整性
- 低 q 空穴主导时，禁止直接把 `lc/Xc` 当主优化目标
- 长周期锚点丢失时，优先修锚点，而不是修 phase
- phase 证据冲突时，不允许“靠平滑结果曲线”提升置信

验收标准：

- AI 调参顺序更像一个懂拉伸 SAXS 的助手，而不是一个只想把曲线修顺的自动器
- 新候选只有在证据链更稳时才会被接受

推荐模型：`5.4`


### I-T7. 接受 / 回滚规则升级

目标：
让系统按“物理证据是否更完整”来决定接受结果，而不是按单一分数或图面观感。

主要落点：
- [D:\PolyNexus\polynexus\orchestrator.py](D:\PolyNexus\polynexus\orchestrator.py)
- [D:\PolyNexus\polynexus\core\analysis_evidence.py](D:\PolyNexus\polynexus\core\analysis_evidence.py)

建议新增比较项：

- `condition_axis_confidence`
- `void_dominance_score`
- `lamellar_anchor_consistency`
- `phase_support_score`
- `effective_param_ratio`
- `raw_effective_gap`
- `method_agreement_score`
- `parameter_stability_score`

建议新增回滚条件：

- `condition_axis_still_unstable`
- `void_lamellar_conflict_worsened`
- `lamellar_anchor_not_recovered`
- `phase_became_more_ambiguous`
- `effective_params_still_dominate_without_support`

验收标准：

- “图更顺但物理意义更假”的候选会被自动回滚
- “结果仍不可信但原因更清楚”的候选可以保留为诊断进展，而不是冒充成功修复

推荐模型：`5.4`


### I-T8. GUI 语义与论文输出拆分

目标：
让用户一眼看懂当前看到的是测得值、相对值还是诊断值，同时保证论文图不被诊断信息污染。

主要落点：
- `D:\PolyNexus\polynexus\gui\main_window.py`
- `D:\PolyNexus\polynexus\gui\convergence_viewer.py`
- `D:\PolyNexus\polynexus\gui\i18n.py`
- [D:\PolyNexus\polynexus\core\saxs_engine\saxs_output.py](D:\PolyNexus\polynexus\core\saxs_engine\saxs_output.py)

建议最小界面结构：

- 当前测得层状信息
- 当前有效解释参数
- 当前 phase 诊断
- 当前主要风险
- 已尝试修正
- 当前是否适合作为论文图
- 当前是否适合作为论文结论

建议最小文案语义：

- `Measured lamellar signal`
- `Effective trend-only parameter`
- `Diagnostic-only phase hint`
- `Low-q void conflict`
- `Not ready for paper conclusion`

验收标准：

- 用户不会再把所有 `lc/Xc` 默认当成“已可直接写进论文的结构参数”
- 论文导出图保持干净，诊断信息只在 GUI / 报告层展示

推荐模型：`mini`


### I-T9. 真实样本回归验证

目标：
让这条拉伸 SAXS 可信度修复链不是只在理想测试样本上成立，而是真能解释真实拉伸数据为什么可信或为什么暂时还不能信。

主要落点：
- `D:\PolyNexus\tests\test_analysis_evidence.py`
- `D:\PolyNexus\tests\test_saxs_symptom_detector.py`
- `D:\PolyNexus\tests\test_saxs_orchestrator_loop.py`
- 如有必要新增：
  - `D:\PolyNexus\tests\test_saxs_strain_evidence.py`
  - `D:\PolyNexus\tests\test_saxs_strain_orchestrator.py`
  - `D:\PolyNexus\tests\eval\cases\real\saxs_real_strain_*.json`

最小验证内容：

- 应变轴恢复是否稳定
- raw / effective / diagnostic 是否已拆开
- 空穴/低 q 与层状峰混淆是否能稳定命中
- phase_ambiguous 是否在该触发时触发
- orchestrator 是否按拉伸语义优先修轴、低 q 和锚点
- GUI 是否不再误导用户把诊断值当结论值

验收标准：

- 即使结果还不能完全修好，系统也能把“不可信”的原因讲对
- 如果后续某轮确实修好了，系统也能证明它比基线更可信，而不是只是更平滑

推荐模型：`mini`
