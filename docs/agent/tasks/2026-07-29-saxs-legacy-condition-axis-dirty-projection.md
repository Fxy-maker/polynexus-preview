---
kind: task
status: completed
date: 2026-07-29
title: Degrade legacy SAXS condition-axis Figures on dirty values
---

# SAXS legacy condition-axis dirty projection

## Goal

Keep legacy static/strain SAXS Figure definitions usable when a condition-axis
array contains malformed individual values, while preserving frame order and
making unresolved labels explicit.

## Non-goals

- No change to SAXS analysis, strain/temperature semantics, source ordering,
  quality levels, metric evidence, physical gates, rescue, AI, or publication
  roles.
- No interpolation, padding, condition inference, sorting, frame deletion, or
  replacement values.
- No change to modern Figure providers, detector/orientation projections, GUI,
  real datasets, generated output, memory files, or parallel workspace files.
- Structural frame-count mismatch behavior remains unchanged.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_provider.py`: legacy condition-axis
  projection used by non-temperature static/strain compatibility routes.
- `tests/test_saxs_temperature_figure_provider.py`: focused legacy strain
  regression.
- This task's task/spec/plan/acceptance documents only.

## Design invariants

- Numeric condition tokens retain their numeric value and existing label
  formatting.
- A malformed or non-finite condition token becomes `NaN` in a detached
  projection and is displayed by the existing `_frame_label()` fallback as
  `Frame <index>`.
- The original condition sequence and frame data are not mutated or reordered.
- If the projected array length does not match the frame count, the existing
  all-`NaN` fallback remains in force.

## Acceptance criteria

- [x] RED reproduces the current `ValueError` for a dirty legacy strain axis.
- [x] GREEN emits all valid frame Figures and a deterministic fallback label
      for the unresolved condition.
- [x] Source arrays remain unchanged and frame order is preserved.
- [x] Existing clean, dirty q/I, partial-frame, and V2 lifecycle regressions
      remain green.
- [x] TDD, focused tests, exact SAXS matrix, structured verification, storage
      dry-run, diff audit, and explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: `1 failed, 11 deselected`; the failure was the expected whole-array
  conversion `ValueError` for `bad-strain`.
- TDD GREEN: `1 passed, 11 deselected`; complete legacy provider returned
  `12 passed`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, quality
  `287 passed`, preprocessing `106 passed`, and whitespace all passed.
- Exact SAXS matrix exited `0`: `575 passed, 6 warnings in 508.86s`.
  Warnings were existing Arial glyph and EDF geometry-header warnings.
- `git diff --check` exited `0`.
- Storage report and clean were dry-run only: `30` artifacts, `0` eligible
  bytes, `6` zero-byte legacy entries classified eligible, `24` younger-than-
  retention entries, and `0` removed. `test_storage.py --apply` was not run.
- The explicit allowlist checkpoint is created after these results; its commit
  hash is reported in the handoff.

## Known limitations

This task covers only legacy static/strain Figure condition labels. It does
not alter analysis condition semantics, source ordering, modern Figure
providers, detector/orientation paths, quality or physical gates, AI/rescue,
publication roles, or human scientific/release review.

## Implementation plan

1. Add a RED regression through `build_saxs_figure_definitions()` with a
   legacy strain state whose condition array contains one malformed token.
2. Replace only the condition-axis whole-array conversion with the existing
   detached `_coerce_numeric_array()` helper; preserve the existing length
   fallback and `_frame_label()` behavior.
3. Run focused legacy provider coverage, exact SAXS, structured verification,
   diff check, and storage report/clean dry-runs.
4. Record actual evidence and create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_condition_red'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k condition_axis

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_condition_green'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py

python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The SAXS matrix counts only with a final pytest summary and exit code `0`.
Storage commands are dry-run; `test_storage.py --apply` is prohibited for
this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `docs/agent/tasks/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md`
- `docs/superpowers/specs/2026-07-29-saxs-legacy-condition-axis-dirty-projection-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md`
- `docs/acceptance/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md`

## Pre-existing workspace changes

The prior SAXS checkpoint, modified IR/Joint/NMR/scientific-review files,
`current-state.md`, GUI/editor/release files, `.superpowers/`, and all
pytest/storage/scratch directories remain outside this checkpoint.
