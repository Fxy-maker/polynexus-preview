# AI Preprocessing GUI Confirmation and Transaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a report-driven preprocessing decision view and a transactional GUI confirmation/apply/undo path without changing scientific preprocessing or unrelated GUI boundaries.

**Architecture:** Keep report interpretation in a pure `preprocess_decision_service.py`. Put snapshot, apply, rerun, rollback, undo, and experience-persistence state transitions in a callback-driven `preprocess_transaction_service.py`. Integrate both through the existing AI tuning dialog and run callbacks; the GUI mixin supplies widgets and callbacks but does not make scientific decisions.

**Tech Stack:** Python 3.10+, dataclasses, PySide6, pytest, existing `ExperienceStore` and `MainWindow` run lifecycle.

---

## File map

- `polynexus/gui/preprocess_decision_service.py`: immutable report-to-UI decision projection.
- `polynexus/gui/preprocess_transaction_service.py`: callback-driven transaction state machine.
- `polynexus/gui/main_window.py`: show protected metrics/reasons and enable only valid actions.
- `polynexus/gui/main_window_ai_tuning_mixin.py`: connect dialog actions to the transaction service.
- `polynexus/gui/main_window_run_mixin.py`: finalize or roll back pending transactions after rerun callbacks.
- `tests/test_preprocess_decision_service.py`: pure decision projection tests.
- `tests/test_preprocess_transaction_service.py`: transaction and failure-path tests.
- `tests/test_main_window_ai_tuning_mixin.py`: existing mixin regression plus integration seam tests.
- `tests/test_preprocess_decision_dialog.py`: offscreen dialog behavior tests.

Do not modify Editor/Export modules, publication-pack modules, Unified Tables modules, or preprocessing core algorithms in this plan.

### Task 1: Add the immutable decision view model

**Files:**
- Create: `polynexus/gui/preprocess_decision_service.py`
- Create: `tests/test_preprocess_decision_service.py`

- [ ] **Step 1: Write failing tests for all decision modes and evidence selection**

```python
def test_confirmation_exposes_selected_metrics_and_apply():
    view = build_preprocess_ui_decision(report_with("request_confirmation", "medium"))
    assert view.mode == "confirm"
    assert view.apply_enabled is True
    assert view.undo_enabled is False
    assert "weak_peak_retention" in view.metric_rows


def test_auto_accept_exposes_undo_without_reapplying():
    view = build_preprocess_ui_decision(report_with("auto_accept", "high"))
    assert view.mode == "auto_apply"
    assert view.apply_enabled is False
    assert view.undo_enabled is True


def test_shadow_and_invalid_reports_are_informational():
    shadow = build_preprocess_ui_decision(
        report_with("keep_original", "high", simulated="auto_accept")
    )
    invalid = build_preprocess_ui_decision({"preprocess_decision": "invalid"})
    assert shadow.mode == "shadow"
    assert shadow.apply_enabled is False
    assert invalid.mode == "keep_original"
    assert invalid.apply_enabled is False
    assert invalid.undo_enabled is False


def test_selected_candidate_controls_evidence_projection():
    report = report_with("request_confirmation", "medium")
    report["selected_candidate_id"] = "selected"
    report["preprocess_evidence"] = [
        {"candidate_id": "other", "weak_peak_retention": 0.0},
        {"candidate_id": "selected", "weak_peak_retention": 1.0},
    ]
    view = build_preprocess_ui_decision(report)
    assert view.metric_rows["weak_peak_retention"] == 1.0
```

- [ ] **Step 2: Run the new tests and verify the expected import failure**

Run: `python -m pytest tests/test_preprocess_decision_service.py -q`

Expected: FAIL with `ModuleNotFoundError` because the service does not exist.

- [ ] **Step 3: Implement the pure projection**

Define `PreprocessUIDecision` as a frozen dataclass with `mode`, `title`,
`summary`, `metric_rows`, `reason_codes`, `apply_enabled`, `undo_enabled`, and
`selected_config`. Define `PROTECTED_METRICS` as the seven evidence fields used
by the current decision contract. `build_preprocess_ui_decision(report)` must
accept any object, treat non-dicts and malformed nested values as empty data,
and use this exact mode mapping:

