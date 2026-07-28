# Results Workbench main-Tab opacity acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-28-results-workbench-tab-opacity.md`
Status: automated acceptance passed

## Evidence

- Focused Results/MainWindow selection returned `23 passed in 5.42s`, exit
  code `0`.
- Native Windows route:
  `python -m pytest -q tests/test_native_gui_real_route_capture.py -k saxs -vv`
  returned `3 passed, 14 deselected in 57.98s`, exit code `0`, using external D:
  capture and basetemp. SAXS static, temperature, and strain each completed
  Results/Gallery/History/Editor capture.
- The production behavior was previously checkpointed in `2e0fe50`; this
  acceptance record changes no GUI source, scientific result, or fixture.

## Boundary

The shared main Tab pages remain opaque while local transient effects are
preserved. Restarted-GUI review for every technique, scientific review, and
final release approval remain open.
