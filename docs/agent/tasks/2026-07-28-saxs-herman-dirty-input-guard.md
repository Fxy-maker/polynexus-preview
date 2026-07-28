---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS Herman orientation helper against dirty sector profiles
---

# SAXS Herman dirty-input guard

## Goal

Make the public `herman_orientation_factor()` helper tolerate recoverable
sector angle/intensity inputs and return its existing diagnostic NaN payload
instead of raising on malformed observations.

## Decision and boundaries

The helper will perform elementwise numeric coercion, pairwise length
alignment, finite-pair filtering, and stable angle sorting in a detached copy.
Finite negative intensities are retained: this helper has no established
positive-intensity gate and they may represent background-subtracted values.
No new evidence level or physical threshold is introduced.

## Non-goals

- Do not change the Herman formula, angular windows, integration weighting, or
  existing minimum-point behavior.
- Do not interpolate, pad, average, clip, or replace observations.
- Do not promote orientation evidence, change detector provenance, rescue, AI,
  Figure/Manifest/Export behavior, or publication roles.
- Do not edit real datasets, generated outputs, GUI code, or parallel scratch.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`: detached sector profile guard.
- `tests/test_saxs_herman_dirty_input.py`: dirty, mismatched, empty, negative,
  clean-reference, and immutability regressions.
- this task card, design/spec, implementation plan, acceptance note, and
  `docs/agent/memory/active-work.md`.

## Acceptance criteria

- [x] String and non-finite angle/intensity observations no longer raise and do
  not enter the integration.
- [x] Unsorted finite angle/intensity pairs are stably ordered without changing
  the clean numerical result.
- [x] Mismatched and wholly invalid inputs return the existing dictionary shape
  with NaN metrics rather than indexing errors.
- [x] Finite negative intensities are not silently discarded by a new gate.
- [x] Caller-owned arrays remain unchanged.
- [x] TDD RED/GREEN, exact SAXS matrix, structured verifier, diff check, and an
  explicit allowlist checkpoint are recorded with real output.

## Implementation plan

1. Add focused dirty, mismatched, empty, negative-intensity, clean-reference,
   and immutability regressions; run RED before changing production code.
2. Reuse the existing elementwise numeric coercion helper at the Herman
   boundary, filter only non-finite pairs, and stably sort angles while keeping
   the current calculation body unchanged.
3. Run focused GREEN, the related strain/orientation matrix, exact SAXS matrix,
   task verifier, and diff check with external basetemps.
4. Record exact evidence, review the explicit allowlist, and create one local
   automatic checkpoint.

## Verification

The focused tests, exact SAXS matrix, and task-scoped verifier below must
produce readable summaries and exit code 0. A timeout or historical process is
not evidence for this task.

### Verification commands

```powershell
python -m pytest -q tests/test_saxs_herman_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_herman_dirty_green
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_herman_dirty_matrix
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_herman_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-herman-dirty-input-guard.md --changed --types
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

## Verification record

- TDD RED: `2 failed, 1 passed in 0.49s`; failures were the expected
  malformed-angle/object-array arithmetic errors. The existing empty/short
  path passed.
- Focused GREEN: `3 passed in 0.18s`, exit code `0`.
- Related strain/orientation matrix: `36 passed in 0.82s`, exit code `0`.
- Exact SAXS matrix: `494 passed, 6 warnings in 259.20s`, exit code `0`, using
  `D:\PolyNexus_saxs_herman_dirty_matrix`. Warnings are the existing Arial
  glyph and EDF missing-geometry warnings.
- Structured verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality (`287 passed`), preprocessing (`106 passed`), and
  whitespace all passed. `git diff --check` passed.
- The initial verifier attempt failed only because this task card lacked the
  required `Implementation plan` and `Verification` headings; the corrected
  rerun above is authoritative.

Full/boundary verification is not attributed unless a fresh command produces a
readable pytest summary and exit code 0.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_herman_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-herman-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-herman-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-herman-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-herman-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, `.superpowers/`, GUI/editor files, real data,
and test-output directories remain outside this task.

## Checkpoint

The checkpoint is created with `scripts/auto_commit.py` after fresh
verification, using the allowlist above; its final hash is reported in the
handoff. No push, merge, deployment, or scientific publication approval is
part of this task.
