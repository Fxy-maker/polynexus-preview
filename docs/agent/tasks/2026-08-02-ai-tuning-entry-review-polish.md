---
task_id: 2026-08-02-ai-tuning-entry-review-polish
status: complete
date: 2026-08-02
---

# AI 调参入口与结果复核视觉升级

## Goal

让 Results 页面无需滚动即可发现 AI 调参入口，并把候选结果复核窗口改成能清楚区分推荐配置、证据变化和剩余风险的专业审阅界面。

## Non-goals

- 不改变 `ParameterOrchestrator`、参数白名单、候选执行、评分、回滚或安全门控。
- 不改变 SAXS shadow/confirm 预处理策略。
- 不自动确认结果或自动提升导出/科学状态。

## Affected boundaries

- GUI Results 页面入口与已有底部兼容入口。
- AI 调参启动目标选择的用户文案。
- AI 调参完成后的 `SideTuningReportDialog` 展示层。
- 中英文 i18n 与对应 GUI 回归测试。

## Implementation plan

1. 将 Results 页的 AI 调参入口移至摘要区上方，同时保留底部次级入口。
2. 用完成状态、独立风险提示和明确的应用/保留按钮升级 `SideTuningReportDialog`，不改变应用与重跑路径。
3. 更新中英文文案、补齐 GUI 回归，并运行任务卡规定的验证。

## Acceptance criteria

- [x] Results 页首屏显示 `开始 AI 调参` 和说明文字，底部保留 `AI 调参` 兼容入口。
- [x] 启动与工作流文案使用直接的 AI 调参语言，不再向用户显示“受控优化”。
- [x] 结果复核窗口显示候选完成状态、推荐/证据摘要和独立风险区。
- [x] 应用推荐配置仍只触发现有重新分析流程，`确认结果` 状态不被自动设置。
- [x] 任务卡结构化验证通过。

## Verification

```powershell
python -m pytest tests/test_main_window_ai_tuning_mixin.py tests/test_preprocess_decision_dialog.py tests/test_saxs_ai_confirmation_gui_route.py -q
python scripts/verify.py --task docs/agent/tasks/2026-08-02-ai-tuning-entry-review-polish.md --changed --types
```

Focused GUI verification passed: `15 passed, 185 deselected` for the Results
entry/report slice, and `8 passed` for the confirmation paths. Structured
verification passed with Ruff, compilation, quality gate `297 passed`, and
preprocess optimization gate `106 passed`.
