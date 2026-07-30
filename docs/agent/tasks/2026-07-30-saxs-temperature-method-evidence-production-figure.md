---
task_id: 2026-07-30-saxs-temperature-method-evidence-production-figure
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Bind temperature method evidence to the production Figure provider
---

# SAXS temperature method evidence production Figure

## Goal

Make the existing temperature 1D Porod, Kratky, invariant, and lamellar
evidence visible through the production Figure path.

## Non-goals

- No changes to method calculations, q/I data, quality levels, thresholds,
  physical gates, rescue, AI, or publication roles.
- No positional source guessing, interpolation, frame fabrication, source
  repair, or time-axis behavior change.
- No GUI event logic, Workbench label changes, real datasets, generated
  outputs, or test-storage deletion.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_temperature.py`: production temperature
  Figure projection.
- `tests/test_saxs_temperature_figure_panels.py`: production Figure contract
  and fail-closed source binding regression coverage.
- Existing Figure evidence attachment, Manifest, and Export contracts,
  read-only.

## Implementation plan

1. Add RED tests for production method evidence, missing values, source-index
   order, and duplicate mapping fail-closed behavior.
2. Add a diagnostic-only production Figure that consumes only existing
   `TempSeriesResult.temp_points` evidence.
3. Run focused GREEN, structured verification, exact SAXS verification,
   storage dry-run, diff checks, and one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Production temperature Figure emits the four supported method evidence
      channels when existing evidence is present.
- [x] Missing values remain explicit; no interpolation or reclassification is
      introduced.
- [x] Duplicate/invalid source mappings remain fail-closed.
- [x] Existing evolution Main Figure and time-axis behavior remain unchanged.
- [x] Verification evidence and explicit checkpoint are recorded.

## Verification

The structured check is `python scripts/verify.py --task
docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-production-figure.md
--changed --types`.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_panels.py -k "method_evidence" -o addopts=
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_evidence_filtering.py tests/test_saxs_figure_evidence_binding.py -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-production-figure.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix requires a complete pytest summary and exit code `0`.
`test_storage.py --apply` is not authorized for this task.

## Verification evidence

- TDD RED: `2 failed, 8 deselected`.
- Focused GREEN: `2 passed, 8 deselected`.
- Production temperature/evidence/provenance matrix: `48 passed`.
- Production matrix including the portable provider regression: `66 passed`.
- Exact SAXS matrix: `653 passed, 6 warnings` in `541.39s`, exit code `0`.
- Structured verifier passed quality `296`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace checks.
- Storage report/clean remained non-destructive: `71` artifacts,
  `16,473,416,178` bytes, `eligible_bytes=0`, no emergency pressure, and
  `removed=0`. No `test_storage.py --apply` was run.
- `git diff --check` passed.
- Explicit allowlist checkpoint: `929da91`; no push or merge was performed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_temperature_figure_panels.py`
- `docs/superpowers/specs/2026-07-30-saxs-temperature-method-evidence-production-figure-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-temperature-method-evidence-production-figure.md`
- `docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-production-figure.md`
- `docs/acceptance/2026-07-30-saxs-temperature-method-evidence-production-figure.md`
- `docs/agent/memory/active-work.md`

## Current limitations

This slice covers the production temperature-axis Figure provider only. The
portable provider, Workbench presentation, Manifest/Export transport, static/
strain/2D consumers, human scientific review, and full release gates remain
separate boundaries.