```python
if decision == "auto_accept":
    mode, apply_enabled, undo_enabled = "auto_apply", False, True
elif decision == "request_confirmation":
    mode, apply_enabled, undo_enabled = "confirm", True, False
elif simulated != "keep_original":
    mode, apply_enabled, undo_enabled = "shadow", False, False
else:
    mode, apply_enabled, undo_enabled = "keep_original", False, False
```

Match evidence by `selected_candidate_id`; otherwise use the last dict row. Copy
all returned mappings so a dialog cannot mutate the orchestration report.

- [ ] **Step 4: Run the view-model tests**

Run: `python -m pytest tests/test_preprocess_decision_service.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the isolated view-model slice**

```powershell
git add polynexus/gui/preprocess_decision_service.py tests/test_preprocess_decision_service.py
git commit -m "feat(gui): add preprocessing decision view model"
```

### Task 2: Add the transactional apply/undo service

**Files:**
- Create: `polynexus/gui/preprocess_transaction_service.py`
- Create: `tests/test_preprocess_transaction_service.py`

- [ ] **Step 1: Write failing transaction tests**

```python
def test_confirmation_persists_experience_only_after_successful_rerun(harness):
    assert harness.service.begin_confirmation(harness.report(), accepted_by="user_confirmed")
    assert harness.config == {"smooth_window": 15}
    assert harness.persisted == []
    harness.service.finalize_success()
    assert harness.persisted == [("preprocess-c1", "user_confirmed")]
    assert harness.service.state.phase == "applied"


def test_rerun_failure_restores_config_and_result_without_experience(harness):
    harness.service.begin_confirmation(harness.report(), accepted_by="user_confirmed")
    harness.result = {"status": "partial"}
    harness.service.rollback_failure()
    assert harness.config == {"smooth_window": 11}
    assert harness.result is harness.original_result
    assert harness.persisted == []
    assert harness.service.state.phase == "failed"


def test_auto_accept_registers_existing_commit_without_second_apply(harness):
    harness.service.register_auto_accept(harness.report(), previous_config={"smooth_window": 11})
    assert harness.apply_calls == []
    assert harness.service.state.phase == "applied"


def test_undo_revokes_experience_only_after_undo_rerun_success(harness):
    harness.service.begin_confirmation(harness.report(), accepted_by="user_confirmed")
    harness.service.finalize_success()
    assert harness.service.undo() is True
    assert harness.config == {"smooth_window": 11}
    assert harness.revoked == []
    harness.service.finalize_success()
    assert harness.revoked == ["preprocess-c1"]
    assert harness.service.state.phase == "undone"
```

The harness must use real callbacks and a mutable fake config/result, not mocks
of the service itself. It must record `apply_calls`, persisted IDs, revoked
IDs, and rerun calls.

- [ ] **Step 2: Run the transaction tests and verify they fail for the missing service**

Run: `python -m pytest tests/test_preprocess_transaction_service.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the explicit state machine**

Define:

```python
@dataclass
class PreprocessTransactionState:
    phase: str = "idle"
    technique: str = ""
    previous_config: dict[str, Any] = field(default_factory=dict)
    selected_config: dict[str, Any] = field(default_factory=dict)
    previous_result: Any = None
    proposal: dict[str, Any] = field(default_factory=dict)
    accepted_by: str = ""
    experience_id: str = ""
```

`PreprocessTransactionService` receives callbacks for `capture_config(keys)`,
`apply_config(config)`, `get_result()`, `set_result(result)`, `rerun()`,
`persist_experience(proposal, accepted_by)`, and `revoke_experience(id)`.

`begin_confirmation` accepts only a `confirm` view, captures the prior config
and result, applies the selected config, and changes phase to
`apply_pending`. Any exception restores both snapshots and changes phase to
`failed`. `register_auto_accept` records the already-committed transaction
using `report["original_preprocess_config"]` or the supplied prior config and
does not call `apply_config` or `rerun`.

`finalize_success` persists a non-empty proposal only for `apply_pending`, then
sets phase to `applied`; for `undo_pending`, it revokes the stored experience
and sets phase to `undone`. Persistence failure leaves the applied result in
place, leaves `experience_id` empty, and records phase `applied`.

