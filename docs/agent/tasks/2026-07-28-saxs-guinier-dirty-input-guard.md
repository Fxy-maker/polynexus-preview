---
kind: task
status: completed
date: 2026-07-28
title: Guard the public SAXS Guinier helper against dirty q/I inputs
---

# SAXS Guinier dirty-input guard

## Goal

Extend the existing deterministic 1D sanitizer to the public low-level
Guinier helper so recoverable dirty q/I observations do not raise or enter the
fit in an invalid order.

## Decision and boundaries

The helper will reuse `sanitize_1d_profile()` and keep all existing Guinier
selection and fit semantics. This task is limited to the helper input
boundary; the normal `analyze_single()` quality report remains the provenance
authority. No threshold, physical interpretation, rescue behavior, or
publication role changes.

## Non-goals

- Do not change Guinier fitting, q-window selection, `qRg` rules, or evidence
  classification.
- Do not interpolate, extrapolate, aggregate duplicate q values, fabricate
  frames, copy neighbors, rescue, invoke AI, or alter publication roles.
- Do not edit real datasets, generated outputs, GUI code, or parallel scratch.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_physical_helpers.py`: low-level Guinier
  q/I input boundary.
- `polynexus/core/saxs_engine/__init__.py`: existing public export, unchanged.
- `tests/test_saxs_guinier_dirty_input.py`: focused contract regressions.
- task/spec/plan, acceptance, and durable active-work records.

## Affected files

- `polynexus/core/saxs_engine/saxs_physical_helpers.py`: sanitize q/I before
  the existing Guinier calculation.
- `tests/test_saxs_guinier_dirty_input.py`: focused dirty, clean, empty, and
  immutability regressions.
- this task card, its design/spec and implementation plan, acceptance evidence,
  and `docs/agent/memory/active-work.md`.

## Acceptance criteria

- [x] String, non-finite, non-positive, and unsorted q/I pairs are handled by
  the existing sanitizer without raising.
- [x] Returned fit q values are finite, positive, and sorted; invalid pairs do
  not contribute to the fit.
- [x] Clean inputs retain the previous numeric result.
- [x] Fewer than ten usable points retain the existing NaN/empty return shape.
- [x] Caller-owned arrays are unchanged.
- [x] TDD RED/GREEN, exact SAXS matrix, structured verifier, diff check, and
  explicit allowlist checkpoint are recorded with real output.

## Implementation plan

1. Add dirty, empty, clean-reference, and caller-immutability tests and observe
   the expected RED at the raw NumPy boundary.
2. Reuse `sanitize_1d_profile()` at the start of `guinier_analysis()` and leave
   the existing fit body unchanged; rerun the focused GREEN suite.
3. Run the exact SAXS matrix, structured verifier, and diff check using an
   external basetemp, then record actual output and create the allowlisted
   checkpoint.

## Verification

The focused test, exact SAXS matrix, and task-scoped verifier commands below
must produce readable summaries and exit code 0. A timeout or an older
full/boundary process is not counted as evidence for this task.

### Verification commands

```powershell
python -m pytest -q tests/test_saxs_guinier_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_guinier_dirty_redgreen
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_guinier_dirty_matrix
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_guinier_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-guinier-dirty-input-guard.md --changed --types
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

A full/boundary result is not attributed to this atomic task unless a fresh
command produces both a readable pytest summary and exit code 0.

## Verification record

- TDD RED: the focused run returned `2 failed, 1 passed` in `0.66s`; the two
  failures were the expected `TypeError` from `np.isfinite()` on dirty object
  and string q/I input.
- TDD GREEN: the focused run returned `3 passed in 0.22s` after the Ruff-safe
  local-name correction.
- Exact SAXS matrix: `487 passed, 6 warnings in 260.77s` with exit code `0`.
  Warnings are the existing Arial glyph warnings and EDF missing-geometry
  warnings; no new warning family was introduced.
- Structured verifier: the first attempt exposed only the new local `E741`
  naming issue; the corrected rerun exited `0` with task/memory checks,
  Ruff/compile/type baseline, quality `287 passed`, preprocessing `106 passed`,
  and whitespace all passing.
- `git diff --check`: exit code `0`.
- No full/boundary result is attributed to this task; the independent older
  process has no readable terminal summary or exit code.

## Scientific limitation

This change only makes a public helper consume already-approved deterministic
survivors. It does not establish Guinier applicability, add a q window or
quality threshold, interpret phase transitions, or promote any evidence or
publication role.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- `tests/test_saxs_guinier_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-guinier-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-guinier-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-guinier-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-guinier-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, GUI/editor drafts, `.superpowers/`, running
processes, and all test-output directories remain outside this task.

## Checkpoint

Checkpoint `c4c78a7` was created with `scripts/auto_commit.py` using only the
explicit allowlist above. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
