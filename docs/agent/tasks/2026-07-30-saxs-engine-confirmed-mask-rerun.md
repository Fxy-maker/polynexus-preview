---
task_id: 2026-07-30-saxs-engine-confirmed-mask-rerun
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Thread confirmed SAXS mask candidates through the engine rerun path
---

# SAXS engine confirmed mask rerun

## Goal

Make the existing confirmed detector-mask candidate usable by the normal
`SAXSEngine` and `AnalysisWorker` path for a single static 2D image, without
changing any scientific gate or sequence semantics.

## Non-goals

- No GUI mask editor in this slice.
- No candidate application to directories, temperature sequences, strain
  sequences, or 1D profiles.
- No automatic mask inference, interpolation, morphology, AI call, new
  threshold, automatic rescue, or publication promotion.
- No edits to real datasets, generated outputs, `current-state.md`, or
  parallel scratch files.

## Affected boundaries

- `polynexus/core/saxs.py`: transient candidate transport into preprocessing.
- `polynexus/gui/main_window_workers.py`: optional worker keyword forwarding.
- `tests/test_saxs_engine_confirmed_mask_rerun.py`: engine/worker boundary tests.

## Implementation plan

1. Write RED tests for engine forwarding, cleanup, plot-only no-op, and worker
   forwarding.
2. Add transient engine state and pass the candidate through the existing
   preprocessing boundary; add optional worker forwarding.
3. Run focused GREEN, task verification, the exact SAXS matrix, storage
   report/dry-run, diff checks, and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] A candidate supplied to a full static image run reaches
      `preprocess_pipeline()` exactly for that invocation.
- [x] Candidate state is cleared after both successful and failed runs.
- [x] `skip_to="plot"`, 1D input, and sequence routes do not apply a candidate.
- [x] Worker forwarding is optional and does not alter non-SAXS engine calls.
- [x] Existing detector quality, data-quality, physical, and publication gates
      remain authoritative.

## Verification

```powershell
python -m pytest -q tests/test_saxs_engine_confirmed_mask_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-engine-mask-rerun-red
python -m pytest -q tests/test_saxs_engine_confirmed_mask_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-engine-mask-rerun-green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The exact SAXS matrix must have a complete summary and exit code `0` before
checkpointing. Full/boundary release status is not claimed by this slice.

## Current evidence

- Focused RED: `4 failed` with the expected missing engine/worker keyword
  boundaries.
- Focused GREEN: `6 passed`.
- Task verifier: exit code `0`; quality `292`, preprocessing `106`; Ruff,
  compile, memory/task, type baseline, and whitespace checks passed.
- Exact SAXS matrix: `642 passed, 6 warnings` in `559.53s`, exit code `0`.
- Storage report: `54` artifacts, `eligible_bytes=0`, no emergency.
- Storage clean: dry-run only; no directory was removed or migrated.
- First SAXS matrix attempt hit the 120-second tool timeout without a pytest
  summary and is not counted as evidence; the retry above is authoritative.

## Explicit changed-file allowlist

- `polynexus/core/saxs.py`
- `polynexus/gui/main_window_workers.py`
- `tests/test_saxs_engine_confirmed_mask_rerun.py`
- `docs/superpowers/specs/2026-07-30-saxs-engine-confirmed-mask-rerun-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- `docs/agent/tasks/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- `docs/acceptance/2026-07-30-saxs-engine-confirmed-mask-rerun.md`
- `docs/agent/memory/active-work.md`
