# Results Workbench 主 Tab 透明效果修复

## Goal

修复真实 Qt 路由切换后 Results Workbench 整页被 `QGraphicsOpacityEffect`
压淡的问题，确保 Results、Gallery、History 等主 Tab 的正文在 Light theme
下保持可读，同时保留局部提示条所需的淡入效果。

## Non-goals

- 不改变 Results 数据、证据、表格、图形或科学判断。
- 不调整主题 token、颜色对比度或分析算法。
- 不修改真实回归数据、生成输出、发布流程或其他未相关的动画。

## Affected boundaries

- `polynexus/gui/main_window.py` 主 Tab 路由动画边界。
- `tests/test_main_window_results_mixin.py` Qt 路由回归测试。
- native SAXS Results/Gallery/History/Editor 视觉验收 harness。

## Implementation plan

1. Add a focused Qt regression that reproduces the full-page opacity effect
   during a main Tab route change.
2. Remove the full-page Tab transition effect while retaining local transient
   surface animation.
3. Run focused tests, native SAXS route capture, diff checks, and the task
   verifier; then checkpoint the explicit allowlist.

## Acceptance criteria

- [x] 主 Tab 切换不会给 Tab page 安装 `QGraphicsOpacityEffect`。
- [x] Results Workbench 的现有内容和路由测试继续通过。
- [x] native Windows SAXS static/temperature/strain capture 通过，且 Results
  正文不再因整页透明效果而被压淡。
- [x] `python scripts/verify.py --task docs/agent/tasks/2026-07-28-results-workbench-tab-opacity.md --changed --types` 通过。

## Verification result

- [x] TDD RED: `test_main_tab_route_does_not_apply_full_page_opacity_effect`
  failed because `_on_tab_changed` installed `QGraphicsOpacityEffect`.
- [x] Focused GREEN: `23 passed` across MainWindow Results and ResultsTablePanel
  tests.
- [x] Native Windows SAXS route capture: `3 passed, 13 deselected in 44.10s`;
  static, temperature, and strain each captured Results/Gallery/History/Editor
  successfully under `C:\Temp\polynexus_native_saxs_visual_20260728_fixed`.
- [x] `git diff --check` passed.
- [x] Task verifier passed with external basetemp
  `C:\Temp\polynexus_results_tab_opacity_verify_20260728`: Ruff, compile/type
  baseline, quality `283 passed`, preprocessing `106 passed`, memory/task, and
  whitespace checks.

The first verifier attempt is excluded from acceptance because the pre-existing
repository `.pytest_tmp` was Windows-permission locked; it produced fixture
cleanup errors rather than product test failures. No scratch directory was
deleted or modified.

Fresh follow-up on 2026-07-30 returned `23 passed in 5.42s` for the focused
Results/MainWindow selection and `3 passed, 14 deselected in 57.98s`, exit code
`0`, for the native Windows SAXS route with external D: capture/basetemp.

## Follow-up documentation checkpoint allowlist

- `docs/agent/tasks/2026-07-28-results-workbench-tab-opacity.md`
- `docs/acceptance/2026-07-30-results-workbench-tab-opacity.md`
- `docs/agent/memory/active-work.md`

## Changed-file allowlist

- `polynexus/gui/main_window.py`
- `tests/test_main_window_results_mixin.py`
- this task card
- the implementation plan
- durable agent memory entries updated for this correction

## Verification

```powershell
python -m pytest -q tests/test_main_window_results_mixin.py -k tab_page
python -m pytest -q tests/test_main_window_results_mixin.py tests/test_results_table_panel.py
$env:QT_QPA_PLATFORM='windows'
$env:POLYNEXUS_NATIVE_GUI_CAPTURE_DIR='C:\Temp\polynexus_native_saxs_visual_20260728_fixed'
python -m pytest -q --basetemp=C:\Temp\polynexus_native_saxs_visual_base_20260728_fixed tests/test_native_gui_real_route_capture.py -k saxs -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-28-results-workbench-tab-opacity.md --changed --types
```

## Known limitations

Restarted-GUI visual review for every technique and scientific meaning review
remain open in the full-software task.
