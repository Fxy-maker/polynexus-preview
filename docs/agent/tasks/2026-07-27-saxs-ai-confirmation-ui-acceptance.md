# SAXS AI Confirmation UI Acceptance Task

## Goal

Audit and regression-test the real SAXS AI confirmation path from a
`request_confirmation` report through the enabled review-dialog control into
the existing guarded preprocessing transaction.

## Non-goals

- No new SAXS algorithm, physical threshold, or quality threshold.
- No interpolation, frame fabrication, missing-frame repair, or automatic
  rescue.
- No GUI-side scientific gate or duplicate transaction implementation.
- No publication-role, Figure, Manifest, History, or export behavior change.
- No restarted-GUI or human scientific sign-off claim.

## Affected boundaries

- `polynexus/gui/main_window.py` (`SideTuningReportDialog`)
- `polynexus/gui/main_window_ai_tuning_mixin.py`
- Existing `polynexus/gui/preprocess_transaction_service.py` boundary
- `tests/test_saxs_ai_confirmation_gui_route.py`
- This task card, its design/plan, and durable agent memory

## Acceptance criteria

- [x] The real dialog enables Apply for a SAXS `request_confirmation` report.
- [x] Activating the real Apply button through the MainWindow completion route
      starts exactly one pending SAXS transaction and invokes the existing
      apply/rerun callbacks.
- [x] Rejecting the real dialog leaves the transaction idle and does not apply
      the candidate.
- [x] Existing SAXS physical/quality gates remain the only post-rerun authority;
      this route test does not add a second gate.
- [x] Exact focused and structured verification evidence is recorded.
- [x] One explicit allowlist checkpoint is created without touching parallel
      untracked GUI/scratch files.

## Implementation plan

1. Add an offscreen regression that drives the real SAXS review-dialog Apply
   button through the MainWindow completion route.
2. Run the focused GUI/SAXS matrix and the structured task verifier with an
   external basetemp.
3. Record exact evidence, update durable limitations, and create one explicit
   allowlist checkpoint.

## Design and plan

- Spec: `docs/superpowers/specs/2026-07-27-saxs-ai-confirmation-ui-acceptance-design.md`
- Plan: `docs/superpowers/plans/2026-07-27-saxs-ai-confirmation-ui-acceptance.md`

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests/test_saxs_ai_confirmation_gui_route.py -q
python -m pytest tests/test_saxs_ai_confirmation_gui_route.py tests/test_preprocess_decision_dialog.py tests/test_saxs_ai_confirmed_rerun_safety.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md --changed --types
git diff --check
```

## Verification evidence (2026-07-27)

- TDD RED was not applicable as a production defect: the new acceptance test
  was intentionally designed to expose the missing route evidence, and it
  passed immediately against the existing implementation. No production code
  change was necessary.
- `python -m pytest tests/test_saxs_ai_confirmation_gui_route.py -q`:
  **2 passed in 6.30s**.
- The real `MainWindow` and real `SideTuningReportDialog` were exercised under
  the offscreen Qt platform. The test clicked the actual enabled Apply button,
  observed one `apply_pending` SAXS transaction, and verified the reject path
  performs no apply or rerun.
- `python -m pytest tests/test_saxs_ai_confirmation_gui_route.py tests/test_preprocess_decision_dialog.py tests/test_saxs_ai_confirmed_rerun_safety.py -q`:
  **24 passed in 4.97s**.
- `python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md --changed --types`:
  **exit 0**. Task card and memory checks passed; Ruff and compile passed for
  the changed test set; the current type baseline had no changed files;
  quality gate passed with **283 passed**; preprocessing gate passed with
  **106 passed**; whitespace passed.
- The verifier also inspected the pre-existing untracked
  `tests/_tmp_phase3/test_visual_audit_capture.py` as part of its changed-file
  discovery; it is not part of this task allowlist and was left untouched.
- `git diff --check` is run again after this evidence update before the
  checkpoint is created.

## Known limitations

The automated confirmation route and existing transaction/gate contracts are
covered. Restarted-GUI visual inspection, real-data scientific meaning review,
and human release approval remain open. This task does not authorize automatic
rescue, scientific publication, or release promotion.

## Changed-file allowlist

- `docs/agent/tasks/2026-07-27-saxs-ai-confirmation-ui-acceptance.md`
- `docs/superpowers/specs/2026-07-27-saxs-ai-confirmation-ui-acceptance-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-ai-confirmation-ui-acceptance.md`
- `tests/test_saxs_ai_confirmation_gui_route.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
