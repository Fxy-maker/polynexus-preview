---
kind: task
status: completed
date: 2026-07-29
title: Harden SAXS temperature and strain 1D Figure projections against dirty tokens
---

# SAXS temperature/strain 1D Figure dirty projection

## Goal

Keep all scoped SAXS 1D Figure routes usable when q/intensity or derived 1D
trace arrays contain malformed individual tokens, without changing scientific
eligibility or quality semantics.

## Non-goals

- No changes to SAXS analysis, DataQualityReport levels, physical thresholds,
  condition-axis semantics, publication roles, AI/rescue, or GUI behavior.
- No interpolation except the existing strain common-q overlap interpolation
  after valid curves have been selected.
- No padding, frame fabrication, neighbor copying, inference, automatic rescue,
  2D detector/image/chi handling, or real-data edits.
- Do not modify `docs/agent/memory/current-state.md`, scratch, or parallel
  workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_common.py`: shared detached projection.
- `polynexus/core/saxs_engine/figure_static.py`: reuse the shared projection.
- `polynexus/core/saxs_engine/figure_temperature.py`: temperature 1D profile
  and derived trace projection.
- `polynexus/core/saxs_engine/figure_strain.py`: strain 1D profile, heatmap,
  and derived trace projection.
- `polynexus/core/saxs_engine/figure_provider.py`: legacy `_clean_frame`
  projection.
- Existing SAXS Figure provider tests plus this task's durable artifacts.

## Acceptance criteria

- [x] Shared coercion preserves positions, converts malformed elements to
      `NaN`, and never mutates input arrays.
- [x] New temperature Figure routes retain valid q/I pairs from a dirty frame
      and omit fully invalid curves without raising.
- [x] New strain Figure routes retain valid q/I pairs in representative
      profiles and the existing q-strain heatmap path.
- [x] Legacy temperature/strain `_clean_frame` routes retain valid pairs.
- [x] Existing clean Figure definitions, role assignments, and fail-closed
      behavior remain unchanged.
- [x] TDD, focused/SAXS/structured verification, storage dry-run, diff audit,
      and explicit allowlist checkpoint evidence are recorded.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_figure_1d_dirty_focus'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_evidence_binding.py -k dirty_projection
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-figure-1d-dirty-projection.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact `tests/test_saxs_*.py` matrix must use an external basetemp and is a
pass only with a final pytest summary and exit code `0`. `test_storage.py
--apply` must not be executed.

## Implementation plan

1. Add RED tests to the real temperature, strain, and legacy Figure provider
   entry points without changing production code.
2. Run the selected tests and record the expected whole-array conversion
   failures.
3. Add `_coerce_numeric_array()` to `figure_common.py`, migrate static and
   scoped temperature/strain/legacy 1D call sites, and preserve their existing
   filtering and fail-closed rules.
4. Run focused GREEN and clean provider regression suites, then the structured
   verifier and exact SAXS matrix.
5. Run storage report/clean dry-run, inspect the cumulative allowlist diff,
   update durable evidence, and create one checkpoint with `auto_commit.py`.

## Verification evidence

- TDD RED for q/I provider paths: `3 failed, 21 deselected`; the new
  temperature/strain/legacy regressions reproduced the expected missing source
  or whole-array `ValueError` behavior.
- TDD RED for derived traces: after restoring the two call sites to their
  pre-change whole-array conversions, `2 failed, 15 deselected`; both trace
  regressions failed because dirty trace sources were omitted. The old code was
  then replaced by the shared helper before GREEN.
- TDD GREEN: dirty projection matrix `7 passed, 22 deselected in 0.51s`;
  complete related provider files returned `29 passed in 5.10s`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `287 passed in 7.74s`, preprocessing `106 passed in
  3.06s`, and whitespace all passed.
- Exact SAXS matrix exited `0`: `540 passed, 6 warnings in 315.38s
  (0:05:15)`. Warnings were existing Arial glyph and EDF geometry-header
  warnings.
- `git diff --check` exited `0`.
- Storage report and clean were dry-run only: `302` artifacts, `40` eligible,
  `262` protected, `0` removed. `test_storage.py --apply` was not executed;
  no test directory was deleted, moved, or migrated.
- The explicit allowlist checkpoint is created after these results; its commit
  hash is reported in the handoff. No push, merge, deployment, or unrelated
  cleanup was performed.

## Known limitations

This task covers 1D q/I and derived trace projection only. The remaining
condition/result arrays in the legacy provider and the 2D detector image,
azimuthal chi, geometry, mask, saturation, and orientation paths retain their
existing contracts and require separate scientific/quality tasks. No analysis
quality level, physical threshold, AI/rescue decision, publication role, or
human scientific/release gate was changed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_common.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_panels.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-figure-1d-dirty-projection.md`
- `docs/superpowers/specs/2026-07-29-saxs-figure-1d-dirty-projection-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-figure-1d-dirty-projection.md`
- `docs/acceptance/2026-07-29-saxs-figure-1d-dirty-projection.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, the staged
`docs/agent/memory/active-work.md` release-packet work, `.superpowers/`,
historical pytest/storage directories, and all other untracked or parallel
files remain outside this checkpoint. The new active-work evidence remains
staged in that shared file for the parallel owner to retain.
