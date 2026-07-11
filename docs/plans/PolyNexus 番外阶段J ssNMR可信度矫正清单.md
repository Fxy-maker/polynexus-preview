# PolyNexus 番外阶段 J ssNMR 可信度矫正清单

## 0. 当前问题定位

这份专项清单针对 `nmr.liquid_h`、`nmr.liquid_c`、`nmr.solid_h`、`nmr.solid_c` 四个 NMR 分区，重点先放在固体 13C / 固体 1H 的 ssNMR 可信度链。

当前代码已经具备 NMR 的主流程：

1. `NMREngine` 已注册四个 NMR 子模块，并能在加载前按液体/固体、1H/13C 做分区拦截。
2. `nmr_engine.io` 已支持两列表格、FID、JEOL `JEOL.NMR` 容器和计算位移文件。
3. `nmr_engine.core` 已能做峰检测、去卷积、区域积分、聚合物 13C 数据库归属、固体 13C `Xc_NMR` 尝试、T1/T2 拟合和计算位移匹配。
4. `analysis_evidence.py` 里已经有 NMR 的基础约束入口，但目前只有 `fit_quality` 和 `peak_snr` 两个轻量约束。

真正缺的是“为什么这条 NMR 结果能信或不能信”的分层证据。现在容易出现几种混淆：

1. 峰数不少，不等于谱图质量和归属都可信。
2. 去卷积 R2 不差，不等于宽峰、重叠峰和基线残差已经解决。
3. 固体 13C 有峰面积，不等于 `Xc_NMR` 可以作为结晶度结论。
4. generic region assignment 不能和 polymer DB / DFT 匹配同等对待。
5. 液体 NMR 的溶剂峰、残余水峰可能被误当成聚合物结构证据。

## 1. 专项目标

番外阶段 J 只解决一个问题：

**让 PolyNexus 能把 NMR 结果拆成输入可信度、信号可信度、峰可信度、归属可信度、结晶度可信度和计算/参考匹配可信度，并让 GUI、AI 和导出都能诚实表达当前 NMR 结论能用到哪一步。**

本专项希望完成 6 件事：

1. 建立 NMR 当前基线台账。
2. 扩展 NMR `analysis_evidence` 分层结构。
3. 建立 NMR 专属可信度约束和症状。
4. 把固体 13C `Xc_NMR` 和“峰面积/归属支持”绑定。
5. 把计算位移匹配和 polymer DB 归属拆成不同证据等级。
6. 让 AI 调参优先修复谱图/峰/归属证据，而不是只追逐更高拟合分数。

## 2. 阶段边界

### 2.1 本专项要做什么

- 围绕 `NMR` 建立独立的可信度证据链。
- 冻结一份真实/合成 NMR 当前基线台账。
- 补齐 `signal_evidence`、`peak_evidence`、`assignment_evidence`、`reference_evidence`、`phase_evidence`、`structure_evidence`。
- 增加 NMR 约束：低 SNR、峰过宽、峰数不足、fit 不稳定、归属过弱、溶剂峰风险、Xc 缺少晶/非晶归属。
- 让 `orchestrator` 和 prompt 能看到 NMR 的关键风险。
- 让导出和结果摘要能表达 `Xc_NMR` 是可用、待标定，还是仅诊断。

### 2.2 本专项暂时不做什么

- 不重写 NMR 基础峰检测和去卷积算法。
- 不一次性实现完整 GIPAW / Gaussian 自动任务流。
- 不把 generic region assignment 当成论文级化学归属。
- 不把所有 NMR 输出都映射成结晶度。
- 不把 Joint 跨技术一致性判断放进本专项，Joint 单独在 K 阶段处理。

## 3. 最小闭环

本专项最小可交付闭环如下：

1. `core` 输出 NMR 分层证据：
   - 输入来源、分区、点数、ppm 范围。
   - SNR、噪声、峰数、线宽、去卷积 R2。
   - 峰区域、可能溶剂峰、归属来源。
   - 固体 13C 晶/非晶峰面积支持。
   - 计算位移匹配数量和偏差。
2. `analysis_evidence` 能识别 NMR 主要风险：
   - `nmr_low_snr`
   - `nmr_broad_linewidth`
   - `nmr_fit_quality_low`
   - `nmr_assignment_weak`
   - `nmr_solvent_peak_dominant`
   - `nmr_xc_assignment_missing`
3. `orchestrator` 接收这些风险并降低低可信候选的接受概率。
4. GUI/导出能说明：
   - 当前 NMR 适合做谱图诊断、结构归属、结晶度估计，还是只能做参考。

## 4. 任务清单

### J-T1. ssNMR 当前基线台账冻结

目标：冻结当前 NMR 的真实/合成样本表现，作为后续修复对照。

主要落点：
- `tests/test_nmr_engine.py`
- `tests/eval/cases/synth/nmr_synth_pa6_carbon.json`
- `tests/eval/cases/synth/nmr_synth_pa6_proton.json`
- `docs/baselines/PolyNexus 番外阶段J-T1 ssNMR当前基线台账.md`

