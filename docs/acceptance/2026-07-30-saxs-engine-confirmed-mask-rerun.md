# SAXS Engine Confirmed Mask Rerun Acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
Status: automated acceptance complete; explicit allowlist checkpoint created

## Delivered behavior

The existing confirmed detector-mask candidate can now be supplied to
`SAXSEngine.run_pipeline()` and forwarded by `AnalysisWorker`. The candidate
is transient and reaches the existing `preprocess_pipeline()` contract only
for a single static 2D image. It is not applied to 1D profiles, directory or
temperature/strain sequence routes, or `skip_to="plot"` runs.

The existing candidate validation, copied-mask application, detector quality
report, data-quality gates, physical gates, and publication gates remain the
authorities. No inference, interpolation, morphology, AI call, new threshold,
automatic rescue, or publication promotion was introduced.

## Evidence

- RED: `4 failed`; failures were the expected missing
  `mask_edit_candidate` engine and worker boundaries.
- GREEN: `6 passed in 1.04s`, including successful and failed-run cleanup,
  plot-only no-op, 1D no-op, sequence no-op, and worker forwarding.
- Task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md --changed --types`
  returned exit code `0`; quality `292 passed`, preprocessing `106 passed`,
  Ruff, compile, memory/task, type baseline, and whitespace checks passed.
- Exact SAXS matrix:
  `642 passed, 6 warnings in 559.53s (0:09:19)`, exit code `0`.
- Storage report:
  `54` artifacts, `eligible_bytes=0`, emergency pressure `false`, and no
  cleanup failures.
- Storage cleanup was dry-run only; no `--apply` was executed, and no test
  directory was deleted or migrated.
- `git diff --check` returned exit code `0`.

The first matrix attempt reached the 120-second tool timeout without a final
pytest summary and is not counted as evidence. The independent retry above is
authoritative.

## Boundary and follow-up

This slice does not add a GUI mask editor or sequence-wide per-frame mask
transactions. Full/boundary release verification, scientific review, and
restarted-GUI approval remain open. The explicit allowlist checkpoint commit
for this task contains only the files listed below; its hash is kept in Git
history rather than duplicated in this mutable evidence file.

## Files in the checkpoint allowlist

- `polynexus/core/saxs.py`
- `polynexus/gui/main_window_workers.py`
- `tests/test_saxs_engine_confirmed_mask_rerun.py`
- `docs/superpowers/specs/2026-07-30-saxs-engine-confirmed-mask-rerun-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- `docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- `docs/acceptance/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- `docs/agent/memory/active-work.md`

Parallel edits in `current-state.md`, release-decision documents, GUI/editor
files, `.superpowers/`, and historical test-output directories are outside
this checkpoint and remain untouched.
