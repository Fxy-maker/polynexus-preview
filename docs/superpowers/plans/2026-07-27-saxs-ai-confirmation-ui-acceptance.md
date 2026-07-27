# SAXS AI Confirmation UI Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a real SAXS GUI-route regression and durable acceptance evidence for user-confirmed AI preprocessing.

**Architecture:** Reuse the existing `SideTuningReportDialog`, `MainWindowAITuningMixin`, and `PreprocessTransactionService` contracts. The test drives the real dialog button and observes the existing transaction boundary; it does not add a second GUI decision path or bypass SAXS gates.

**Tech Stack:** Python, PySide6 offscreen widgets, pytest, repository task/spec/checkpoint tooling.

---

### Task 1: Establish the SAXS confirmation GUI-route regression

**Files:**
- Create: `tests/test_saxs_ai_confirmation_gui_route.py`
- Modify: none in production code unless the RED test identifies a real route defect

- [x] **Step 1: Write the failing test**

Add a test fixture that supplies a minimal existing-gate-passing SAXS result,
an unchanged `smooth_window` configuration, and a valid
`request_confirmation` report whose candidate hash matches that configuration.
Instantiate the real `MainWindow`, configure its SAXS engine cache, and patch
only the modal `exec` method so it clicks the real enabled Apply button. Assert
that the route invokes the existing apply and rerun callbacks, creates one
`apply_pending` SAXS transaction, and leaves a rejected dialog as `idle`.

- [x] **Step 2: Run the focused test to verify RED or existing GREEN**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_saxs_ai_confirmation_gui_route.py -q
```

Expected for a missing route: a focused assertion failure identifying the
missing transaction start. If the current route already satisfies the test,
record that the test is an acceptance regression for existing behavior and do
not add production code.

- [x] **Step 3: If RED, implement only the minimal route fix**

Change only the smallest existing GUI boundary needed to preserve this flow:
the real dialog's enabled Apply result must reach
`_begin_preprocess_confirmation(report, accepted_by="user_confirmed")` for
SAXS. Do not call `_run_analysis` directly from the dialog branch, do not add
new physical thresholds, and do not move gate logic into the GUI.

- [x] **Step 4: Run the focused test to verify GREEN**

Run the same focused command and require zero failures. Then run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_saxs_ai_confirmation_gui_route.py tests/test_preprocess_decision_dialog.py tests/test_saxs_ai_confirmed_rerun_safety.py -q
```

Expected: all focused GUI and SAXS confirmation tests pass; any existing Qt
font warnings are reported but are not reclassified as failures.

### Task 2: Record the audit and update durable limitations

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md`
- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/memory/current-state.md`

- [x] **Step 1: Record exact evidence**

Add the actual focused command results, the exact changed-file allowlist, and
the fact that no production code changed if the route was already closed.

- [x] **Step 2: State remaining gates precisely**

Replace the stale statement that the user confirmation UI is entirely open
with the narrower boundary: automated route and transaction contracts are
covered; restarted-GUI visual inspection, real-data scientific review, and
human release approval remain open.

- [x] **Step 3: Verify the structured task**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md --changed --types
git diff --check
```

Record the exact outcomes. Do not claim a full repository pass unless a fresh
full/boundary command completes with exit code zero and a boundary audit pass.

- [x] **Step 4: Create one explicit checkpoint**

Use `scripts/auto_commit.py` with only the task card, spec, plan, focused test,
and the two durable memory files when they have actual changes. Do not include
GUI scratch, generated outputs, temporary pytest directories, or unrelated
parallel work.
