# SAXS temperature other panels design

## Context

温变 SAXS 的 waterfall 已经完成较细的视觉打磨，但温变结果仍需要把其他
板块组织成可读的证据链。当前 provider 已有 evolution、条件性 Avrami、
waterfall 和 selected-frame evidence；本设计只整理既有产物的呈现边界，
不重新计算科学结果。

## Design choice

采用现有 provider/manifest 的轻量排序与元数据校验方案，而不新建 GUI 专用
的温变 panel model，也不把多个 figure 合并成新的 figure ID。推荐方案的
原因是它能保留已经稳定的证据过滤、publication role 和 Gallery/Editor
入口，同时让结果页按既有 `Main -> SI -> diagnostic` 消费。

温变链路固定为：

1. `saxs.temperature.evolution`：主结论，order 10；
2. `saxs.temperature.avrami`：仅在既有 Avrami evidence eligible 时出现，
   order 20；
3. `saxs.temperature.waterfall`：SI，order 100，保持现有细调和 ID；
4. `saxs.temperature.evidence.*`：selected-frame evidence，order 200+，
   role 由既有证据资格决定，不能因为排序而升级为 Main。

当 evolution gate 不满足时，沿用现有 fallback：保留 waterfall，并允许已有
的 SI summary/heatmap；本阶段只增加回归保护，不改变 fallback 判定。

## Component responsibilities

- `polynexus/core/saxs_engine/figure_temperature.py`：唯一负责温变 figure
  definition 的顺序、display order、role 和 fallback 合同；若现有实现已满足
  合同，则只补测试，不做无效重构。
- 温变 summary/review text service：继续提供已有 summary、risk 和 next-step
  文本；review hint 只消费证据状态，不在 GUI 中推导温度或阈值。
- `polynexus/gui/main_window_output_mixin.py`：复用已有 temperature review
  hint wiring；若发现 wiring 缺失，只补消费层适配，不复制 provider 判断。
- `polynexus/gui/result_table_templates.py` 与
  `polynexus/gui/widgets/results_table_panel.py`：保持当前温变 hero、primary、
  detail、diagnostics 分层，补充契约回归而不新增 technique-specific branch。

## Data flow

```text
SAXS AnalysisResult
  -> temperature provider
  -> FigureDefinition + evidence metadata + publication_role
  -> Manifest/Gallery/Editor
  -> ResultsTablePresentation / review hint
```

任何缺失、低置信度或诊断状态都沿用已有 metadata，不通过 GUI 重新解释。

## Error and fallback behavior

- evolution 不 eligible：保留既有 waterfall/SI fallback，不伪造 Main evolution。
- Avrami 不 eligible：不创建 `saxs.temperature.avrami` entry。
- selected evidence 缺失或低置信度：不提升 role；若 provider 已输出 diagnostic
  entry，继续显示为 diagnostic。
- 既有 figure ID、columns 或 publication role 变化：测试失败并阻止 checkpoint。

## Testing strategy

采用 TDD，先锁定当前行为，再对实际需要的消费层 wiring 增加最小回归：

- provider 正常路径：顺序、ID、role、Avrami 条件出现；
- fallback 路径：evolution/Avrami 不合格时的既有条目集合；
- evidence 路径：selected evidence 的 order 与 role 不越权；
- GUI 适配：review hint 仅在 temperature manifest/summary context 下消费已有
  evidence，不改变科学输入；
- 运行聚焦测试、Ruff、compile、`git diff --check` 和仓库 verifier。

## Out of scope and follow-up

拉伸与静态 SAXS 另建独立设计和计划，分别复用同一条“主结论 -> 补充证据 ->
诊断证据”原则，但不在本阶段共享新的跨模块接口。
