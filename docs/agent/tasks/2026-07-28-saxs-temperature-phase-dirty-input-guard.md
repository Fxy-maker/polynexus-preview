---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS temperature-phase classification against dirty scalars
---

# SAXS temperature-phase dirty-input guard

## Goal

Make `detect_temperature_phase()` degrade malformed numeric scalar inputs
without changing its existing thermal-phase classification rules.

## Non-goals

- Do not change Q*/Qsolid normalization, heating/cooling/isothermal thresholds,
  cold-crystallization logic, enum members, or default branch.
- Do not infer a phase, copy a neighboring frame, add quality thresholds,
  interpolate, invoke AI/rescue, or alter publication roles.
- Do not change the existing q/I frame-count mismatch contract.
- Do not edit GUI code, real datasets, generated outputs, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: scalar classifier only.
- `tests/test_saxs_temperature_phase_dirty_input.py`: focused regression.
- This task's spec, plan, acceptance note, and durable active-work memory.

## Implementation plan

1. Write RED tests for numeric strings, malformed/non-finite Q*/L values,
   branch equivalence, and the unknown experiment-type fallback.
2. Coerce the four numeric values with `_coerce_optional_float()` and leave
   the phase branch body unchanged.
3. Run focused and SAXS verification, record evidence, and create the explicit
   allowlist checkpoint.

## Acceptance criteria

- [x] Numeric strings and malformed/non-finite scalar inputs no longer raise.
- [x] Clean numeric inputs produce identical `TempPhase` members.
- [x] Existing thresholds and experiment-type branches remain unchanged.
- [x] No inference, rescue, interpolation, or publication behavior is added.
- [x] TDD RED/GREEN, matrices, structured verifier, diff, storage audit, and
  explicit checkpoint are recorded.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_temperature_phase_dirty_input.py --basetemp=D:\PolyNexus_saxs_temperature_phase_redgreen
$temperatureTests = Get-ChildItem -Path tests -Filter 'test_saxs_temperature*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $temperatureTests --basetemp=D:\PolyNexus_saxs_temperature_phase_temperature_matrix
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_phase_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-phase-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No fresh full/boundary result is attributed to this atomic task unless a
fresh command returns a pytest summary and exit code 0.

## Verification evidence

- TDD RED: `3 failed, 2 passed`; failures were the expected raw scalar
  comparison/`np.isfinite` TypeErrors.
- Focused GREEN: `5 passed in 0.10s`.
- Temperature matrix: `53 passed in 19.94s`, exit code `0`.
- Exact SAXS matrix: `518 passed, 6 warnings in 256.45s`, exit code `0`.
- `python scripts/verify.py --task ... --types`: exit code `0`; task/memory,
  Pyright (`0 errors, 0 warnings, 0 informations`), quality `287`,
  preprocessing `106`, compile, whitespace, and diff checks passed.
- Targeted Ruff and `py_compile` for the two task Python files passed.
- The prescribed `--changed --types` variant was run and exited `1` only
  because pre-existing parallel changes in `polynexus/core/saxs_engine/io.py`
  selected ten unrelated E402/E741/F401 Ruff findings. `io.py` is outside
  this task's allowlist and was not edited.
- Storage dry-run: `526` artifacts, `192` eligible, `334` protected, `0`
  removed. No cleanup apply was run for this task.

## Verification

The focused RED run must fail on the pre-fix raw-scalar boundary, GREEN and
the matrices must return exit code 0, and the structured command is:

`python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-phase-dirty-input-guard.md --changed --types`

Test-storage cleanup remains dry-run unless explicitly authorized.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_phase_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-temperature-phase-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-temperature-phase-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, GUI/editor drafts, `.superpowers/`, and
external test-output directories are outside this task.

## Checkpoint

Fresh verification is complete; the explicit allowlist checkpoint is the next
and final local action. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
