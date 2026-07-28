---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS invariant conservation against dirty arrays
---

# SAXS invariant-conservation dirty-input guard

## Goal

Make `check_invariant_conservation()` tolerate malformed strain/Q* arrays and
retain only valid measured pairs while preserving its existing result contract.

## Non-goals

- Do not change the mean/std/CV/deviation equations, result keys, tolerance
  semantics, finite negative-Q behavior, or minimum-point gate.
- Do not add a Q* positivity rule, interpolate, pad, sort, fabricate frames,
  invoke AI/rescue, or alter publication roles.
- Do not edit GUI code, real datasets, generated outputs, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`: public invariant helper only.
- `tests/test_saxs_invariant_conservation_dirty_input.py`: focused regression.
- This task's spec, plan, acceptance note, and durable active-work memory.

## Implementation plan

1. Write RED tests for malformed/non-finite pairs, common-prefix alignment,
   tolerance coercion, order, insufficient input, and immutability.
2. Coerce local arrays, align prefixes, retain finite measured pairs, and keep
   the existing conservation calculation unchanged.
3. Run focused and SAXS verification, record evidence and storage audit, then
   create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] Malformed Q*/strain tokens no longer raise.
- [x] Non-finite pairs are excluded without reordering or fabricating data.
- [x] Mismatched arrays use common-prefix alignment without indexing errors.
- [x] Malformed tolerance fails closed without raising.
- [x] Clean output, finite negative-Q behavior, result keys, and caller arrays
  remain compatible.
- [x] TDD RED/GREEN, matrices, verifier, diff, storage audit, and checkpoint
  are recorded.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_invariant_conservation_dirty_input.py --basetemp=D:\PolyNexus_saxs_invariant_conservation_redgreen
python -m pytest -q tests/test_saxs_strain*.py --basetemp=D:\PolyNexus_saxs_invariant_conservation_strain_matrix
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_invariant_conservation_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No fresh full/boundary result is attributed unless a fresh command returns a
pytest summary and exit code 0.

## Verification evidence

- TDD RED: `6 failed`; failures were the expected raw `np.isfinite`, boolean
  mismatch, malformed-tolerance, and non-finite-strain inclusion behavior.
- Focused GREEN: `6 passed in 0.13s`.
- Strain matrix: `11 passed in 0.35s`, exit code `0`.
- Exact SAXS matrix: `524 passed, 6 warnings in 195.72s`, exit code `0`.
- `python scripts/verify.py --task ... --types`: exit code `0`; task/memory,
  Pyright (`0 errors, 0 warnings, 0 informations`), quality `287`,
  preprocessing `106`, compile, whitespace, and diff checks passed.
- Targeted Ruff and `py_compile` for `saxs_strain.py` and the task test passed.
- The prescribed `--changed --types` variant exited `1` only because the
  pre-existing parallel modification in `polynexus/core/saxs_engine/io.py`
  selected ten unrelated E402/E741/F401 findings. `io.py` is outside this
  task's allowlist and was not edited.
- Storage dry-run: `530` artifacts, `202` eligible, `328` protected, `0`
  removed. No cleanup apply was run for this task.

## Verification

The focused RED run must show the pre-fix raw-array failure; GREEN and the
strain/SAXS matrices must return exit code 0. The structured command is:

`python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md --changed --types`

Test-storage cleanup remains dry-run unless explicitly authorized.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_invariant_conservation_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-invariant-conservation-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-invariant-conservation-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, `saxs_engine/io.py`, GUI/editor drafts,
`.superpowers/`, and external test-output directories are outside this task.

## Checkpoint

Fresh verification is complete; the explicit allowlist checkpoint is the next
and final local action. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
