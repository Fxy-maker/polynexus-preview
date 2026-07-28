---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS melting-range helper against dirty arrays
---

# SAXS melting-range dirty-input guard

## Goal

Make `detect_melting_from_saxs()` safely degrade malformed temperature and
peak-intensity inputs while preserving the existing melting-range algorithm.

## Non-goals

- Do not change `_first_sustained_threshold_crossing()`, initial-intensity
  median selection, thresholds, output keys, or melting-range semantics.
- Do not filter finite negative intensities, sort, interpolate, pad, infer,
  fabricate points, invoke AI/rescue, or alter publication roles.
- Do not repurpose the currently unused `q_star_array` parameter.
- Do not edit GUI code, real datasets, generated outputs, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: public melting helper only.
- `tests/test_saxs_melting_dirty_input.py`: focused regression.
- This task's spec, plan, acceptance note, and durable active-work memory.

## Implementation plan

1. Write RED tests for malformed and non-finite temperature/peak pairs,
   common-prefix alignment, order, insufficient input, and immutability.
2. Coerce the consumed arrays with `_as_1d_float_array()`, align local
   prefixes, retain finite pairs, and preserve the existing melting logic.
3. Run focused and repository SAXS verification, record test-storage evidence,
   and create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] Malformed numeric tokens no longer raise; finite survivors reach the
  existing thresholds.
- [x] Non-finite temperature/peak pairs are excluded without reordering.
- [x] Mismatched consumed arrays use common-prefix alignment without indexing
  errors or padding.
- [x] Empty/insufficient input returns the legacy invalid result shape.
- [x] Clean results remain equivalent and caller arrays are unchanged.
- [x] TDD RED/GREEN, temperature/SAXS matrices, structured verifier, diff,
  storage audit, and explicit checkpoint are recorded.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_melting_dirty_input.py --basetemp=D:\PolyNexus_saxs_melting_redgreen
$temperatureTests = Get-ChildItem -Path tests -Filter 'test_saxs_temperature*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $temperatureTests --basetemp=D:\PolyNexus_saxs_melting_temperature_matrix
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_melting_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-melting-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No fresh full/boundary result is attributed to this atomic task unless a
fresh command returns a pytest summary and exit code 0.

## Verification evidence

- Read-only baseline and TDD RED: `4 failed, 1 passed`; failures were the
  expected raw `np.isfinite` TypeError and mismatched consumed-array boundary.
- Focused GREEN: `5 passed in 0.10s`.
- Temperature SAXS matrix: `48 passed in 16.31s`, exit code `0`.
- Exact SAXS matrix: `513 passed, 6 warnings in 238.42s`, exit code `0`.
  Warnings are the existing Arial CJK glyph and EDF geometry-header warnings.
- Structured verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality `287`, preprocessing `106`, and whitespace passed.
- `git diff --check`: exit code `0`; only the existing CRLF normalization
  notice was emitted.
- Test-storage dry-run: `522` artifacts, `24` eligible, `498` protected,
  `0` removed. No cleanup apply was run for this task.

## Verification

The focused RED run must fail on the pre-fix raw-array boundary, the GREEN
run and both SAXS matrices must return exit code 0, and the structured command
must be run exactly as follows:

`python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-melting-dirty-input-guard.md --changed --types`

Test-storage cleanup remains dry-run unless explicitly authorized; no real
datasets or source files may be deleted.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_melting_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-melting-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-melting-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-melting-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-melting-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, GUI/editor drafts, `.superpowers/`, and
external test-output directories are outside this task.

## Checkpoint

Fresh verification is complete; the explicit allowlist checkpoint is the next
and final local action. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
