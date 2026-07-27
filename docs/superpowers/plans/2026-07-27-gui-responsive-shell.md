# GUI responsive shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove right-edge clipping from the canonical Results Workbench shell
at default and maximized desktop sizes while preserving menu-based actions.

**Architecture:** Keep responsive policy in `MainWindowShellMixin`. The mixin
will measure the actual content/header and top-bar layouts, collapse optional
widgets in a fixed priority order, and leave the task card and canonical menu
routes intact. MainWindow will expose the top-bar widget and make flexible
header controls compressible; no technique-specific code changes.

**Tech Stack:** Python, PySide6, pytest, offscreen Qt, PowerShell launcher.

---

### Task 1: Lock the content-width regression

**Files:**
- Modify: `tests/test_main_window_shell_mixin.py`
- Read: `polynexus/gui/main_window_shell_mixin.py`

- [x] Add a fake shell window whose full width is wide but whose content width
  is compact, with visibility-tracking metric, task-card, and shortcut widgets.
- [x] Assert that compact content hides metrics and shortcuts while keeping the
  task card visible.
- [x] Run the focused test and observe the expected failure because the current
  mixin consults only `self.width()` and does not collapse these widgets.

### Task 2: Implement compact shell policy

**Files:**
- Modify: `polynexus/gui/main_window_shell_mixin.py`
- Test: `tests/test_main_window_shell_mixin.py`

- [x] Add a small width helper that returns `_content.width()` when available
  and falls back to `self.width()` for existing lightweight test doubles.
- [x] Apply a stable priority: hide workflow metrics first, then replot and
  current/project export shortcuts only when the top bar overflows; never hide
  the task card or menu actions.
- [x] Run the focused shell tests and confirm the regression is green.

### Task 3: Make MainWindow flexible widgets shrinkable

**Files:**
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Test: `tests/test_main_window_shell_mixin.py`,
  `tests/test_ui_function_streamlining.py`

- [x] Store the top-bar widget for overflow measurement.
- [x] Set minimum widths to zero and compressible horizontal policies on the
  task-card labels and optional header metrics where the existing layout
  otherwise propagates long text minimums.
- [x] Wrap the History action toolbar in a zero-minimum horizontal scroll area
  so its long action row does not become the minimum width of the full tab set.
- [x] Preserve the existing minimum supported window size and canonical menu
  routes; run the GUI-focused matrix.

### Task 4: Verify runtime and record acceptance

**Files:**
- Modify: `docs/acceptance/2026-07-27-gui-responsive-shell.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`
- Test: all files in the task allowlist

- [x] Run the focused tests and the task-scoped verifier with an external
  basetemp.
- [x] Run the full/boundary verifier and record exact counts and warnings.
- [x] Restart the canonical GUI, run `--diagnose`, maximize the window, and
  capture a fresh screenshot proving the header and top-bar are inside bounds.
- [ ] Create one checkpoint with `scripts/auto_commit.py` using the explicit
  allowlist, leaving pre-existing scratch untouched.
