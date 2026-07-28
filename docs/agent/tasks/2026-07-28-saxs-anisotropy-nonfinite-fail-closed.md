---
kind: task
status: completed
date: 2026-07-28
title: Fail closed on non-finite SAXS 2D anisotropy inputs
---

# SAXS anisotropy non-finite input fail-closed

## Goal

Prevent `NaN` and infinite values in required SAXS 2D anisotropy inputs from
reaching orientation calculations. Return the existing empty result with
explicit `Unusable` orientation evidence instead.

## Non-goals

- Do not interpolate, delete, replace, or impute non-finite pixels or axes.
- Do not infer detector geometry, beam center, masks, saturation, or an axis.
- Do not change valid anisotropy calculations, physical thresholds, quality
  levels, rescue behavior, or downstream Figure/Workbench/Export contracts.
- Do not edit real datasets, generated outputs, `current-state.md`, or
  parallel task files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_anisotropy.py`: finite-input validation in
  the existing normalization boundary.
- `tests/test_saxs_2d_detector_orientation_evidence.py`: non-finite regression
  and strict evidence serialization.
- Task/spec/plan and `docs/agent/memory/active-work.md`: durable workflow and
  verification evidence.

## Implementation plan

1. Add a parameterized regression for `NaN`, `Inf`, and `-Inf` in each of the
   five required anisotropy inputs and observe the expected RED result.
2. Add one finite-input guard to `_normalize_anisotropy_inputs()` that returns
   `orientation_input_nonfinite` without changing valid analysis behavior.
3. Run focused 2D/strain/batch tests, the structured verifier, diff check, and
   test-storage dry-run using external basetemp directories.
4. Run the exact SAXS matrix within the available bound, record only a fresh
   pytest summary, update durable memory, and create the explicit allowlist
   checkpoint.

## Acceptance criteria

- [x] Non-finite values in any of `I_2d`, `q`, `chi`, `q_1d`, and `I_1d` never
  raise from `analyze_anisotropy()`.
- [x] Each invalid case returns no orientation metrics and `Unusable`
  orientation evidence with `orientation_input_nonfinite`.
- [x] Detector and orientation evidence pass strict JSON serialization with
  `allow_nan=False`.
- [x] Existing valid configured-axis, auto-axis, isotropic, empty, and shape
  mismatch paths remain passing.
- [x] Focused tests, structured verifier, diff check, and storage dry-run are
  recorded; the exact SAXS matrix is only called passing with a fresh summary.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_anisotropy_nonfinite_red'
python -m pytest -q tests/test_saxs_2d_detector_orientation_evidence.py -k nonfinite

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_anisotropy_nonfinite_focus'
python -m pytest -q tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_strain_sector_fail_closed.py tests/test_saxs_strain_axis_fail_closed.py tests/test_saxs_batch_parameters.py

python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The exact SAXS matrix is run separately as `python -m pytest -q
tests/test_saxs_*.py` with an external basetemp; a timeout or missing pytest
summary is recorded as a limitation, not a pass.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `tests/test_saxs_2d_detector_orientation_evidence.py`
- `docs/agent/tasks/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md`
- `docs/superpowers/specs/2026-07-28-saxs-anisotropy-nonfinite-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The shared worktree contains a modified `docs/agent/memory/current-state.md`,
historical pytest/test-storage directories, `.superpowers/`, GUI/editor drafts,
and other parallel task files. They remain outside this task checkpoint.

## Verification evidence

- TDD RED: `15 failed, 10 deselected`; every failure was the expected
  `confidence == 0.0` assertion because the old normalizer accepted the
  non-finite input and continued analysis.
- TDD GREEN: `15 passed, 10 deselected`.
- Focused 2D/strain/batch matrix: `69 passed in 0.68s`.
- Structured verifier: exit `0`; task card valid, memory check passed, Ruff,
  compile, type baseline, whitespace, quality `287 passed`, and preprocessing
  `106 passed` all passed.
- `git diff --check`: passed.
- Test-storage report: exit `0`, dry-run mode; `484` artifacts, `100` eligible,
  `384` protected, and `0` removed. No data was deleted or moved.
- Exact SAXS matrix: attempted with an external basetemp using the resolved
  `test_saxs_*.py` file list; timed out after `124` seconds with no pytest
  summary (`exit 124`). The residual process was confirmed as the same matrix
  command and was no longer present on final process inspection. This matrix
  is not claimed as passed.
- Explicit allowlist checkpoint: this task card and the listed source, test,
  spec, plan, and active-work files are the final checkpoint allowlist.
