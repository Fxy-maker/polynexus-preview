---
kind: task
status: completed
date: 2026-07-29
title: Record SAXS strain auxiliary 1D Figure provenance
---

# SAXS strain auxiliary 1D Figure provenance

## Goal

Expose deterministic projection provenance for the strain low-q diagnostic and
Correlation/IDF trace Figures, completing the audit boundary for existing
auxiliary 1D outputs.

## Non-goals

- No change to SAXS analysis, Guinier/Porod/Kratky/invariant/lamellar methods,
  DataQualityReport levels, physical thresholds, AI/rescue, or publication
  roles.
- No change to q-strain heatmap interpolation/clipping, detector/azimuthal
  projection, orientation, phase, or any static/temperature provider.
- No interpolation, padding, frame fabrication, replacement, inference, or
  automatic rescue.
- Do not edit real data, generated outputs, memory files, scratch, or parallel
  workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: detached maps for the existing
  low-q, Correlation, and IDF Figure recipes.
- `tests/test_saxs_figure_evidence_binding.py`: dirty and clean regressions.
- This task's spec and implementation plan.

## Contract

The low-q recipe uses the existing profile shape, keyed by emitted frame index:

```json
{
  "input_pair_count": 4,
  "retained_pair_count": 3,
  "nonfinite_pair_count": 1,
  "nonpositive_pair_count": 0,
  "status": "partial_invalid"
}
```

Correlation and IDF recipes use finite aligned trace pairs:

```json
{
  "input_pair_count": 4,
  "retained_pair_count": 2,
  "nonfinite_pair_count": 2,
  "status": "partial_nonfinite"
}
```

Counts use the aligned prefix before the existing finite projection. Only
emitted sources receive entries; omitted or insufficient traces receive no
fabricated metadata. All counts are Python integers and recipes remain strict
JSON-safe.

## Acceptance criteria

- [x] Low-q recipes record deterministic profile counts for dirty and clean
      emitted frames.
- [x] Correlation and IDF recipes record finite-pair counts for dirty and clean
      emitted traces.
- [x] Existing source values, omission rules, roles, and scientific analysis
      behavior remain unchanged.
- [x] TDD RED/GREEN, focused/structured/SAXS verification, storage dry-run,
      diff audit, and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add dirty and clean regressions for low-q, Correlation, and IDF recipes and
   verify the expected RED.
2. Add local detached counters and attach them only to the three existing
   auxiliary 1D recipes.
3. Run focused tests, structured verification, a fresh SAXS matrix, storage
   dry-runs, diff/allowlist audit, and one atomic checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_auxiliary_provenance_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k strain_auxiliary_provenance -vv
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_strain_evidence_filtering.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-strain-auxiliary-1d-provenance.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix must use a PowerShell-expanded `test_saxs_*.py` list,
an external basetemp without condition-axis digits, and a final pytest summary
with exit code `0`. Never run `test_storage.py --apply`.

## Verification evidence

- TDD RED: `2 failed, 22 deselected`; failures were the expected missing
  `profile_projection_quality` field.
- TDD GREEN: `2 passed, 22 deselected`; related strain evidence/filtering slice
  passed `25 tests`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `287 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Fresh SAXS matrix exited `0`: `553 passed, 6 warnings in 208.60s` using the
  neutral external basetemp `D:\SaxsAuxiliaryMatrix`.
- Storage report/clean were dry-run only: `278 artifacts`, `6 eligible`,
  `272 younger than retention`, and `0` eligible bytes. No `--apply` command
  was run and no artifact was removed.
- The final checkpoint is restricted to the five files in the explicit
  allowlist below; `current-state.md`, scratch, and parallel files are
  excluded.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-strain-auxiliary-1d-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-strain-auxiliary-1d-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-strain-auxiliary-1d-provenance.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, `.superpowers/`, historical
pytest/storage directories, and all other untracked or parallel files remain
outside this checkpoint.
