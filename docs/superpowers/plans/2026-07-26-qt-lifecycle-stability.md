# Qt lifecycle stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent deferred Qt callbacks and workspace-summary name collisions
from breaking full-software verification.

**Architecture:** Keep scientific and figure contracts unchanged. Make delayed
preview work QObject-owned, separate the GUI label from the summary method, and
isolate test-created ChartEditor windows at the test boundary.

**Tech Stack:** Python, PySide6, pytest, offscreen Qt.

---

### Task 1: Lock the preview deletion failure

**Files:**
- Create: `tests/test_chart_viewer_lifecycle.py`
- Read: `polynexus/gui/widgets/chart_viewer.py`

- [x] Create a preview, schedule fit callbacks, delete it, and process deferred
  events.
- [x] Observe the pre-fix `QGraphicsScene already deleted` failure.

### Task 2: Make deferred preview work QObject-owned

**Files:**
- Modify: `polynexus/gui/widgets/chart_viewer.py`
- Test: `tests/test_chart_viewer_lifecycle.py`, `tests/test_chart_viewer.py`

- [x] Add parent-owned single-shot timers for immediate and delayed fitting.
- [x] Stop both timers when the preview is cleared.
- [x] Replace all preview `QTimer.singleShot` calls and run the focused viewer
  matrix.

### Task 3: Repair GUI method/label collision and test isolation

**Files:**
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/main_window_workspace_mixin.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_main_window_persistence.py`,
  `tests/test_main_window_workspace_mixin.py`,
  `tests/test_main_window_ai_tuning_mixin.py`

- [x] Rename the MainWindow label storage and retain fake-window compatibility.
- [x] Close leaked ChartEditor test windows without invoking production prompts.
- [x] Run the AI tuning/workspace matrix and the editor-plus-DSC sequence.

### Task 4: Verify and checkpoint

**Files:**
- Modify: `docs/acceptance/2026-07-26-qt-lifecycle-stability.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Create: `docs/agent/tasks/2026-07-26-qt-lifecycle-stability.md`

- [ ] Run focused, changed/type, default, and full/boundary verification.
- [ ] Record exact pass/fail/timeout evidence and preserve unrelated scratch.
- [ ] Create one allowlisted checkpoint commit.