`rollback_failure` restores the snapshot for `apply_pending`, or restores the
selected config/result for `undo_pending`. `undo` is allowed only from
`applied`, captures the current selected state, applies the previous config,
and sets `undo_pending`; failure restores the selected state and returns
`False`.

- [ ] **Step 4: Run transaction tests and verify all pass**

Run: `python -m pytest tests/test_preprocess_transaction_service.py -q`

Expected: all transaction tests pass.

- [ ] **Step 5: Commit the transaction service slice**

```powershell
git add polynexus/gui/preprocess_transaction_service.py tests/test_preprocess_transaction_service.py
git commit -m "feat(gui): add transactional preprocessing apply service"
```

### Task 3: Integrate the decision view into the existing report dialog

**Files:**
- Modify: `polynexus/gui/main_window.py` near `SideTuningReportDialog` imports and button construction.
- Create: `tests/test_preprocess_decision_dialog.py`

- [ ] **Step 1: Write failing offscreen dialog tests**

```python
def test_confirm_dialog_enables_apply_and_uses_selected_config():
    app = QApplication.instance() or QApplication([])
    dialog = SideTuningReportDialog(report_with("request_confirmation", "medium"))
    assert dialog.best_config() == {"smooth_window": 15}
    assert dialog._buttons.button(QDialogButtonBox.Ok).isEnabled() is True
    assert "weak_peak_retention" in dialog._preprocess_metrics_label.text()


def test_shadow_disables_apply_and_auto_accept_offers_undo():
    app = QApplication.instance() or QApplication([])
    shadow = SideTuningReportDialog(report_with("keep_original", "high", simulated="auto_accept"))
    auto = SideTuningReportDialog(report_with("auto_accept", "high"))
    assert shadow._buttons.button(QDialogButtonBox.Ok).isEnabled() is False
    assert "Undo" in auto._buttons.button(QDialogButtonBox.Ok).text()
```

- [ ] **Step 2: Run dialog tests and verify the missing integration fails**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_preprocess_decision_dialog.py -q`

Expected: FAIL because `SideTuningReportDialog` does not yet render the decision model.

- [ ] **Step 3: Add informational decision content and button gating**

Import `build_preprocess_ui_decision`, create a read-only label for title,
summary, protected metrics, and reason codes when `preprocess_decision` is in
the report. Keep the existing dialog unchanged for ordinary AI tuning reports.
Store the decision view on the dialog, return its copied selected config from
`best_config()`, disable Apply for `shadow`/`keep_original`, and label the
enabled action `Undo` for `auto_apply`.

- [ ] **Step 4: Run dialog and existing GUI tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_preprocess_decision_dialog.py tests/test_main_window_ai_tuning_mixin.py -q`

Expected: all focused GUI tests pass.

- [ ] **Step 5: Commit the dialog slice**

```powershell
git add polynexus/gui/main_window.py tests/test_preprocess_decision_dialog.py
git commit -m "feat(gui): show preprocessing decision evidence"
```

### Task 4: Connect confirmation, auto-accept undo, and rerun callbacks

**Files:**
- Modify: `polynexus/gui/main_window_ai_tuning_mixin.py`
- Modify: `polynexus/gui/main_window_run_mixin.py`
- Modify: `polynexus/gui/main_window.py` only for transaction-service construction/state initialization.
- Modify: `tests/test_main_window_ai_tuning_mixin.py`

- [ ] **Step 1: Write failing mixin transaction-seam tests**

```python
def test_confirmation_starts_transaction_but_defers_experience_until_success():
    window = preprocess_window_harness()
    assert window._begin_preprocess_confirmation(report_with("request_confirmation")) is True
    assert window.persisted == []
    window._finalize_preprocess_apply_success()
    assert window.persisted == [("preprocess-c1", "user_confirmed")]


def test_failed_rerun_restores_previous_result_and_config():
    window = preprocess_window_harness()
    window._begin_preprocess_confirmation(report_with("request_confirmation"))
    window._results["dsc"] = {"status": "partial"}
    window._rollback_preprocess_apply_failure()
    assert window.config == {"smooth_window": 11}
    assert window._results["dsc"] is window.original_result


def test_auto_accept_path_registers_existing_commit_and_undoes_without_reapply():
    window = preprocess_window_harness()
    window._register_preprocess_auto_accept(report_with("auto_accept"))
    assert window.apply_calls == []
    assert window._undo_last_preprocess_apply() is True
```

