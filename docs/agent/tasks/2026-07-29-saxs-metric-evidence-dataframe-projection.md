---
kind: task
status: completed
date: 2026-07-29
title: Project SAXS metric evidence into temperature and strain DataFrames
---

# SAXS metric-evidence DataFrame projection

## Goal

Expose existing frame-level Porod, Kratky, invariant, and lamellar quality
evidence in the temperature and strain DataFrame/CSV view so degraded frames
remain explainable without opening nested JSON.

## Non-goals

- No new analysis algorithm, physical threshold, quality-level rule,
  interpolation, repair, frame fabrication, AI action, rescue, or publication
  change.
- No change to Guinier/Rg columns, `Metric_evidence_levels`, static behavior,
  Figure/Manifest/Export behavior, real data, generated output, memory files,
  or parallel workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: defensive shared
  formatter for existing metric evidence.
- `polynexus/core/saxs_engine/saxs_temperature.py`: temperature row projection.
- `polynexus/core/saxs_engine/saxs_strain.py`: strain row projection.
- `tests/test_saxs_metric_evidence_dataframe.py`: complete, degraded, and
  missing-payload regressions.
- The associated spec and implementation plan.

## Contract

For each point and each fixed metric key (`porod`, `kratky`, `invariant`,
`lamellar`), the row contains `<Metric>_level`, `<Metric>_coverage`, and
`<Metric>_reason_codes`, using labels `Porod`, `Kratky`, `Invariant`, and
`Lamellar`. The values are copied from the existing frame payload. Missing or
malformed payloads produce empty fields; no row or metric evidence is invented.

## Acceptance criteria

- [x] Temperature DataFrames expose all four metric field triplets.
- [x] Strain DataFrames expose all four metric field triplets.
- [x] Complete, diagnostic, unusable, and missing payloads are represented
      deterministically without raising.
- [x] Existing DataFrame values, row counts, and compatibility columns remain
      unchanged; caller-owned nested payloads are not mutated.
- [x] TDD RED/GREEN, structured/SAXS verification, storage dry-run, diff audit,
      and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add temperature, strain, and malformed-payload RED regressions for the
   fixed metric field triplets.
2. Add the shared defensive formatter and attach its detached fields at the
   existing temperature/strain DataFrame row boundaries.
3. Run the focused compatibility slice, task-scoped verifier, exact SAXS
   matrix, storage dry-run, and allowlist audit before checkpointing.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_metric_dataframe_focus'
python -m pytest -q tests/test_saxs_metric_evidence_dataframe.py tests/test_saxs_series_metric_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_strain_evidence_filtering.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-metric-evidence-dataframe-projection.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix must use an external neutral basetemp and is a pass only
with a final pytest summary and exit code `0`. This task never runs
`test_storage.py --apply`.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_temperature.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_metric_evidence_dataframe.py`
- `docs/agent/tasks/2026-07-29-saxs-metric-evidence-dataframe-projection.md`
- `docs/superpowers/specs/2026-07-29-saxs-metric-evidence-dataframe-projection-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-metric-evidence-dataframe-projection.md`

## Verification evidence

- TDD RED: `3 failed`, each due to the expected missing DataFrame projection
  columns.
- TDD GREEN: `3 passed`; related series/temperature/strain compatibility slice:
  `23 passed`.
- Task-scoped verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `287 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Fresh PowerShell-expanded SAXS matrix exited `0`: `556 passed, 6 warnings`
  in `204.02s`. Warnings are the existing Arial CJK glyph and missing EDF
  geometry-header warnings.
- Storage report and clean were dry-run only: `14` artifacts,
  `13,935,155,317` bytes total, `6` eligible entries but `0` eligible bytes;
  no `--apply` command or removal was performed.
- `git diff --check` exited `0` as part of the structured verification.

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, scratch outputs, and all other untracked or
parallel files remain outside this checkpoint.
