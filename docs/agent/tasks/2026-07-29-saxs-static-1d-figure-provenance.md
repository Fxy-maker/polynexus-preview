---
kind: task
status: completed
date: 2026-07-29
title: Record SAXS static 1D Figure projection provenance
---

# SAXS static 1D Figure projection provenance

## Goal

Make the existing static q/I Figure projection explain which aligned pairs
were available, retained, or discarded, without changing analysis or Figure
eligibility.

## Non-goals

- No change to SAXS algorithms, Guinier/Porod/Kratky/invariant/lamellar
  evidence, physical thresholds, quality levels, rescue, AI, or publication
  roles.
- No interpolation, padding, sorting, value replacement, or frame fabrication.
- Do not change temperature/strain providers in this atomic task; they will
  reuse the reviewed schema in separate slices.
- Do not edit real data, generated outputs, memory files, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_static.py`: static sample/comparison
  profile recipe only.
- `tests/test_saxs_figure_evidence_binding.py`: dirty/clean static regressions.
- this task's spec and implementation plan.

## Contract

For every static profile source that is actually emitted, attach a detached
`profile_projection_quality` mapping keyed by existing frame index:

```json
{
  "input_pair_count": 4,
  "retained_pair_count": 2,
  "nonfinite_pair_count": 2,
  "nonpositive_pair_count": 0,
  "status": "partial_invalid"
}
```

Counts use the already aligned prefix (`min(q.size, intensity.size)`).
Retention uses the existing Figure filter `finite & q > 0 & intensity > 0`;
this task adds no new scientific rule. Fully retained pairs use `complete`.
All-invalid or insufficient profiles remain omitted as before and do not get
fabricated Figure sources.

## Implementation plan

1. Add mixed-invalid and clean static profile recipe regressions and verify the
   missing provenance field produces a real RED.
2. Add a static-only counter for the existing aligned q/I projection and thread
   its detached mapping into sample/comparison recipes.
3. Run focused static tests, the structured verifier, a fresh SAXS matrix, and
   storage report/clean dry-runs; audit the allowlist and checkpoint.

## Acceptance criteria

- [x] Mixed finite/non-finite q/I pairs record deterministic counts and
  `partial_invalid` status.
- [x] Non-positive finite q/I pairs are counted separately from non-finite
  pairs.
- [x] Fully valid pairs record `complete` status.
- [x] Counts are frame-index keyed, detached, and strict JSON-safe.
- [x] Existing static Figure roles and fail-closed minimum-point behavior are
  unchanged.
- [x] TDD RED/GREEN, focused/static/SAXS verification, structured verifier,
  storage dry-run, diff audit, and explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: the two new regressions failed with `KeyError:
  'profile_projection_quality'`; an initial selector typo produced `0
  selected` and was rerun with the correct `-k static_profile` selector.
- GREEN provenance regressions: `2 passed, 18 deselected`.
- Static Figure/publication gate matrix: `24 passed`.
- Structured verifier: task/memory checks valid; quality `287 passed`,
  preprocessing `106 passed`; compile/Ruff/type baseline/whitespace passed.
- Fresh SAXS matrix: `547 passed, 6 warnings` in `202.93s`, exit code `0`.
- Storage report and clean: `350` artifacts, `57` eligible, `9` referenced by
  a running process, `284` younger than retention; `mode=dry-run` and
  `removed_count=0`. No `--apply` command ran.
- `git diff --check` and explicit allowlist audit are required immediately
  before the checkpoint; parallel files remain outside it.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_1d_provenance_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k static_profile
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_static_publication_gate.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-static-1d-figure-provenance.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix must use a PowerShell-expanded `test_saxs_*.py` list and
counts as passing only with a final pytest summary and exit code `0`. Never run
`test_storage.py --apply`.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_static.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-static-1d-figure-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-static-1d-figure-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-static-1d-figure-provenance.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, and all other parallel/untracked files remain
outside this checkpoint.
