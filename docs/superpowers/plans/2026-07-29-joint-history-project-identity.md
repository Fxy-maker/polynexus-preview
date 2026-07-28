# Joint History Project Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a restored Joint run expose its persisted/report sample identity in the Workbench project badge instead of showing the default `No project` label.

**Architecture:** Keep the Joint report and scientific contracts unchanged. The history restore boundary will derive a display-only project label from the persisted `project_label` when meaningful, otherwise from the Joint report's row samples; one sample uses its name and multiple samples use the translated Joint workspace label. Empty reports retain the existing default label.

**Tech Stack:** Python, PySide6 MainWindow history mixin, existing Joint lifecycle tests, pytest, Ruff, repository verifier.

---

### Task 1: Reproduce the restored Joint identity defect

**Files:**
- Modify: `tests/test_joint_lifecycle_closure.py`
- Read: `polynexus/gui/main_window_history_mixin.py`

- [ ] Add an assertion that restoring the existing `PA6-A` Joint report sets
  `window._project_label` to `PA6-A`.
- [ ] Run the focused lifecycle test and observe the expected `No project`
  failure before changing production code.

### Task 2: Implement the minimal display-label projection

**Files:**
- Modify: `polynexus/gui/main_window_history_mixin.py`
- Modify: `tests/test_joint_lifecycle_closure.py`

- [ ] Restore an explicit non-default `results_summary.project_label` when it
  exists.
- [ ] For Joint reports without a meaningful project label, derive one sample
  name from `report.rows[*].sample`; use the translated Joint workspace label
  for multiple samples and keep `No project` for an empty report.
- [ ] Keep data paths, run IDs, report values, validation severities, and
  provenance unchanged.

### Task 3: Verify and checkpoint

- [ ] Run the focused Joint lifecycle/history matrix and `git diff --check`.
- [ ] Run the task-scoped verifier with an external basetemp.
- [ ] Create one explicit allowlist checkpoint using `scripts/auto_commit.py`.

## Scope audit

- No Joint formula, threshold, conflict severity, scientific assignment, or
  publication role changes.
- No raw-file ingestion or new cross-layer contract.
- The project label is UI identity metadata only; it must never be consumed as
  a scientific value.
