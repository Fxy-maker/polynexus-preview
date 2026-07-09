# PolyNexus 番外阶段 J-T1 ssNMR 当前基线台账

## 0. 台账目的

这份台账冻结当前 NMR 可信度链的起点。它不是结论文档，而是后续 J 阶段每一轮修复的对照表。

## 1. 当前代码入口

主要入口：

- `polynexus/core/nmr.py`
- `polynexus/core/nmr_engine/io.py`
- `polynexus/core/nmr_engine/core.py`
- `polynexus/core/nmr_engine/nmr_output.py`
- `polynexus/core/analysis_evidence.py`
- `tests/test_nmr_engine.py`

当前注册子模块：

- `nmr.liquid_h`
- `nmr.liquid_c`
- `nmr.solid_h`
- `nmr.solid_c`

当前支持输入：

- two-column table: `.csv`、`.txt`、`.dat`
- Bruker-like `fid`
- JEOL `JEOL.NMR` `.jdf/.bin`
- computed shifts / `.magres` 解析入口

## 2. 当前已有能力

当前 NMR engine 已经能输出：

- `nucleus`
- `sample_state`
- `n_peaks`
- `dominant_peak_ppm`
- `median_snr`
- `mean_fwhm_ppm`
- `r_squared`
- `region_*_pct`
- `quality_*`
- `peak_*_ppm`
- `peak_*_assignment`
- `peak_*_snr`
- `peak_*_region`
- `peak_*_possible_solvent`
- `Xc_pct`
- `Xc_method`
- `n_matches`

当前质量标记：

- `NMR_peaks`
- `NMR_SNR`
- `NMR_linewidth`
- `NMR_fit_R2`
- `Xc_NMR`
- `Xc_NMR_assignment`

## 3. 当前可信度短板

### 3.1 evidence 层偏薄

`analysis_evidence.py` 当前 NMR 约束主要是：

- `fit_quality`
- `peak_snr`

这不足以解释：

- 峰数是否足够。
- 线宽是否异常。
- 去卷积是否可用。
- 归属来自 generic region、polymer DB 还是 computed shifts。
- `Xc_NMR` 是否真的有晶/非晶峰支持。

### 3.2 Xc_NMR 语义仍需收紧

当前固体 13C 会尝试通过 phase label 计算 `Xc_pct`。如果没有晶/非晶 phase 支撑，则 `Xc_method = requires_crystalline_amorphous_assignment`。

这个方向是对的，但 evidence / GUI / Joint 还需要显式表达：

- `Xc_NMR` 当前是 supported、assignment_limited 还是 unavailable。
- `Xc_NMR_assignment` WARN 不能被 Joint 当成强结晶度证据。

### 3.3 溶剂峰和 generic assignment 容易被过度解释

液体 NMR 已能标记 `possible_solvent`，但还没有进入可信度门。

generic region assignment 可作为诊断，不应和 polymer DB / DFT 匹配同等对待。

## 4. 当前基线字段建议

J 阶段后续应稳定输出这些字段：

- `nmr_input_format`
- `nmr_partition`
- `nucleus`
- `sample_state`
- `point_count`
- `ppm_range`
- `peak_count`
- `median_snr`
- `mean_fwhm_ppm`
- `fit_r_squared`
- `fit_quality_level`
- `assignment_source`
- `assigned_peak_fraction`
- `generic_assignment_fraction`
- `solvent_peak_count`
- `computed_shift_match_count`
- `computed_shift_delta_ppm_mean`
- `phase_assignment_count`
- `Xc_NMR`
- `Xc_method`
- `Xc_assignment_status`
- `paper_conclusion_ready`

## 5. 当前判断

当前 NMR 主流程已经跑通，但可信度层仍然偏薄。

可以信的部分：

- 输入分区拦截已有基础。
- 峰检测、去卷积、区域积分、峰表导出已有基础。
- 固体 13C 在没有 phase 支撑时不会直接输出强 `Xc_NMR`。

暂时不能直接信的部分：

- `quality_score/raw score` 不应替代 NMR 谱图可信度。
- generic assignment 不应被当成结构归属结论。
- `Xc_NMR_assignment=WARN` 时，Joint 不应把 NMR 当作强结晶度来源。

## 6. 后续验收基线

J 阶段完成后，应能回答：

- 这条 NMR 谱图是否有足够 SNR 和峰结构。
- 当前峰拟合是否只是诊断可用，还是能支撑参数。
- 当前归属来自哪里，可信等级是什么。
- 当前 `Xc_NMR` 是否可作为结晶度估计。
- 当前结果是否能进入 Joint 交叉验证。
