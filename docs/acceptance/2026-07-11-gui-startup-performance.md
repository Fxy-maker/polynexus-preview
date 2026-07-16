# GUI Startup Performance Acceptance

**Date:** 2026-07-11

## Result

The GUI entry point now imports the application shell lazily and opts into a deferred startup mode. The main window first creates the shell and data-entry surface; configuration, results, plots, history, sample browser, and joint-analysis widgets are built after the window is shown through the Qt event loop. `MainWindow()` without the keyword remains synchronous for compatibility.

## Measured startup evidence

Measured with `QT_QPA_PLATFORM=offscreen` on the current Windows/Python 3.12 environment:

- First window visible after `show()` and one `processEvents()` cycle: approximately 1.90 seconds.
- Deferred optional UI complete: approximately 2.18 seconds.
- Fresh-process `main(startup_probe=True)`: approximately 2.67 seconds.

These timings are environment-dependent and are evidence for this workspace, not a cross-machine performance baseline.

## Changed files

- `polynexus/app.py`
- `polynexus/gui/main_window.py`
- `tests/test_gui_startup.py`
- `docs/superpowers/specs/2026-07-11-gui-startup-performance-design.md`
- `docs/superpowers/plans/2026-07-11-gui-startup-performance.md`
- `docs/agent/tasks/2026-07-11-gui-startup-performance.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/decisions/0002-gui-startup-deferred-ui.md`
- `docs/agent/memory/lessons/0002-qt-scientific-import-order.md`

## Verification

| Command | Result |
| --- | --- |
| `$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_gui_startup.py -q` | 3 passed |
| `$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_main_window_persistence.py -q` | 222 passed |
| `$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_gui_startup.py tests/test_main_window_settings_mixin.py tests/test_main_window_workspace_mixin.py tests/test_main_window_navigation_mixin.py -q` | 11 passed |
| `python -m compileall polynexus tests -q` | passed |
| `ruff check polynexus/app.py tests/test_gui_startup.py` | passed |
| `git diff --check` | passed |
| `python scripts/verify.py --changed --types` | blocked by existing `main_window.py` Ruff findings (149 errors); type phase was not reached |
| `pyright polynexus/app.py polynexus/gui/main_window.py tests/test_gui_startup.py` | existing GUI baseline reports 85 PySide6/type errors |

## Known limitations

- The current dependency combination requires preloading `polynexus.core` before PySide6 to avoid a Shiboken/dateutil import-hook failure; that preload remains in the startup path.
- The unified verification command cannot pass until the repository's existing `main_window.py` Ruff and Pyright baselines are addressed in a separate maintenance task.
- Optional tabs briefly show loading placeholders; the data-entry surface is usable during that interval.

## Pre-existing workspace changes

Existing changes in `pyproject.toml`, `.github/`, `.superpowers/`, `AGENTS.md`, `docs/agent/`, other plans, `scripts/verify.py`, `scripts/agent_memory.py`, `tests/eval/test_runner_real_nmr.py`, `tests/test_agent_workflow_tools.py`, `pyrightconfig.json`, and `uv.lock` were intentionally preserved and not cleaned up.
