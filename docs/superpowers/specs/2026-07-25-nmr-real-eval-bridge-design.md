# NMR real-engine evaluation bridge design

## Context

NMR 已有四个 typed submodule、分析结果和 Figure provider，但 `EvalRunner`
的 real-engine allowlist 只覆盖 WAXS、DSC、SAXS、IR。因此 NMR cases 会退回
ground-truth stub，无法验证 NMR engine 到评测指标的真实边界。

## Design

在 `EvalRunner` 中增加四个显式 NMR submodule allowlist。real dispatch 复用现有
`get_engine`/`run_pipeline` 流程，只增加受限配置 alias、NMR config provenance
和 `NMRResult` 的稳定字段提取：`peak_shifts`、`peaks`、`n_peaks`、`Xc_pct`、
`Xc_method`、`Xc_assignment_status`、`median_snr`、`r_squared`、`x_min/x_max`。
所有 numpy/ dataclass 值继续通过 `_to_plain_value` 序列化；assignment-limited
状态只作为输出证据，不被提升为 Main 结论。

## Failure and fallback

NMR 不可读、无数据或 engine 返回空结果时沿用现有 `run_case` 错误边界；本设计
不吞掉异常，也不把缺失峰伪造成通过。AI 不参与 real dispatch，因而 AI-off 路径
天然确定性；preprocess fallback 仍由既有 preprocessing hard guard 处理。

## Testing

先添加会因 NMR 不在 allowlist 而失败的 bridge regression，再实现最小 dispatch 和
extraction。回归同时检查四技术既有 real/publication matrix，避免扩展 allowlist
改变其他 technique 的输出。