最小输出：
- 当前支持的 NMR 输入格式。
- 四个 NMR 子模块的分区行为。
- 合成 PA6 1H / 13C 的峰数、SNR、线宽、R2、归属数量。
- 当前 `Xc_NMR` 是否可用，以及不可用原因。

验收标准：
- 不看图也能知道当前 NMR 结果卡在输入、信号、峰、归属还是结晶度语义。
- 台账能作为后续每轮修复的对照基线。

### J-T2. NMR evidence pack 扩展

目标：把 NMR 从两个轻约束扩展成结构化证据包。

主要落点：
- `polynexus/core/analysis_evidence.py`
- `tests/test_analysis_evidence.py`

建议 evidence 字段：
- `signal_evidence`: `point_count`、`ppm_min`、`ppm_max`、`median_snr`、`noise_mad`
- `peak_evidence`: `peak_count`、`dominant_peak_ppm`、`mean_fwhm_ppm`、`peak_area_total`
- `assignment_evidence`: `n_matches`、`assignment_source`、`assigned_peak_fraction`、`generic_assignment_fraction`
- `reference_evidence`: `computed_shift_match_count`、`computed_shift_delta_ppm_mean`
- `phase_evidence`: `crystalline_area`、`amorphous_area`、`phase_assignment_count`
- `structure_evidence`: `Xc_NMR`、`Xc_method`、`Xc_assignment_status`

验收标准：
- `build_analysis_evidence("NMR", ...)` 输出分层字段。
- summary 中出现 NMR 关键证据，而不只是 `constraint_status`。

### J-T3. NMR 可信度约束和症状

目标：把低可信 NMR 变成可解释、可行动的症状。

建议新增约束：
- `nmr_peak_count_too_low`
- `nmr_low_snr`
- `nmr_broad_linewidth`
- `nmr_fit_quality_low`
- `nmr_assignment_weak`
- `nmr_solvent_peak_risk`
- `nmr_xc_assignment_missing`
- `nmr_computed_shift_mismatch`

验收标准：
- 低 SNR、宽峰、归属不足、Xc 缺晶/非晶支持时会触发明确症状。
- `actionable_symptoms` 能给 AI 明确修复方向。

### J-T4. 固体 13C Xc_NMR 可信度门槛

目标：`Xc_NMR` 只有在晶相/非晶相峰都有证据时才可作为结晶度估计。

主要落点：
- `polynexus/core/nmr_engine/core.py`
- `polynexus/core/analysis_evidence.py`
- `tests/test_nmr_engine.py`
- `tests/test_analysis_evidence.py`

规则：
- 没有晶/非晶 phase 归属时，`Xc_method` 保持 `requires_crystalline_amorphous_assignment`。
- 有峰面积但没有 phase 支撑时，`Xc_NMR` 只能作为诊断缺口，不进入论文结论。
- 有足够 phase 支撑时，输出 `Xc_assignment_status = supported`。

验收标准：
- 不会把 generic region 或未知 phase 峰面积误升格成 `Xc_NMR`。

### J-T5. NMR AI 调参和 action 对齐

目标：让 AI 优先修复 NMR 证据链，而不是泛泛建议改参数。

主要落点：
- `polynexus/orchestrator.py`
- `rag/prompt_builder.py`
- `polynexus/config_bridge.py`

建议动作方向：
- 降低/提高 `peak_height_min`
- 调整 `peak_distance_ppm`
- 切换 `baseline_method`
- 切换 `deconvolution_method`
- 限制 `max_peaks`
- 要求用户提供 polymer 或 computed shift 参考

验收标准：
- NMR 低可信候选不会只因分数局部上升被接受。
- prompt 中能看到 NMR 具体症状和目标证据。

### J-T6. GUI / 导出语义补齐

目标：结果页和导出包能表达 NMR 当前可信度层级。

主要落点：
- `polynexus/gui/main_window.py`
- `polynexus/core/report.py`

最小输出：
- NMR 谱图质量摘要。
- 归属可信度摘要。
- `Xc_NMR` 可用性说明。
- 计算位移匹配说明。

验收标准：
- 用户能区分“谱图可看”“归属可参考”“结晶度可用”三个层级。

### J-T7. 回归测试和真实样本巡检

目标：保证 NMR 可信度链能解释真实和合成数据。

建议测试：
- `test_nmr_analysis_evidence_surfaces_signal_peak_assignment_sections`
- `test_nmr_xc_requires_crystalline_and_amorphous_assignment`
- `test_nmr_low_confidence_symptoms_are_actionable`

验收标准：
- NMR 相关 targeted tests 通过。
- 不破坏 IR/DSC/WAXS/SAXS 现有 evidence tests。

## 5. 推荐执行顺序

1. `J-T1` 冻结基线台账。
2. `J-T2` 扩展 evidence pack。
3. `J-T3` 增加约束和症状。
4. `J-T4` 收紧 `Xc_NMR` 可信度门槛。
5. `J-T5` 接入 AI 调参上下文。
6. `J-T6` 补 GUI/导出语义。
7. `J-T7` 回归收口。

这一阶段完成后，NMR 才能作为 Joint 阶段的可信输入，而不是一个只有峰表和拟合分数的旁路模块。
