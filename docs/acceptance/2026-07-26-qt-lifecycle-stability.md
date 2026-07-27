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

The focused Qt matrices, MainWindow persistence file, structured verifier, and
current full/boundary verifier are green. The full run completed with `2671
passed, 10 warnings` in `1644.65s`; the boundary audit passed. The warnings are
the existing Qt tight-layout, DSC polyfit-conditioning, and SAXS CJK glyph
warnings. The lifecycle checkpoint is `fbf22b6`; GUI restart review and human
scientific/publication review remain outside this automated note.
