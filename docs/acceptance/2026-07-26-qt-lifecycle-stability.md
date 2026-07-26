# Qt lifecycle stability acceptance

## Delivered so far

- `FigureFilePreview` deferred fit callbacks are now parent-owned timers.
- MainWindow's workspace summary QLabel no longer shadows the summary method.
- ChartEditor test windows are isolated during teardown.

## Verification evidence

```text
python -m pytest tests/test_chart_viewer_lifecycle.py tests/test_chart_viewer.py -q
23 passed in 0.57s

python -m pytest tests/test_chart_editor.py tests/test_dsc_lifecycle_closure.py -q
251 passed in 50.85s

python -m pytest tests/test_main_window_workspace_mixin.py tests/test_main_window_summary_mixin.py tests/test_main_window_ai_tuning_mixin.py tests/test_main_window_persistence.py -q -k "workspace or ai_tuning_workspace_context"
11 passed in 11.75s

python -m pytest --basetemp=C:\Temp\PolyNexus_qt_persistence_full tests/test_main_window_persistence.py -q --durations=20
197 passed in 216.23s (0:03:36)
```

## Verification boundary

The focused Qt matrices and the complete MainWindow persistence file pass.
`python scripts/verify.py --task docs/agent/tasks/2026-07-26-qt-lifecycle-stability.md --changed --types`
currently stops in the changed-file Ruff phase because the existing
`polynexus/gui/main_window.py` baseline has 150 errors at `HEAD` (151 with the
scoped rename). That import baseline is outside this lifecycle task and was
left untouched. The allowlisted checkpoint is therefore pending until the
baseline decision is resolved.
