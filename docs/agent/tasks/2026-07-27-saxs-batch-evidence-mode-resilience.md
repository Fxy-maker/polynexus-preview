# SAXS aligned batch evidence mode resilience

## Goal

Preserve per-frame SAXS quality evidence when `get_parameters()` is asked to
serialize aligned `_batch_results` and no dedicated temperature/strain series
result is available. The transport decision must not silently drop evidence
because a stale or inconsistent `cfg.experiment_type` label says that the
batch is non-static.

## Non-goals

- Do not change SAXS scientific thresholds, frame alignment, or evidence
  levels.
- Do not reinterpret a missing temperature/strain series as a scientific
  success.
- Do not change dedicated temperature or strain result branches.

## Affected boundaries

- SAXS engine `get_parameters()` batch serialization.
- Shared SAXS frame-evidence copy helper contract.
- SAXS batch/2D/export regression coverage and task verification.

## Implementation plan

1. Reproduce the mode-label/evidence-loss boundary with a focused regression.
2. Make generic aligned-batch transport depend on the available series result,
   not only on the mode label.
3. Run the SAXS neighboring matrices, structured verifier, and full suite.
4. Record the checkpoint and remaining overall release gates.

## Acceptance criteria

- [x] A regression fails on the old mode-gated branch when a generic aligned
  batch carries a non-static mode label.
- [x] Generic aligned batches copy existing frame evidence without reordering
  rows or fabricating evidence for missing frames.
- [x] Existing SAXS batch, 2D evidence, and export matrices remain green.
- [x] Full repository verifier rerun for this checkpoint.

## Change boundary

- `polynexus/core/saxs.py`
- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs_export_bundle.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `tests/test_saxs_export_bundle.py`
- This task card and its acceptance evidence.

## Verification

```text
python -m pytest -q tests/test_saxs_batch_parameters.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_export_bundle.py
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-batch-evidence-mode-resilience.md --changed --types
```

The full suite previously exposed the motivating failure after 2309 passing
tests: `test_saxs_static_batch_get_parameters_preserves_aligned_frame_evidence`
raised `KeyError: metric_evidence`. The focused reproduction was made
deterministic by setting a non-static mode label while leaving the dedicated
series result absent; it failed before the implementation change and passed
after it.

The additional scope regression first failed in all three consumers: parameters
and Export emitted `static_batch`, while Workbench recommended using a series
trend. The corrected contract uses `aligned_batch`, labels the Workbench as
aligned batch quality, and keeps the missing-series state Diagnostic.

Checkpoint verification:

- Fresh focused matrix: `37 passed` for batch parameters, 2D evidence
  propagation, and Export.
- Fresh task-scoped verifier with `PYTEST_ADDOPTS=--basetemp=C:\Temp\PolyNexus-aligned-batch-verify`:
  quality `282`, preprocessing `106`; task/memory, Ruff, compile/type baseline,
  and whitespace checks passed.
- The default verifier path was also attempted and recorded `229 passed, 53
  setup errors` because the pre-existing repository `.pytest_tmp` could not be
  removed (`WinError 5`); no changed-file assertion failed. A separate
  independent full/boundary rerun reported `2707 passed, 10 warnings`, quality
  `282`, preprocessing `106`, and a passing boundary audit.

## Known limitations

This task does not close real-data scientific review, restarted-GUI visual
walkthroughs, AI model calibration, or final release approval for the overall
PolyNexus goal.
