---
kind: task
status: completed
date: 2026-07-29
title: Record SAXS strain 1D Figure projection provenance
---

# SAXS strain 1D Figure projection provenance

## Goal

Make strain 1D Figure recipes explain the aligned q/I projection used by the
existing representative-profile and full-sequence sources, so dirty input is
auditable without changing scientific eligibility or analysis semantics.

## Non-goals

- No change to SAXS analysis, Guinier/Porod/Kratky/invariant/lamellar methods,
  DataQualityReport levels, physical thresholds, AI/rescue, or publication
  roles.
- No change to q-strain heatmap finite-pair handling, common-q interpolation,
  log-intensity clipping, 2D detector/image projection, azimuthal projection,
  orientation, or strain phase paths.
- No interpolation, padding, frame fabrication, value replacement, inference,
  or automatic rescue.
- Do not edit real data, generated outputs, memory files, scratch, or parallel
  workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: detached counts for emitted
  1D profile sources in the main evolution and ordinary/diagnostic sequence
  recipes.
- `tests/test_saxs_figure_evidence_binding.py`: dirty and clean strain 1D
  recipe regressions.
- This task's spec and implementation plan.

## Contract

For every emitted strain 1D profile source, attach a detached mapping keyed by
the existing frame index:

```json
{
  "input_pair_count": 4,
  "retained_pair_count": 1,
  "nonfinite_pair_count": 1,
  "nonpositive_pair_count": 2,
  "status": "partial_invalid"
}
```

Counts use the aligned prefix before the existing profile projection. Retention
is exactly `_profile_values()`'s existing `finite(q, I) & q > 0 & I > 0`
filter, before any later ordering or source serialization. `nonpositive_pair_count`
is the finite rejected remainder, preserving the established static Figure
provenance shape. Fully retained input uses `complete`; omitted or insufficient
curves do not receive fabricated metadata.

## Acceptance criteria

- [x] Mixed non-finite, non-positive-q, and non-positive-intensity pairs record
      deterministic counts with `partial_invalid` status.
- [x] Fully finite positive strain profiles record `complete` status.
- [x] Main `saxs.strain.evolution.1d` and ordinary/diagnostic
      `saxs.strain.sequence.1d` recipes use the same frame-indexed,
      strict-JSON-safe provenance shape.
- [x] q-strain heatmap, 2D detector, orientation, phase, analysis, quality,
      threshold, and publication behavior remain unchanged.
- [x] TDD RED/GREEN, focused/structured/SAXS verification, storage dry-run,
      diff audit, and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add dirty and clean regressions for the strain main evolution and ordinary
   sequence 1D recipe metadata, then verify a real RED.
2. Add one local counter beside `_profile_values()` and thread detached maps
   through the non-detector main and sequence recipes.
3. Run focused strain tests, structured verification, a fresh SAXS matrix,
   storage dry-runs, diff/allowlist audit, and one atomic checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_1d_provenance_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k strain_profile_provenance -vv
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_strain_evidence_filtering.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-strain-1d-figure-provenance.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix must use a PowerShell-expanded `test_saxs_*.py` list,
an external basetemp without condition-axis digits, and counts as passing only
with a final pytest summary and exit code `0`. Never run
`test_storage.py --apply`.

## Verification evidence

- TDD RED: `2 failed, 20 deselected`; both failures were the expected missing
  `profile_projection_quality` key.
- TDD GREEN: `2 passed, 20 deselected`; related strain evidence/filtering slice
  passed `23 tests`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `287 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Fresh SAXS matrix exited `0`: `551 passed, 6 warnings in 192.12s` using the
  neutral external basetemp `D:\SaxsStrainMatrix`.
- Storage report/clean were dry-run only: `301 artifacts`, `29 eligible`,
  `272 younger than retention`, and `499046` eligible bytes. No
  `test_storage.py --apply` command was run and no artifact was removed.
- The final checkpoint is restricted to the five files in the explicit
  allowlist below; `current-state.md`, scratch, and parallel files are
  excluded.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-strain-1d-figure-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-strain-1d-figure-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-strain-1d-figure-provenance.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, `.superpowers/`, historical
pytest/storage directories, and all other untracked or parallel files remain
outside this checkpoint.
