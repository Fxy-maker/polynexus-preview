# PolyNexus 番外阶段 E-T1 IR 当前基线台账

## 0. 冻结说明

这份台账只做一件事：把一条真实 IR 样本在**当前代码路径**下的行为冻结下来，作为后续 E-T2 / E-T3 修复的对照基线。

本次冻结样本：
- 文件：`D:\PolyNexus\测试数据\IR\普通红外\YL.SPA`
- 聚合物提示：`PA6`
- 当前分析配置：`peak_height_min=0.03, peak_prominence_min=0.02, peak_distance=18.0`
- 预处理默认：`baseline_method=rubberband, smooth_method=savgol, normalization_method=minmax`
- 基线报告：`D:\PolyNexus\results\ir_rag_warmup\YL.json`
- 基线日志：`D:\PolyNexus\results\ir_rag_warmup\logs\50_YL.log`

说明：
- 这条样本在当前链路下能稳定跑通，也能稳定识别 PA6 的主特征带。
- 这里冻结的不是“最终科学结论”，而是**当前工程状态**，方便后续每次修正都拿它对照。
- 当前 IR 结果里，`polymer_score` 已经能给出很强的 PA6 匹配，但它仍不能单独等价为“论文结论已可直接使用”，还要同时看关键参考带、峰覆盖、残差类型和约束状态。


## 1. 当前结果快照

### 1.1 baseline round

- `label`: `YL`
- `has_data`: `true`
- `raw_points_in_metadata`: `7157`
- `analyzed_points`: `7156`
- `polymer_name`: `PA6`
- `polymer_score`: `1.0`
- `r_squared`: `0.9957743267444965`
- `n_peaks`: `18`
- `Xc_pct`: `13.734547028307798`
- `Xc_method`: `PA6_A1200_A1637_uncalibrated`
- `analysis_span_cm1`: `550.1041870117188 - 3999.7063518713944`

补充说明：
- `load_project` 在当前链路里返回 1 条谱。
- `SPA` 元数据里是 7157 点，但经过 `400.0 - 4000.0 cm^-1` 的分析范围裁剪后，当前分析点数是 7156。

### 1.2 warmup best round

这条样本还跑过 3 轮 warmup 调参，但结论没有翻转，只是让峰数量稍微多了一些。

- `baseline_r_squared`: `0.9957743267444965`
- `best_r_squared`: `0.9958828939772135`
- `r_squared_abs_improvement`: `0.00010856723271701618`
- `rounds`: `3`
- `converged`: `true`
- `convergence_reason`: `delta_r_squared<0.001`
- `best_n_peaks`: `22`
- `best_polymer_score`: `0.2822613845779369`
- `best_Xc_pct`: `13.734547028307798`

这说明：
- 主特征带本身是稳定的。
- 但弱峰、未知峰和阈值边界还会随着参数变化而增减。


## 2. 峰结构冻结

### 2.1 主峰冻结表

下面这些峰是当前这条样本里最值得冻结的主骨架：

| 序号 | 波数 (cm^-1) | FWHM (cm^-1) | 归属 | 稳定性 |
| --- | ---: | ---: | --- | --- |
| 1 | 3289.26 | 86.16 | N-H stretch | 稳定 |
| 2 | 2916.60 | 28.76 | vas(CH2) | 稳定 |
| 3 | 2848.01 | 16.38 | vs(CH2) | 稳定 |
| 4 | 1632.32 | 33.30 | amide I | 稳定 |
| 5 | 1548.35 | 68.08 | amide II | 稳定 |
| 6 | 1461.25 | 16.44 | CH2 bend | 稳定 |
| 7 | 1422.61 | 41.60 | CH2 adjacent to NH | 稳定 |
| 8 | 1258.34 | 22.41 | amide III | 稳定 |
| 9 | 1184.22 | 6.66 | amide III + CH2 twist | 阈值敏感 |
| 10 | 939.96 | 15.76 | amide V | 阈值敏感但持续可见 |

### 2.2 结构判断

- 主特征带是清楚的，PA6 的 amide I、amide II、amide III 都已经被抓到。
- 当前 baseline round 下 `n_peaks=18`，warmup best round 下 `n_peaks=22`。
- 这说明不是“没峰”，而是“弱峰会随阈值和窗口轻微漂移”。
- 以当前代码路径看，峰位大体稳定，弱峰数量不完全稳定。
- `r_squared` 很高，但它只说明拟合表面上顺，不等于结论已经足够扎实。
- 当前代码下 `polymer_score=1.0`，说明 PA6 主体匹配已经很强；但关键参考带仍是 `10/13` 命中，峰覆盖约 `0.556`，所以高 `r_squared` 和高 `polymer_score` 仍不能直接推出“无条件 paper-ready”。
- 当前样本的主要问题不是“识别不出 PA6”，而是“关键带缺失、拥挤峰残差和峰覆盖不足仍然会限制论文结论的稳健性”。


## 3. 证据层冻结

当前 IR 的证据层已经不是空壳了，但还不算厚。

### 3.1 总览

- `constraint_summary.status`: `soft_warn`
- `constraint_summary.triggered_total`: `6`
- `constraint_summary.triggered_names.soft_warn`:
  - `key_band_support_insufficient`
  - `baseline_sensitive_assignment`
  - `crowded_band_underfit`
  - `overcrowded_band_separation_unstable`
  - `crystallinity_index_without_band_support`
