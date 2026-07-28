---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS long-period helpers against dirty q/I inputs
---

# SAXS long-period helper dirty-input guard

## Goal

Extend deterministic q/I sanitization to the public Bragg, Lorentz, and
correlation helper boundaries so recoverable dirty profiles do not raise or
pollute the calculation.

## Non-goals

- Do not change analysis windows, fit algorithms, extrapolation, quality levels,
  or physical thresholds.
- Do not interpolate, extrapolate, aggregate duplicate q values, fabricate
  frames, copy neighbors, rescue, invoke AI, or change publication roles.
- Do not edit real datasets, generated outputs, GUI code, or parallel scratch.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`: sanitize q/I in
  `bragg_long_period()`, `lorentz_fit_long_period()`, and
  `correlation_function()`; add only empty-survivor guards before `q[-1]`.
- `tests/test_saxs_long_period_dirty_input.py`: dirty, clean-reference, empty,
  and immutability regressions.
- this task card, design/spec, implementation plan, acceptance note, and
  `docs/agent/memory/active-work.md`.

## Acceptance criteria

- [x] String, non-finite, non-positive, and unsorted q/I pairs are handled by
  the existing sanitizer without raising in all three helpers.
- [x] Bragg, Lorentz, and correlation outputs do not include invalid q/I pairs.
- [x] Empty/wholly invalid input returns stable diagnostic output without an
  `IndexError`.
- [x] Clean input and caller-owned q/I arrays remain compatible and unchanged.
- [x] TDD RED/GREEN, exact SAXS matrix, structured verifier, diff check, and
  explicit allowlist checkpoint are recorded with real output.

## Implementation plan

1. Add focused tests using a synthetic lamellar-like profile, dirty object
   pairs, clean reference calls, empty input, and caller-array immutability;
   run RED before changing production code.
2. Reuse `sanitize_1d_profile()` at each helper boundary. Preserve the Bragg
   return path and add empty guards to Lorentz/correlation before any q index.
3. Run focused GREEN, the exact SAXS matrix, task verifier, and diff check with
   external basetemps; record exact summaries and warnings.
4. Review the explicit allowlist and create one automatic checkpoint.

## Verification

The focused tests, exact SAXS matrix, and task-scoped verifier below must
produce readable summaries and exit code 0. An absent summary or unrelated
full/boundary process is not evidence for this task.

### Verification commands

```powershell
python -m pytest -q tests/test_saxs_long_period_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_long_period_dirty_redgreen
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_long_period_dirty_matrix
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_long_period_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-long-period-dirty-input-guard.md --changed --types
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

### Verification record

- TDD RED: the initial focused run returned `3 failed in 0.54s`; failures were
  the expected raw `TypeError` at dirty q comparison and empty-profile
  indexing boundaries.
- Focused GREEN: the final rerun returned `3 passed in 0.19s`, exit code `0`.
  An intermediate assertion-only failure was corrected in the regression test
  because object-array `NaN` values require an explicit equal-NaN check.
- Exact SAXS matrix: `490 passed, 6 warnings in 239.12s`, exit code `0`, using
  `D:\PolyNexus_saxs_long_period_dirty_matrix`. Warnings were the existing
  font-glyph and missing-EDF-geometry warnings.
- Structured verification exited `0`: task/memory checks passed; Ruff and
  compile passed; no changed files were selected in the type baseline; quality
  passed `287` tests; preprocessing passed `106` tests; and whitespace passed.
- `git diff --check` exited `0`.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/core.py`
- `tests/test_saxs_long_period_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-long-period-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-long-period-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-long-period-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-long-period-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, `.superpowers/`, GUI/editor drafts, running
processes, real data, and all test-output directories remain outside this task.

## Checkpoint

The checkpoint was created with `scripts/auto_commit.py` using only the
explicit allowlist; the final amended commit hash is reported in the handoff.
No push, merge, deployment, or publication approval is part of this task.
