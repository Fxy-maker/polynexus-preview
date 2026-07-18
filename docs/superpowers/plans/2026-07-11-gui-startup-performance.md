# GUI Startup Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show an interactive PolyNexus main window quickly by separating first-screen construction from optional GUI initialization.

**Architecture:** Keep `MainWindow()` synchronous for compatibility, while the application entry point opts into a deferred startup mode. The deferred mode builds only the shell and data-entry surface before showing the window, then replaces loading tabs with the existing widgets from the Qt event loop using an idempotent completion method.

**Tech Stack:** Python 3.10+, PySide6, pytest, existing MainWindow mixins and widgets.

---

### Task 1: Add the startup regression harness

**Files:**
- Create: `tests/test_gui_startup.py`
- Modify: `polynexus/app.py` only if the test needs a probe seam

- [ ] **Step 1: Write the failing tests**

Add tests that construct `MainWindow(defer_optional_ui=True)` under an offscreen `QApplication`, assert the data-entry surface exists before deferred completion, call the completion method twice, and assert the existing tabs and widgets exist exactly once. Add an entry test that imports `polynexus.app` without importing `MainWindow` at module import time.

- [ ] **Step 2: Run the focused tests and verify the expected failure**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_gui_startup.py -q
```

Expected: collection or execution fails because the deferred constructor and completion seam do not yet exist.

- [ ] **Step 3: Keep the test independent of scientific results**

Use only Qt widget existence, tab labels/counts, signal-safe repeated completion, and import behavior. Do not load real regression datasets or call an analysis engine.

### Task 2: Implement lazy entry import and deferred GUI construction

**Files:**
- Modify: `polynexus/app.py`
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/widgets/chart_viewer.py` only if top-level imports remain on the critical path
- Modify: `polynexus/gui/widgets/joint_analysis_hub.py` only if top-level imports remain on the critical path

- [ ] **Step 1: Make the application entry import Qt and MainWindow lazily**

Keep `polynexus.app` importable without importing `MainWindow` at module collection time. In `main()`, create `QApplication`, import `MainWindow`, construct it with `defer_optional_ui=True`, show it, and schedule deferred initialization before entering `app.exec()`.

- [ ] **Step 2: Add a compatibility-preserving deferred mode**

Extend `MainWindow.__init__` with a keyword-only `defer_optional_ui=False` parameter. Initialize all state needed by the first screen in both modes. In deferred mode, build the existing shell and data tab plus loading placeholders for optional tabs; do not construct chart, sample browser, joint hub, history, or other heavy optional widgets before `show()`.

- [ ] **Step 3: Add an idempotent completion path**

Implement `schedule_deferred_startup()` and `finish_deferred_startup()`. The scheduler must use `QTimer.singleShot` and prevent duplicate scheduling. The completion method must replace placeholders in the same tab order as synchronous mode, connect existing signals once, retranslate and apply the current theme, then mark startup complete. Any exception must be logged and surfaced in the optional area without making the first screen unusable.

- [ ] **Step 4: Preserve synchronous behavior**

When `defer_optional_ui=False`, retain the existing builder sequence and make `finish_deferred_startup()` a no-op. Existing callers and tests that instantiate `MainWindow()` must still see the complete widget set immediately.

### Task 3: Add timing evidence and focused verification

**Files:**
- Modify: `tests/test_gui_startup.py`
- Create: `docs/acceptance/2026-07-11-gui-startup-performance.md`
- Modify: `docs/agent/memory/active-work.md`
- Add decision entry under: `docs/agent/memory/decisions/`

- [ ] **Step 1: Add stage timing assertions without a brittle global threshold**

Record monotonic timestamps for application construction, main-window show, first event processing, and deferred completion. Assert ordering and that the first event cycle completes; report the measured values for the normal dependency environment.

- [ ] **Step 2: Run focused GUI tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; pytest tests/test_gui_startup.py tests/test_main_window_persistence.py -q
```

- [ ] **Step 3: Run the required project verification**

Run:

```powershell
python scripts/verify.py --changed --types
```

Expected: exit code 0, with changed-file compile/type checks completed. If the pre-existing dependency mismatch prevents GUI execution, report the exact failure separately.

- [ ] **Step 4: Review the complete diff and document handoff**

Run `git diff --check` and `git status --short`. Update the acceptance note with changed files, measured timings, verification outcomes, limitations, and untouched pre-existing changes. Do not commit or push.
