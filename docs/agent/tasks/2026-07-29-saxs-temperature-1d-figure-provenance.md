---
kind: task
status: completed
date: 2026-07-29
title: Record SAXS temperature 1D Figure projection provenance
---

# SAXS temperature 1D Figure projection provenance

## Goal

Make the existing temperature representative-profile and waterfall Figure
projections explain their aligned q/I filtering without changing sequence or
physical evidence semantics.

## Non-goals

- No change to temperature analysis, Guinier sequence evidence, Porod/Kratky,
  invariants, lamellar metrics, quality levels, thresholds, rescue, AI, or
  publication roles.
- No interpolation, padding, value replacement, frame fabrication, or new q
  positivity gate. Existing heatmap interpolation remains unchanged.
- Do not change static or strain providers in this atomic task.
- Do not edit real data, generated outputs, memory files, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_temperature.py`: representative profile
  and waterfall recipe metadata only.
- `tests/test_saxs_temperature_figure_panels.py`: dirty/clean regressions.
- this task's spec and implementation plan.

## Contract

For every emitted temperature 1D profile source, attach a detached mapping
keyed by existing frame index:

```json
{
  "input_pair_count": 4,
  "retained_pair_count": 2,
  "nonfinite_pair_count": 2,
  "nonpositive_intensity_pair_count": 0,
  "status": "partial_invalid"
}
```

Counts use the aligned prefix before the existing stable sort and unique-q
projection. Retention is exactly the existing `finite(q,I) & intensity > 0`
filter. A non-positive q is not counted as invalid because this provider does
not reject it. Fully retained input uses `complete`; all-invalid or
insufficient curves remain omitted.

## Implementation plan

1. Add dirty and clean regression tests for the main representative profile and
   waterfall recipe metadata and verify a real RED.
2. Add one local counter for the existing temperature profile filter and thread
   detached mappings into the evolution and waterfall recipes.
3. Run focused temperature tests, structured verification, a fresh SAXS matrix,
   storage dry-runs, diff/allowlist audit, and an atomic checkpoint.

## Acceptance criteria

- [x] Mixed finite/non-finite temperature q/I pairs record deterministic counts
  with `partial_invalid` status.
- [x] Non-positive intensity pairs are counted separately, without inventing a
  q positivity rule.
- [x] Fully finite positive pairs record `complete` status.
- [x] Main representative and waterfall recipes use the same frame-indexed,
  strict JSON-safe provenance shape.
- [x] Existing temperature sequence, interpolation, roles, and fail-closed
  behavior remain unchanged.
- [x] TDD RED/GREEN, focused/SAXS/structured verification, storage dry-run,
  diff audit, and explicit allowlist checkpoint are recorded.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_1d_provenance_focus'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py -k temperature_profile
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-temperature-1d-figure-provenance.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix must use a PowerShell-expanded `test_saxs_*.py` list and
counts as passing only with a final pytest summary and exit code `0`. The
task-scoped storage commands are dry-run commands; any separate
user-authorized storage maintenance apply is outside this checkpoint.

## Recorded evidence

- TDD RED: the corrected `-k temperature_profile` run selected the two new
  tests and failed `2 failed, 4 deselected` with the expected missing
  `profile_projection_quality` key.
- TDD GREEN: the same selection passed `2 passed, 4 deselected`.
- Temperature Figure provider/regression slice: `15 passed`.
- Structured verifier: quality gate `287 passed`, preprocessing gate `106
  passed`; Ruff, compile, type baseline, and whitespace checks passed.
- Fresh SAXS matrix: `549 passed, 6 warnings in 239.55s`, exit code `0`, using
  a numeric-free dedicated base-temp path so the existing condition-axis
  recovery tests did not interpret a temporary-directory digit as a
  temperature value.
- Storage safety: the fresh report and clean dry-run found `298 artifacts`,
  `9 eligible`, `289 younger than retention`, and `0 eligible bytes`; every
  listed artifact remained `removed=false`. This turn did not run
  `test_storage.py --apply`.
- The final checkpoint allowlist is exactly the five files listed below; the
  pre-existing `docs/agent/memory/current-state.md`, scratch/runtime output,
  and all other parallel files are excluded.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_temperature_figure_panels.py`
- `docs/agent/tasks/2026-07-29-saxs-temperature-1d-figure-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-temperature-1d-figure-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-temperature-1d-figure-provenance.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, and all other parallel/untracked files remain
outside this checkpoint.
