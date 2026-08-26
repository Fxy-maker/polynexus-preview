---
kind: task
status: implementation_complete_review_required
date: 2026-08-27
title: Route SAXS condition recovery through shared ComputeRun
---

# Route SAXS condition recovery through shared ComputeRun

## Goal

Move the real-source `rerun_condition_recovery` candidate path onto the
existing `ComputeRunService` producer while retaining the provider-only
compatibility path used by missing or synthetic test inputs.

## Non-goals

- Do not delete Batch, GUI persistence, Codex/Agent workflow, DSC multi-program,
  or legacy result readers.
- Do not change SAXS condition precedence, quality gates, candidate ranking, or
  provider scientific algorithms.
- Do not reparse or modify raw data, and do not persist a second private result
  representation.

## Shared objects and boundaries

- Producer: `polynexus.core.compute.ComputeRunService`.
- Consumer: `polynexus.orchestrator_session._execute_candidate_trial` for the
  SAXS `rerun_condition_recovery` action.
- Compatibility boundary: missing/synthetic paths in
  `polynexus/orchestrator_run_bootstrap.py` and tests remain provider-only.
- Report boundary: `ParameterOrchestrator._final_report` continues exposing the
  accepted shared run projection.

## Affected boundaries

- `polynexus/orchestrator_session.py`: SAXS candidate execution and shared-run
  handoff.
- `tests/test_saxs_orchestrator_compute_run.py`: real-source, fallback, and
  failure regressions.
- `docs/agent/` and `docs/acceptance/`: durable task state and evidence.

## Implementation plan

1. Add a failing real-source regression that spies on the shared service and a
   synthetic fallback regression that guards the compatibility boundary.
2. Route real-source recovery through `ComputeRunService` with the baseline
   canonical template; return service failures without provider fallback.
3. Hold candidate runs until final candidate selection and successful replay;
   preserve the baseline run on rollback.
4. Run the focused matrix and structured verifier, record evidence, and create
   an explicit allowlisted local checkpoint.

## Acceptance criteria

- [x] A real existing SAXS source calls `ComputeRunService.run_direct` for
  condition recovery and passes the baseline canonical template through
  unchanged.
- [x] The recovery candidate updates `_compute_run` only when the candidate is
  accepted; rejected/rolled-back candidates leave the previous shared run in
  place.
- [x] Missing or synthetic paths retain the existing direct provider fallback.
- [x] Recovery failures expose the shared service reason and do not call the
  provider a second time outside the service.
- [x] Focused regression tests show RED before implementation and GREEN after.
- [x] Structured verification and an explicit allowlisted checkpoint are
  recorded; full historical GUI/SAXS failures remain documented rather than
  silently fixed here.

## Verification

```powershell
python -m pytest -q tests/test_saxs_orchestrator_compute_run.py tests/test_saxs_orchestrator_loop.py -k recovery
python scripts/verify.py --task docs/agent/tasks/2026-08-27-saxs-recovery-compute-run-migration.md --changed --types
git diff --check
```

## Verification evidence

- TDD RED: the real-source test initially observed zero shared-service calls;
  the synthetic fallback test remained green.
- Focused migration/orchestrator/ComputeRun matrix: `83 passed, 4 skipped`.
- Focused recovery subset: `3 passed`.
- Structured verifier and allowlisted checkpoint are recorded in the
  acceptance note below.

## Changed-file allowlist

- `polynexus/orchestrator_session.py`
- `tests/test_saxs_orchestrator_compute_run.py`
- `docs/agent/tasks/2026-08-27-saxs-recovery-compute-run-migration.md`
- `docs/superpowers/specs/2026-08-27-saxs-recovery-compute-run-migration-design.md`
- `docs/superpowers/plans/2026-08-27-saxs-recovery-compute-run-migration.md`
- `docs/acceptance/2026-08-27-saxs-recovery-compute-run-migration.md`
- `docs/agent/memory/active-work.md`
