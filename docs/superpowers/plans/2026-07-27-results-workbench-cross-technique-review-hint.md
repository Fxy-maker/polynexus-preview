# Results Workbench Cross-technique Review Hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing structured result review text into every customized Results Workbench profile.

**Architecture:** Keep analysis and evidence adapters authoritative. The MainWindow output mixin only chooses whether existing text belongs in the shared panel, and the panel only renders it. Profile metadata supplies the localized generic action; SAXS temperature/strain retains its existing specialized action.

**Tech Stack:** Python 3.14, PySide6, pytest, existing i18n and Workbench contracts.

---

### Task 1: Lock non-SAXS projection and translation behavior with TDD

**Files:**
- Modify: `tests/test_main_window_output_mixin.py`
- Modify: `tests/test_results_table_panel.py`

- [x] **Step 1: Write the failing MainWindow test**

Add a recorder case with technique=`dsc`, submodule=`dsc.standard`, an attached
profile `profile_for("dsc.standard")`, and summary/risk/next text. Assert one
`set_review_hint` call uses the existing text, status=`review`, the profile's
`review_action.label`, and a callable Results-tab callback.

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_workbench_review_hint_red'
python -m pytest tests/test_main_window_output_mixin.py tests/test_results_table_panel.py -q
```

Expected result: the new DSC projection assertion fails because the current
implementation clears all non-SAXS hints.

- [x] **Step 3: Write the failing panel retranslation test**

Set a hint with action text equal to `tr_for_language("RESULTS_WORKBENCH_REVIEW_ACTION", "en")`, call the existing `retranslate()` path after switching language, and assert the action text is refreshed to the Chinese translation.

- [x] **Step 4: Run RED for the panel assertion**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_workbench_review_hint_red_panel'
python -m pytest tests/test_results_table_panel.py -q
```

Expected result: the action text remains stale because only the SAXS key is
currently recognized.

### Task 2: Implement the minimal shared projection

**Files:**
- Modify: `polynexus/gui/main_window_output_mixin.py`
- Modify: `polynexus/gui/widgets/results_table_panel.py`

- [x] **Step 1: Preserve SAXS-specific routing**

Keep the current SAXS temperature/strain branch and its localized title/action.
For other techniques, obtain `panel.profile`; if it is absent or its key is
`generic`, clear the hint. Otherwise use `summary_text or profile.title`, the
existing risk/next text, `profile.review_action.label`, and the same Results-tab
callback.

- [x] **Step 2: Recognize the shared action translation key**

Extend `ResultsTablePanel.set_review_hint()`'s existing action-key detection to
recognize both `SAXS_RESULTS_REVIEW_HINT_ACTION` and
`RESULTS_WORKBENCH_REVIEW_ACTION`, without changing arbitrary custom action
text behavior.

### Task 3: Verify and checkpoint

**Files:**
- Modify: this task card
- Modify: the implementation plan

- [x] **Step 1: Run the focused GREEN matrix**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_workbench_review_hint_green'
python -m pytest tests/test_main_window_output_mixin.py tests/test_results_table_panel.py tests/test_results_table_service.py tests/test_results_workbench_profiles.py -q
```

- [x] **Step 2: Run the structured verifier and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-results-workbench-cross-technique-review-hint.md --changed --types
git diff --check
```

Record exact counts and limitations; do not reuse older full/boundary output.

- [ ] **Step 3: Create an explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "feat(gui): project cross-technique review hints" --files polynexus/gui/main_window_output_mixin.py polynexus/gui/widgets/results_table_panel.py tests/test_main_window_output_mixin.py tests/test_results_table_panel.py docs/agent/tasks/2026-07-27-results-workbench-cross-technique-review-hint.md docs/superpowers/specs/2026-07-27-results-workbench-cross-technique-review-hint-design.md docs/superpowers/plans/2026-07-27-results-workbench-cross-technique-review-hint.md
```

The allowlist must exclude all pre-existing scratch and parallel-task files.
