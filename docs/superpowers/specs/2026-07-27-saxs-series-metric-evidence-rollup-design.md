# SAXS Series Metric Evidence Rollup Design

Date: 2026-07-27
Status: proposed for review
Related goal: 建立可解释、可验证、可降级的 PolyNexus SAXS 数据质量与分析体系

## Goal

为温变和应变 SAXS 序列增加一个可追溯的系列级方法证据摘要，把现有每帧
`metric_evidence` 汇总为覆盖率、帧级等级分布、缺失/降级原因和系列级允许
等级，并让 Workbench/Export 能直接消费这个摘要。该摘要只观察已有证据，
不重新分析曲线、不修复缺失帧、不改变任何物理数值或现有质量门。

## Problem

当前 `TemperatureSeriesResult` 和 `StrainSeriesResult` 保存了每帧
`metric_evidence`，但系列对象本身没有明确的摘要。消费者必须自行遍历帧，
容易把“部分帧可用”误读成“整个序列可用于趋势”，也无法在导出中统一显示
缺失帧和最弱证据等级。

## Alternatives

1. 在 Export 层临时遍历帧并生成摘要。放弃：摘要会只存在于导出路径，
   Workbench、History 和其他消费者无法复用，而且会让导出承担分析语义。
2. 把汇总字段塞进每帧 `MetricEvidence`。放弃：混淆帧级和序列级作用域，
   破坏现有 DTO 的含义。
3. 在质量契约层增加只读 `MetricEvidenceSummary`，由温变/应变结果在已有
   帧分析完成后构建，并通过现有 Export quality payload 原样传播。选择：
   作用域清楚、可复用、不会重跑分析，且可以独立测试降级规则。

## Contract

新增不可变、严格 JSON-safe 的 `MetricEvidenceSummary`：

```text
metric_name: str
frame_count: int
evidence_frame_count: int
usable_frame_count: int
diagnostic_frame_count: int
unusable_frame_count: int
missing_frame_count: int
coverage_fraction: float | None
level: QualityLevel
applicable: bool
level_counts: dict[str, int]
reason_codes: tuple[str, ...]
source_ref: str
```

The DTO provides `to_dict()`/`from_dict()` and uses the same enum normalization
and strict JSON conversion as the existing quality contracts.

并提供 `build_series_metric_evidence(frame_evidence, metric_names=None,
source_ref="") -> dict[str, dict]`。输入只接受已有帧证据字典；不会接收或保存
q/I 数组、文件路径或候选配置。

### Aggregation rules

- `frame_count` 是序列帧数；缺失 metric key 计入 `missing_frame_count`，
  不会被过滤掉。
- `evidence_frame_count` 只计算存在且为 mapping 的该 metric；非法或未知
  level 记为 `Unusable`，并增加明确 reason code。
- `coverage_fraction = evidence_frame_count / frame_count`；空序列为
  `None`，不生成 `NaN`。
- 空序列或所有帧缺少该 metric：`Unusable`，`applicable=False`。
- 只要有缺失、`Diagnostic`、`Unusable` 或非法等级帧，系列摘要最高为
  `Diagnostic`；原因分别保留为可检索 reason code。
- 所有帧都有证据、至少两帧、且每帧等级至少为 `Trend` 时，摘要为
  `Trend`，`applicable=True`。即使所有帧是 `Quantitative`，系列摘要也只
  能到 `Trend`，因为本阶段尚未完成序列趋势的真实数据校准。
- 少于两帧不能声称趋势，降为 `Diagnostic` 并记录
  `series_requires_multiple_frames`。
- `level_counts` 使用 `QualityLevel.value` 作为 key，顺序稳定；每帧原有
  evidence 不被改写。

## Propagation

- `TemperatureSeriesResult.metric_evidence` 保存按 metric name 索引的摘要。
- `StrainSeriesResult.metric_evidence` 保存同样结构。
- 两个 `to_dataframe()` 保留现有逐帧 `Metric_evidence_levels` 列，不改变
  数值列或行数。
- `saxs_export_bundle._series_quality_payload()` 通过既有
  `_QUALITY_FIELDS` 原样输出系列摘要，并继续输出逐帧 evidence；Export
  不重新计算等级。
- 静态 `SAXSResult.metric_evidence` 行为不变。

## Safety and downgrade boundaries

- 这是 evidence-only 汇总，不增加 Porod/Kratky/Q*/层片/Guinier 的物理
  阈值，也不改变 `validate_saxs_results`。
- 缺失帧不会被插值、复制或从相邻帧推断。
- 系列摘要不能授权 AI candidate 应用、publication role 或
  `tiered-auto`；它只让降级状态更明确。
- 单帧方法证据仍由现有 `MetricEvidence` 判定；本设计只定义跨帧摘要。

## Acceptance evidence

- Contract tests cover clean all-frame Trend, missing frame, diagnostic frame,
  invalid level, empty series, and strict JSON round-trip.
- Temperature and strain tests prove the summary is attached without changing
  existing frame values or row shape.
- Export tests prove the summary is read-only provenance and coexists with
  per-frame evidence.
- Task-scoped verifier and the applicable SAXS regression matrix pass; full
  repository verification remains a release checkpoint.

## Review boundary

This design deliberately stops at a conservative, audit-only summary. Opening
quantitative sequence claims, imputing missing frames, or introducing
method-specific thresholds requires a separate scientific task and expert
review.
