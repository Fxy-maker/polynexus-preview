---
task_id: 2026-07-30-saxs-series-metric-evidence-projection
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Preserve SAXS series metric evidence in Figure and Export projections
---

# SAXS series metric evidence projection

## Goal

Preserve the existing series metric source-index integrity facts across the
Figure/Manifest and Export evidence boundaries.

## Non-goals

- No changes to metric calculations, q/I values, quality levels, thresholds,
  physical gates, rescue, AI, or publication roles.
- No sorting, interpolation, frame creation, source-index repair, or new
  source-index validation.
- No changes to generated outputs, real datasets, test storage, GUI behavior,
  or unrelated pre-existing worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`: explicit common evidence
  projection allowlist.
- `tests/test_saxs_series_metric_evidence_projection.py`: Figure, Manifest,
  and Export regression coverage.
- Existing FigurePipeline and `quality_evidence.json` contracts, read-only.

## Implementation plan

1. Add RED tests for Figure, Manifest, and Export transport of the existing
   source-index fields.
2. Extend the Figure evidence allowlist with only those three fields.
3. Run focused consumers, task verification, SAXS verification, storage
   dry-run, and diff checks, then create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Series metric Figure provenance retains duplicate and invalid source
      position lists and the reordered flag.
- [x] Manifest persistence retains the same detached JSON-safe projection.
- [x] Export retains the same fields without changing its current payload
      shape or serializer.
- [x] Unknown fields remain filtered by the explicit Figure allowlist.
- [x] Focused RED/GREEN, task verification, SAXS matrix, storage dry-run,
      diff check, and allowlist checkpoint are recorded.

## Verification

```powershell
python -m pytest -q tests/test_saxs_series_metric_evidence_projection.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_evidence_projection_red
python -m pytest -q tests/test_saxs_series_metric_evidence_projection.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_export_bundle.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_evidence_projection_green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-series-metric-evidence-projection.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The exact SAXS matrix requires a complete pytest summary and exit code `0`.
Full/boundary verification is only reported when it has both a pytest summary
and a boundary result. `test_storage.py --apply` is not authorized for this
task.

## Evidence

- TDD RED: `2 failed, 1 passed, 2 warnings`; the two Figure projection tests
  failed with missing `duplicate_source_index_indices`, while Export remained
  green. The first run using a D-root basetemp also hit an environment
  permission error before pytest setup; the valid RED used a workspace
  basetemp.
- Focused GREEN: `47 passed, 1 warning`.
- Consumer matrix: `71 passed, 1 warning`.
- Fresh SAXS matrix: `608 passed, 8 warnings in 394.32s`, exit code `0`.
- Task verifier: task-card, memory, Ruff, and compile checks passed; the
  changed type baseline had no matching baseline files. Its quality gate was
  `288 passed, 2 failed, 3 warnings`, exit code `1`, due to the pre-existing
  locale expectations in `tests/test_history_table_service.py` (`Scientific
  review` expected while the current locale emits `科学复核`).
- Storage report/clean were dry-run only: `56` artifacts, `6` eligible,
  `eligible_bytes=13390550`, and `removed=0`. No `--apply` was run.
- `git diff --check` passed for the task diff before checkpoint review.

The full-software full/boundary gate is not claimed for this task. The SAXS
matrix above is the fresh domain regression evidence.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_series_metric_evidence_projection.py`
- `docs/superpowers/specs/2026-07-30-saxs-series-metric-evidence-projection-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-series-metric-evidence-projection.md`
- `docs/agent/tasks/2026-07-30-saxs-series-metric-evidence-projection.md`
- `docs/acceptance/2026-07-30-saxs-series-metric-evidence-projection.md`
- `docs/agent/memory/active-work.md`