- `constraint_summary.triggered_names.evidence_only`: `peak_structure`
- `confidence_signals`:
  - `polymer_score`
  - `peak_count`
  - `assignment_confidence`
  - `paper_conclusion_ready`

### 3.2 核心证据字段

- `feature_evidence.reference_evidence.band_count = 13`
- `feature_evidence.reference_evidence.hit_count = 10`
- `feature_evidence.reference_evidence.missing_count = 3`
- `feature_evidence.assignment_evidence.assignment_confidence = 1.0`
- `feature_evidence.assignment_evidence.key_band_hit_count = 10`
- `feature_evidence.assignment_evidence.key_band_missing_count = 3`
- `feature_evidence.structure_evidence.classification_basis = peak_assignment`
- `feature_evidence.structure_evidence.detected_peak_count = 18`
- `feature_evidence.structure_evidence.assigned_peak_count = 10`
- `feature_evidence.structure_evidence.matched_peak_count = 10`
- `feature_evidence.structure_evidence.paper_conclusion_candidate = false`
- `feature_evidence.structure_evidence.paper_conclusion_ready = false`
- `feature_evidence.structure_evidence.key_band_support_score = 0.7692307692307693`
- `feature_evidence.structure_evidence.peak_coverage_score = 0.5555555555555556`
- `feature_evidence.structure_evidence.baseline_stability_score = 0.6700000000000002`
- `feature_evidence.structure_evidence.ir_support_score = 0.8045692307692307`

### 3.3 残差信息

- `residual_type`: `crowded_band_underfit`
- `max_residual_region`: `1469.5 cm^-1`
- `rmse`: `0.00674521851468013`
- `residual_summary`: `IR residual maximum near 1469.5 cm^-1 with negative residual (fit too high); RMSE=0.006745, residual_type=crowded_band_underfit. Prefer tuning peak_fit_window_cm1, peak_prominence_min, peak_height_min, or peak_distance.`

### 3.4 当前摘要字符串

这条样本当前的 evidence summary 读起来是：

`residual=crowded_band_underfit; risks=5; constraints=16; constraint_status=soft_warn; triggered_constraints=6; peak_count=18; assignment_confidence=1.0; key_band_support=0.7692307692307693; peak_coverage=0.5555555555555556; baseline_stability=0.6700000000000002; ref_bands=13; ref_hits=10; ref_missing=3; band_support=False; paper_ready=False`

这里最值得注意的是：
- `paper_conclusion_ready=false` 已经被收紧
- `constraint_summary.status=soft_warn`
- 所以这条样本可以作为 PA6 识别和出图候选，但不应被界面或 agent 直接抬成“无条件论文结论”


## 4. GUI 当前会怎么读

按现在的结果组织方式，这条 IR 结果大概率会被界面读成：

1. `core` 层会先看到很高的 `r_squared`，以及 `polymer_score=1.0`、`Xc_pct`、`n_peaks` 这些核心数值。
2. `quality_score/raw_score` 如果被展示，仍不应被当成独立论文可信度。
3. `analysis_evidence` 层会显示：
   - `peak_evidence`
   - `baseline_evidence`
   - `assignment_evidence`
   - `reference_evidence`
   - `structure_evidence`
4. 如果只看图和高分数，容易误读成“这条 PA6 结果已经很稳”。
5. 但如果认真看证据层，会发现：
   - 10/13 个参考带被命中，仍有 3 个参考带缺失
   - `assignment_confidence` 很高，但 `key_band_support_score` 和 `peak_coverage_score` 仍不足以直接 paper-ready
   - 残差明确是 `crowded_band_underfit`

所以更准确的读法应该是：

**主特征带已经出来，PA6 匹配也很强，但当前仍应把它看成“可解释的 PA6 候选结果”，而不是“无条件 paper-ready 的最终结论”。**


## 5. 这条基线的修复指向

后续 IR 修复最好沿着下面几个方向走：

- 保持 `polymer_score`、`quality_score/raw_score` 和“论文结论可信度”的语义拆分。
- 先补厚 `peak_evidence / assignment_evidence / baseline_evidence / reference_evidence`，再谈更激进的 AI 解释。
- 先把 `crowded_band_underfit` 和局部拥挤峰分离问题讲清楚，再去想“让 AI 自动抬高结果”。
- 让系统明确区分：
  - 已测到的峰
  - 已支持的归属
  - 仍然只是候选的结论


## 6. 回归记录

warmup 跑出来的调参轨迹也值得一起冻结：

1. `round 0`
   - baseline config
   - `n_peaks=18`
   - `r_squared=0.9957743267444965`
2. `round 1`
   - 试 `lineshape=pseudo_voigt`
   - 回滚
3. `round 2`
   - 试 `peak_fit_window_cm1=45.0`
   - 试 `peak_distance=15.0`
   - 回滚
4. `round 3`
   - 试 `peak_height_min=0.01`
   - 试 `peak_prominence_min=0.01`
   - 收敛到 `22` 个峰

这说明：
- 主峰骨架本身相当稳。
- 但阈值一松，弱峰会多出来。
- 所以后面修复时，不能只盯着一个高分数看，必须同时盯住峰稳定性和证据层厚度。


## 7. 台账结论

这条样本在当前代码路径下可以总结成一句话：

**PA6 的主特征带已经稳定出现，匹配分数和拟合指标都很漂亮，但关键带覆盖、峰覆盖和拥挤峰残差仍限制最终 paper-ready 结论。**

这份台账现在可以作为番外阶段 E 的起点基线。
