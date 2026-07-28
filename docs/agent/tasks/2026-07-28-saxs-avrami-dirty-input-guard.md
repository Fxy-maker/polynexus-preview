---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS Avrami kinetics against dirty arrays
---

# SAXS Avrami dirty-input guard

## Goal

Make the public `avrami_kinetics()` boundary tolerate malformed numeric time
and relative-crystallinity arrays while preserving its existing selection,
fit, validity, and result contracts.

## Confirmed baseline

A read-only probe on the current checkout reproduced `TypeError` from
`np.isfinite()` when either array contained a malformed token. Mismatched
array lengths also cannot reach the existing mask safely.

## Decision

Use the existing `_as_1d_float_array()` coercion policy for both arrays, align
to the common prefix without padding, and then run the current finite,
positive-time mask and Avrami range selection on detached local arrays.
Preserve observation order because the kinetics fit uses time as its axis.

## Non-goals

- Do not change the Avrami equation, time positivity rule, Xc range selection,
  clipping, minimum-point gates, R² rule, exponent validity bounds, or result
  keys.
- Do not interpolate, extrapolate, infer missing times, fabricate frames, add
  thresholds, or invoke AI/rescue behavior.
- Do not change `avrami_from_temp_series()`, temperature-axis transport, GUI
  code, real datasets, generated outputs, or parallel workspace changes.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: one public kinetics
  boundary;
- `tests/test_saxs_avrami_dirty_input.py`: dirty, mismatch, empty, and
  immutability regressions;
- this task card, design/spec, implementation plan, acceptance note, and
  durable memory.

## Implementation plan

1. Write a RED regression with malformed object arrays, non-finite values,
   mismatched lengths, explicit valid survivors, and empty-input compatibility.
2. Coerce both arrays with the existing `_as_1d_float_array()`, align local
   prefixes, and leave the current valid mask, range selection, and fit body
   unchanged.
3. Run focused GREEN, temperature and exact SAXS matrices, structured
   verification, diff/storage checks, then record evidence and checkpoint.

## Acceptance criteria

- [x] Malformed numeric tokens no longer raise and valid survivors reach the
  existing Avrami fit.
- [x] Mismatched lengths use the common-prefix policy without padding or
  indexing errors.
- [x] Existing positive-time/Xc selection, clipping, point gates, fit results,
  and result keys remain unchanged for clean input.
- [x] Empty or insufficient input remains invalid with the legacy result shape;
  no metric is fabricated.
- [x] Caller-owned arrays remain unchanged and no new scientific/publication
  semantics are introduced.
- [x] TDD RED/GREEN, focused matrix, exact SAXS matrix, verifier, diff check,
  test-storage dry-run, and explicit allowlist checkpoint are recorded.

## Verification

```powershell
python -m pytest -q tests/test_saxs_avrami_dirty_input.py --basetemp=D:\PolyNexus_saxs_avrami_dirty_redgreen
$temperatureTests = Get-ChildItem -Path tests -Filter 'test_saxs_temperature*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $temperatureTests --basetemp=D:\PolyNexus_saxs_avrami_temperature_matrix
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_avrami_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-avrami-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No fresh full/boundary result is attributed to this atomic task unless the
command returns a pytest summary and exit code 0.

## Verification evidence

- Read-only baseline probe reproduced `TypeError` from `np.isfinite()` for
  malformed time/Xc object arrays.
- TDD RED: `2 failed, 1 passed`.
- Focused GREEN: `3 passed in 0.12s`.
- Temperature SAXS matrix: `48 passed in 19.48s`, exit code `0`.
- Exact SAXS matrix: `503 passed, 6 warnings in 265.09s`, exit code `0`.
  Warnings were the existing Arial CJK glyph and EDF geometry-header warnings.
- Task verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality `287`, preprocessing `106`, and whitespace all passed.
- `git diff --check`: exit code `0` with only Git's CRLF normalization notice.
- Test-storage report and cleanup dry-run: `522` artifacts, `26` eligible,
  `496` protected, `0` removed. No test data was deleted.
- No fresh full/boundary result is attributed to this atomic task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_avrami_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-avrami-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-avrami-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-avrami-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-avrami-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, GUI/editor drafts, `.superpowers/`, and
external test-output directories are outside this task.

## Checkpoint

After fresh verification, create one local checkpoint with
`scripts/auto_commit.py` and exactly this allowlist. No push, merge,
deployment, data deletion, or scientific/publication approval is part of this
task.