- [ ] **Step 2: Run the seam tests and verify the missing methods fail**

Run: `python -m pytest tests/test_main_window_ai_tuning_mixin.py -q`

Expected: FAIL with missing transaction integration methods.

- [ ] **Step 3: Wire the service without duplicating scientific logic**

Construct `PreprocessTransactionService` with the window's existing config,
result, apply, rerun, and logging callbacks. In the dialog completion path:

- `confirm` + Accepted calls `begin_confirmation`;
- `auto_apply` registers the already-committed report and Accepted invokes undo;
- `auto_apply` with a non-accepted dialog result only records the undo-capable
  state;
- ordinary AI tuning continues through `_apply_best_config` unchanged.

Call `finalize_success` from the existing successful-run callback and
`rollback_failure` from the existing run-error callback. Preserve the existing
`_last_ai_tuned_run`, tab switching, and logging behavior. Never persist an
experience before the rerun success callback.

- [ ] **Step 4: Run the focused GUI/preprocessing matrix**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_main_window_ai_tuning_mixin.py tests/test_preprocess_decision_service.py tests/test_preprocess_transaction_service.py tests/test_preprocess_decision_dialog.py tests/test_orchestrator_preprocess.py tests/test_orchestrator_preprocess_automation.py -q`

Expected: all focused tests pass.

- [ ] **Step 5: Commit the integration slice**

```powershell
git add polynexus/gui/main_window.py polynexus/gui/main_window_ai_tuning_mixin.py polynexus/gui/main_window_run_mixin.py tests/test_main_window_ai_tuning_mixin.py
git commit -m "feat(gui): connect preprocessing confirmation transactions"
```

### Task 5: Final verification and handoff evidence

**Files:**
- Modify: `docs/agent/tasks/2026-07-13-ai-preprocessing-mainline.md`
- Modify: `docs/agent/memory/active-work.md`
- Create: `docs/acceptance/2026-07-13-ai-preprocess-gui-confirmation.md`

- [ ] **Step 1: Run the complete affected test matrix**

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_preprocess_decision_service.py tests/test_preprocess_transaction_service.py tests/test_preprocess_decision_dialog.py tests/test_main_window_ai_tuning_mixin.py tests/test_orchestrator_preprocess.py tests/test_orchestrator_preprocess_automation.py tests/test_preprocess_calibration.py -q
python -m pytest tests/test_orchestrator.py tests/test_analysis_evidence.py tests/test_quality_gate.py -q
python -m compileall -q polynexus/core/preprocess_optimization polynexus/orchestrator_preprocess.py polynexus/gui/preprocess_decision_service.py polynexus/gui/preprocess_transaction_service.py polynexus/gui/main_window.py polynexus/gui/main_window_ai_tuning_mixin.py polynexus/gui/main_window_run_mixin.py
git diff --check
```

Expected: zero failures, compileall exit 0, and no whitespace errors.

- [ ] **Step 2: Review the complete branch diff**

Run: `git diff --stat main@4437bc90...HEAD; git diff --name-only main@4437bc90...HEAD`

Confirm the diff contains only AI preprocessing, GUI confirmation, tests,
task/spec/plan/acceptance evidence, and memory updates. Explicitly reject any
Editor/Export, publication-pack, Unified Tables, or GUI-streamlining file.

- [ ] **Step 3: Record evidence and update task state**

Write exact commands/results to
`docs/acceptance/2026-07-13-ai-preprocess-gui-confirmation.md`; mark only the
completed acceptance items in the task card and update `active-work.md` with
remaining Golden, AI-off, fault, CI, and human-review blockers.

- [ ] **Step 4: Human review checkpoint**

Request review of transaction semantics, audit/experience persistence, and
scientific evidence presentation before any push or merge. Do not promote
non-shadow automation or merge this slice before that review.
