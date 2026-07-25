# History Gallery restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Reload the active manifest Gallery when a persisted analysis run is restored.

**Architecture:** Keep History responsible for restoring state and delegate figure
  discovery to the existing manifest-only Gallery population boundary. No figure
  files are guessed and no scientific analysis is rerun.

**Tech Stack:** Python, PySide6, pytest, FigurePipeline.

---

### Task 1: Regression and minimal fix

**Files:**

- Modify: `tests/test_main_window_persistence.py`
- Modify: `polynexus/gui/main_window_history_mixin.py`

- [x] Add a failing test with an actual IR FigurePipeline manifest and history
  record pointing to its output root.
- [x] Verify the test fails because `_chart_gallery.figure_ids()` is empty.
- [x] Call `_populate_plots()` after restoring `output_dir`.
- [x] Verify the focused test passes.

### Task 2: Checkpoint

**Files:**

- Create: this task card, design, and plan.

- [x] Run task-scoped verifier and inspect `git diff --check`.
- [ ] Commit only the listed source, test, and planning files with
  `scripts/auto_commit.py`; do not stage existing scratch.
