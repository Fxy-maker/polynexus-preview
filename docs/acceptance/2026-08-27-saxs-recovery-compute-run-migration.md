# SAXS recovery ComputeRun migration acceptance — 2026-08-27

## Scope

The real-source SAXS `rerun_condition_recovery` candidate now uses the shared
`ComputeRunService` producer. The baseline canonical template is passed into
the service, so the recovery does not convert the same source a second time.
Missing or synthetic test paths retain the established provider-only fallback.

## Evidence

- `tests/test_saxs_orchestrator_compute_run.py` covers real-source service
  invocation and canonical-template reuse, synthetic provider fallback, and
  shared-service failure with baseline-run preservation.
- `polynexus/orchestrator_session.py` returns a candidate run only after the
  service completes and commits it to `_compute_run` only after final candidate
  selection and successful engine replay. The selected recovery context is
  merged again after baseline restore so the final engine state matches the
  accepted run.

## Verification

```text
python -m pytest -q tests/test_saxs_orchestrator_compute_run.py
3 passed

python -m pytest -q tests/test_saxs_orchestrator_compute_run.py tests/test_saxs_orchestrator_loop.py tests/test_orchestrator_compute_run.py tests/test_compute_service.py tests/test_compute_models.py
84 passed, 4 skipped

python scripts/verify.py --task docs/agent/tasks/2026-08-27-saxs-recovery-compute-run-migration.md --changed --types
passed (quality/preprocessing/type/compile/task gates)

git diff --check
passed
```

## Boundary and limitations

This task does not remove legacy provider readers or alter SAXS quality gates,
condition precedence, candidate ranking, or scientific algorithms. The broader
repository still has documented historical GUI/chart/SAXS failures, so this
checkpoint is implementation-complete and review-required, not a release-green
claim. Architecture and scientific acceptance remain human review items before
merge.

## Checkpoint

The explicit allowlist is the task card's changed-file list. No push, merge,
deployment, raw-data modification, or data deletion was performed.
