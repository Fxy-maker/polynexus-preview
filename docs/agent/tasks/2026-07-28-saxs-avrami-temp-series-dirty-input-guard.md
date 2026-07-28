---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS Avrami temperature-series wrapper against dirty arrays
---

# SAXS Avrami temperature-series dirty-input guard

## Goal

Make `avrami_from_temp_series()` degrade safely on malformed numeric axes and
mismatched series while preserving the existing temperature tolerance and
Avrami validity gates.

## Non-goals

- Do not change `avrami_kinetics()` or its equation, fit range, minimum-point,
  R², exponent, or validity rules.
- Do not interpolate, pad, sort, infer, fabricate observations, or invoke AI or
  automatic rescue.
- Do not change GUI code, real datasets, generated outputs, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: public wrapper only.
- `tests/test_saxs_avrami_temp_series_dirty_input.py`: focused regression.
- This task's spec, plan, acceptance note, and durable active-work memory.

## Implementation plan

1. Write a focused RED regression for malformed temperature values, non-finite
   time/Xc values, mismatched lengths, insufficient survivors, and caller
   immutability.
2. Coerce the three axes with `_as_1d_float_array()`, align their common
   prefix, keep finite temperature-tolerance survivors in order, and delegate
   relative-time fitting to `avrami_kinetics()`.
3. Run focused, temperature, SAXS, structured verifier, diff, and storage
   checks; record exact evidence and create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] Dirty temperature tokens no longer raise and valid selected survivors
  reach the existing Avrami fit.
- [x] Non-finite time/Xc observations are excluded without changing order.
- [x] Mismatched lengths use a common-prefix policy without padding or
  indexing errors.
- [x] Fewer than five selected finite observations return invalid with no
  fabricated metric.
- [x] Clean inputs remain equivalent and caller arrays are unchanged.
- [x] TDD RED/GREEN, focused and SAXS matrices, structured verification,
  storage audit, and explicit allowlist checkpoint are recorded.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_avrami_temp_series_dirty_input.py --basetemp=D:\PolyNexus_saxs_avrami_temp_series_redgreen
$temperatureTests = Get-ChildItem -Path tests -Filter 'test_saxs_temperature*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $temperatureTests --basetemp=D:\PolyNexus_saxs_avrami_temp_series_temperature_matrix
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_avrami_temp_series_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No full/boundary result is attributed to this task unless a fresh command
returns a pytest summary and exit code 0.

## Verification evidence

- TDD RED: `4 failed, 1 passed`; failures were the expected malformed
  temperature arithmetic, mismatched boolean indexing, and dependent dirty
  calls on the pre-fix wrapper.
- Focused GREEN: `5 passed in 0.10s`.
- Temperature SAXS matrix: `48 passed in 15.20s`, exit code `0`.
- Exact SAXS matrix: `508 passed, 6 warnings in 194.16s`, exit code `0`.
  Warnings were the existing Arial CJK glyph and EDF geometry-header
  warnings.
- Structured verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality `287`, preprocessing `106`, and whitespace passed.
- `git diff --check`: exit code `0`; Git emitted only its existing CRLF
  normalization notice.
- Storage dry-run before apply: `524` artifacts, `29` eligible, `495`
  protected, `0` removed.
- Requested apply command exited `1` at
  `D:\PolyNexus\PolyNexusPolyNexus.pytest_tmp_metric_position_full` with
  Windows `WinError 5` (access denied). Five earlier eligible legacy
  directories were removed before the failure; a follow-up report found
  `518` artifacts and `24` eligible remaining. No permission escalation or
  manual deletion was performed.

## Verification

The commands above are the required verification sequence. The focused RED
run must show the pre-fix failure, the focused GREEN run must pass, and the
temperature/SAXS matrices plus structured verifier must return exit code 0.
The storage cleanup command remains dry-run unless an explicit, reviewed
`--apply` is executed after the final report and its eligible paths are
confirmed to be managed test artifacts.

Required structured command: `python scripts/verify.py --task
docs/agent/tasks/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md
--changed --types`.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_avrami_temp_series_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-avrami-temp-series-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-avrami-temp-series-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, GUI/editor drafts, `.superpowers/`, and
external test-output directories are outside this task.

## Checkpoint

Pending fresh verification and `scripts/auto_commit.py` with exactly this
allowlist. No push, merge, deployment, or scientific/publication approval is
part of this task.
