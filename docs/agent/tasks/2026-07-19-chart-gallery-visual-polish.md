# 日常任务：图表图库视觉与悬停态优化

## 目标

优化图表页的视觉层级，并修正图表卡片蓝色描边应随鼠标悬停移动、却被点击选择状态长期占用的问题。

## 非目标

- 不改变 manifest-only 图库发现策略。
- 不改变分类/论文角色筛选语义。
- 不改变图表预览、编辑、导出和复制信号契约。
- 不改分析核心、图表数据或生成图文件。

## 受影响边界

- `polynexus/gui/widgets/chart_viewer.py`：图表卡片视觉状态与图库布局。
- `tests/test_chart_viewer.py`：卡片 hover/selection 视觉回归。

## 验收标准

- 鼠标移入任意图表卡片时，蓝色描边只出现在当前 hover 卡片。
- 鼠标移出后，hover 蓝色描边消失；已点击卡片仍保留低强调的选择状态。
- 三列卡片结构、筛选、预览、编辑、导出和复制功能保持可用。
- 图表卡片拥有统一边界、内边距、标题和操作区，不再像图片、标签、按钮彼此分散。
- `python scripts/verify.py --changed --types` 运行并记录实际结果；若脚本缺失，明确记录该限制。

## 验证

- `pytest tests/test_chart_viewer.py -q`
- `python scripts/verify.py --changed --types`
- `git diff --check`

## 状态

- 2026-07-19：已确认视觉方向 A（三列卡片精修），实现中。
- Completion: implementation finished on 2026-07-19. The focused chart-viewer suite passes 17 tests. The repository verifier is unavailable because `scripts/verify.py` is missing.
