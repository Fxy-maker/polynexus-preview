# PolyNexus 番外阶段 I-T1 拉伸 SAXS 当前基线台账

冻结时间：2026-07-03

## 1. 冻结目的

这份台账用于固定 `saxs.strain` 真实拉伸序列的当前状态，作为后续每一轮修复的对照基线。

现在仓库里已经有一条可直接冻结的真实 case：

- [D:\PolyNexus\tests\eval\cases\real\saxs_real_strain_pad8_series.json](D:\PolyNexus\tests\eval\cases\real\saxs_real_strain_pad8_series.json)
- 源数据目录：`D:\PolyNexus\测试数据\saxs\PAD8原位拉伸`
- 当前输出目录：`D:\PolyNexus\测试数据\saxs\PAD8原位拉伸\polynexus_output`

这条序列是 5 帧的原位拉伸 SAXS 真实样本，已经可以被 `EvalRunner` 正常加载和运行。

## 2. 当前冻结值

### 2.1 序列级结果

这条真实 case 的当前输出参数是：

- `n_strains = 5`
- `strain_range_pct = 0-400`
- `r_squared = 0.6704046347622732`
- `quality_score = 0.49`
- `strain_axis_confidence = 0.64`
- `strain_reliability_status = diagnostic_only`
- `strain_reliability_reason = strain_axis_low_confidence|low_q_void_dominant`
- `phase_distribution = {elastic: 3, plastic_voiding: 2}`
- `phase_boundary_candidates = [{strain_pct: 200.0, from_phase: elastic, to_phase: plastic_voiding}]`
- `phase_ambiguous_frame_count = 1`
- `void_dominant_frame_count = 5`
- `frame_low_conf_count = 5`
- `effective_param_ratio = 1.0`
- `paper_figure_candidate = False`
- `paper_conclusion_candidate = False`

### 2.2 关键数值范围

- `Q_star_rel_mean = 1.0567`
- `Q_star_rel_span = 0.124`
- `Q_star_rel_range = 1.0000-1.1154`
- `L_range_nm = 4.32-4.70`
- `L_confidence = 0.49`
- `L_bragg = 5.041774404445092`
- `L_lorentz = 4.025442192471779`
- `L_corr_peak = 4.152418172936004`
- `q_peak_snr = 9.98330236425058`
- `porod_slope_mean = -0.173`
- `porod_slope_span = 0.2899`

## 3. 帧级参考

| strain | phase | L_nm | lc_nm | Xc | Q_rel | lc_confidence | lc_method | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 0% | elastic | 5.04 | 1.19 | 0.236 | 1.0000 | 0.50 | tangent_strain | baseline frame |
| 5% | elastic | 5.07 | 1.19 | 0.235 | 1.0039 | 0.50 | tangent_strain | stable but still diagnostic |
| 60% | elastic | 5.15 | 1.19 | 0.231 | 1.0518 | 0.50 | tangent_strain | phase support starts to weaken |
| 200% | plastic_voiding | 6.08 | 1.19 | 0.196 | 1.1240 | 0.35 | tangent_strain_qstar_warn | phase boundary candidate |
| 400% | plastic_voiding | 5.55 | 1.19 | 0.214 | 1.1037 | 0.35 | tangent_strain_qstar_warn | high-strain diagnostic frame |

## 4. 这条基线现在说明什么

这条真实拉伸 SAXS 不是“坏数据”，但它当前更适合做诊断基线，而不是论文结论基线。

当前最重要的结论是：

1. 这条序列已经能稳定看出拉伸阶段变化。
2. 但 `low-q / void / phase` 的证据链还不够强，系统不应该把它硬抬成 `paper_conclusion_candidate = True`。
3. 当前 GUI 和 AI 都应该把它解读为“诊断态、可追踪、可回滚”，而不是“已经足够写结论”。

## 5. 对后续修复的意义

后续每一轮修复都应该拿这份台账对照：

- 应变轴是否更稳
- `Q_star_rel` 是否更像可信物理量，而不是噪声跟着跑
- `phase_distribution` 是否更容易被解释
- `frame_low_conf_count` / `void_dominant_frame_count` 是否下降
- `paper_conclusion_candidate` 是否在证据变强时才被允许变成 `True`

## 6. 结论

I-T1 现在已经不是“缺真实 case”的状态了。

它已经完成了：

- 真实拉伸 SAXS case 的补入
- 真实序列的当前基线冻结
- 真实运行结果与诊断语义的固定

下一步就可以直接拿这条台账去跑 `I-T2` 到 `I-T9` 的回归对照。
