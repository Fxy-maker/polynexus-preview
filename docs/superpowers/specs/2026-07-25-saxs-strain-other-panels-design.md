# SAXS strain other panels design

## Context

拉伸 SAXS provider 已经把主演化、完整序列和补充/诊断证据拆开，但结果页
review hint 目前只识别温变 SAXS。目标是把同一套“主结论 -> 补充证据 ->
诊断证据”体验延伸到拉伸，同时保持现有 provider 的 figure ID、order、role
和证据门槛。

## Design choice

保留 `polynexus/core/saxs_engine/figure_strain.py` 的现有 figure definitions，
只增加契约回归，并在 `MainWindowOutputMixin._update_results_review_hint` 中
把 `saxs.strain` 加入已有摘要提示消费边界。这样 GUI 仍只传递已有的 summary、
risk 和 next-step 文本，不推导应变、phase 或 invariant 状态。

拉伸链路固定为：

1. `saxs.strain.evolution.1d/2d`：主图，order 10；role 由既有 frame evidence
   aggregate 决定；
2. `saxs.strain.sequence.1d/2d`：完整序列 SI，order 100；排除帧有独立
   `saxs.strain.sequence.diagnostic`，order 200；
3. `saxs.strain.invariant`：SI，order 105；
4. `saxs.strain.correlation` / `saxs.strain.idf`：SI 或 diagnostic，order 110/120；
5. `saxs.strain.azimuthal` / `saxs.strain.phase-evidence`：SI 或 diagnostic，
   order 130/140；
6. `saxs.strain.low-q.diagnostic`：diagnostic，order 220。

缺失的分析 trace 不创建空 figure；低置信度或诊断 frame 不因排序而提升为
Main。2D detector 不可用时继续使用现有 1D fallback。

## Component responsibilities

- `figure_strain.py`：提供既有 order、figure ID、证据 role 和 1D/2D fallback。
- `main_window_output_mixin.py`：只判断当前 submodule 是否为 `saxs.strain`，
  将已有文案放入结果 review hint；温变和非 SAXS 清理逻辑保持不变。
- `result_table_templates.py`、`results_table_panel.py`：继续消费已有 strain
  hero/primary/detail/diagnostic sections，不增加图形算法。

## Testing strategy

- 用现有 `tests/test_saxs_publication_pack_upgrade.py` fixture 锁定拉伸 order、
  role 和 low-q diagnostic；
- 在 `tests/test_main_window_output_mixin.py` 先加入拉伸 review hint 失败测试，
  验证 summary/risk/next-step 被原样传递；非拉伸技术仍清理 hint；
- 运行聚焦 pytest、Ruff、compile、`git diff --check` 和仓库 verifier。
