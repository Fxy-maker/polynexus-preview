# AI Preprocessing GUI Confirmation Acceptance Evidence

## Scope

This checkpoint covers the AI preprocessing GUI decision projection and
transactional confirmation/apply/rollback/undo path on
`codex/ai-preprocess-mainline-v2`, based on `main@4437bc90`.

Editor/Export, Unified Tables, publication packs, and GUI streamlining were not
included.

## Implementation commits

- `8d0ed0f` — preprocessing decision view model.
- `58a04ce` — transactional apply/rollback/undo service.
- `5376811` — report-dialog evidence and action gating.
- `b96bedd` — GUI confirmation, auto-accept undo, and rerun lifecycle wiring.
- `f5799e9` — callback keyword compatibility fix.

Earlier uncommitted AI preprocessing foundation, adapter, calibration, and
orchestration work remains in the same isolated worktree and is tracked by
`docs/agent/tasks/2026-07-13-ai-preprocessing-mainline.md`.

## Verification

```text
preprocessing/calibration/GUI matrix: 285 passed
broader orchestration/analysis matrix: 226 passed, 1 skipped
quality gate: 280 passed
compileall: passed
git diff --check: passed
```

Commands run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_preprocess_optimization_contracts.py tests/test_preprocess_optimization_policy.py tests/test_preprocess_optimization_candidates.py tests/test_preprocess_optimization_decision.py tests/test_preprocess_optimization_storage.py tests/test_preprocess_peak_metrics.py tests/test_preprocess_phase1_adapters.py tests/test_preprocess_saxs_adapter.py tests/test_preprocess_nmr_adapter.py tests/test_orchestrator_preprocess.py tests/test_orchestrator_preprocess_automation.py tests/test_preprocess_calibration.py tests/test_preprocess_decision_service.py tests/test_preprocess_transaction_service.py tests/test_preprocess_decision_dialog.py tests/test_main_window_ai_tuning_mixin.py tests/test_main_window_persistence.py -q
python -m pytest tests/test_orchestrator.py tests/test_analysis_evidence.py tests/test_quality_gate.py -q
python scripts/quality_gate.py
python -m compileall -q polynexus/core/preprocess_optimization polynexus/orchestrator_preprocess.py polynexus/orchestrator.py polynexus/gui/preprocess_decision_service.py polynexus/gui/preprocess_transaction_service.py polynexus/gui/main_window.py polynexus/gui/main_window_ai_tuning_mixin.py polynexus/gui/main_window_run_mixin.py
git diff --check
```

## Remaining gates

- Golden/synthetic evaluation, fault-injection, and AI-off compatibility now
  pass in the focused gates.
- The local `python scripts/quality_gate.py --all-tests` run exceeded 304
  seconds without returning a failing test; it is not counted as passed.
- CI has not yet been run for this branch.
- Human review of transaction, audit, experience persistence, and scientific
  evidence semantics is still required before push/merge.
- Automation profiles remain shadow-only by policy.
