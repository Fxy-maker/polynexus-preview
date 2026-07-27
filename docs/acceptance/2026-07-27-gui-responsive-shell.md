# GUI responsive shell acceptance — 2026-07-27

## Result

The restarted canonical GUI shell now fits its Workbench content to the
available viewport at the default and maximized sizes. The task card remains
visible; optional workflow metrics and top-bar shortcuts collapse below the
content-width threshold, while History actions remain available inside an
internal horizontal scroll container.

## Evidence

- TDD RED: the compact-content regression failed against the old
  window-width-only policy; the title-label regression failed before
  compressible policies; the History minimum-width regression failed at
  `1200px` before the scroll container.
- Focused GUI matrix: `18 passed`:
  `tests/test_main_window_shell_mixin.py`
  `tests/test_ui_function_streamlining.py`.
- Full deferred-startup Qt grab diagnostics:
  - default: viewport `1036`, content `1036`, task geometry `(578, 10, 412, 128)`;
  - maximized: viewport `1486`, content `1486`, task geometry `(1028, 10, 412, 128)`;
  - History minimum width after the change: `94px`.
- `python scripts/launch_gui.py --diagnose` resolved the canonical source root
  `D:\PolyNexus`, branch `codex/origin-editor-usable-controls`, and package
  `D:\PolyNexus\polynexus\__init__.py`.
- Task-scoped quality/preprocessing evidence after the GUI-only lint fix:
  quality `282 passed`; preprocessing `106 passed`.
- Fresh focused GUI rerun: `18 passed in 6.50s`.
- Fresh task-scoped verifier with an isolated basetemp passed task/memory,
  Ruff, compile/type baseline, quality `282`, preprocessing `106`, and
  whitespace checks.
- Fresh full/boundary verifier passed `2773 passed, 10 warnings in 1451.67s`;
  the boundary audit also passed. Existing warnings were tight-layout,
  DSC polynomial-conditioning, and Arial CJK glyph warnings.
- The prescribed full suite completed with `2685 passed, 1 failed, 10
  warnings` in `1558.50s`; the single failure was the known order-sensitive
  ChartEditor/Matplotlib-Qt crop test. The same test passed alone and the
  ChartEditor + DSC lifecycle matrix passed `251 passed`.

## Verification limitation

The repository task verifier's changed-file Ruff phase still includes a
pre-existing modified SAXS file (`polynexus/core/saxs.py`) and reports its 24
baseline lint findings. That file and the related pre-existing SAXS evidence
changes were intentionally left outside this GUI task's allowlist. Direct
Ruff/compile checks for the GUI files and the focused GUI tests pass.

The older full-suite failure is retained as historical evidence only. The
fresh full/boundary run above is the current repository-level result and
passed; it supersedes that order-sensitive failure for this acceptance.

## Remaining release gates

This closes the concrete shell clipping defect only. It does not close the
full-software goal's restarted-GUI walkthrough for every technique, real-data
scientific sign-off, IR vendor mapping confirmation, NMR/Joint scientific
review, AI model/apply review, or final release approval.
