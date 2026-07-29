---
kind: task
status: completed
date: 2026-07-29
title: Keep static SAXS figure projection usable with dirty numeric tokens
---

# SAXS static Figure dirty projection

## Goal

Allow the static SAXS Figure provider to retain valid points from frames with
individual malformed q/intensity tokens, while keeping the existing
fail-closed behavior and all scientific gates unchanged.

## Non-goals

- No changes to SAXS analysis, quality levels, physical thresholds, evidence
  interpretation, rescue/AI, publication roles, or GUI behavior.
- No interpolation, padding, sorting before the existing sort stage, inferred
  values, duplicated neighbors, or automatic rescue.
- No edits to real datasets, generated outputs, `current-state.md`, scratch,
  or parallel worktree changes.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_static.py`: static Figure numeric-pair
  projection.
- `tests/test_saxs_static_figure_panels.py`: focused dirty-frame regression.
- This task card, its design/plan/acceptance records, and
  `docs/agent/memory/active-work.md`: durable evidence only.

## Acceptance criteria

- [x] A dirty static frame with at least two valid positive q/I pairs still
      participates in the static comparison Figure.
- [x] Invalid tokens become `NaN` only in the detached projection and are
      excluded by the existing finite/positive filters.
- [x] A frame with no usable pairs remains excluded without raising.
- [x] Clean static provider output remains unchanged.
- [x] Focused RED/GREEN evidence, structured verification, exact SAXS result
      or limitation, storage dry-run, diff audit, and an explicit allowlist
      checkpoint are recorded.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_figure_dirty_focus'
python -m pytest -q tests/test_saxs_static_figure_panels.py -k dirty_projection
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix is attempted with an external basetemp. A timeout,
missing summary, or tool termination is recorded as a limitation and never as
a pass. `test_storage.py --apply` is explicitly out of scope.

## Implementation plan

1. Add the focused dirty-frame RED test without changing production code.
2. Run the test and record the expected whole-array conversion failure.
3. Add the smallest private elementwise coercion helper and route
   `_numeric_pairs` through it.
4. Run focused GREEN, then task-scoped verification and the exact SAXS matrix.
5. Run storage report/clean dry-run, inspect the cumulative diff, update
   durable evidence, and create one explicit allowlist checkpoint.

## Verification evidence

- TDD RED: `1 failed, 2 deselected in 0.61s`; the dirty frame had no static
  comparison because the existing whole-array `dtype=float` conversion caused
  the profile to be rejected. The all-invalid fail-closed test was not part of
  the `-k dirty_projection` selection at that stage.
- TDD GREEN: `2 passed, 1 deselected in 0.17s`; the complete static panel file
  returned `3 passed in 0.11s`. The regression also confirmed caller-owned
  q/I arrays were unchanged.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `287 passed in 7.71s`, preprocessing `106 passed in
  2.37s`, and whitespace all passed.
- Exact SAXS matrix exited `0`: `535 passed, 6 warnings in 340.57s
  (0:05:40)`. Warnings were existing Arial glyph and EDF geometry-header
  warnings; no test failure was reported.
- `git diff --check` exited `0`.
- Storage report and clean were both dry-run: `292` artifacts, `40` eligible,
  `252` protected, `0` removed. `test_storage.py --apply` was not executed;
  no test directory was deleted, moved, or migrated.
- The explicit allowlist checkpoint was created after verification; its commit
  hash is reported in the handoff. No push, merge, deployment, or cleanup of
  unrelated workspace files was performed.

## Known limitations

This task hardens only the static Figure numeric-pair projection. Invalid
positions remain unavailable to the Figure and are not scientifically repaired;
temperature/strain provider boundaries, analysis quality levels, physical
gates, AI/rescue, publication authorization, GUI review, and human scientific
approval remain separate work or open gates.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_static.py`
- `tests/test_saxs_static_figure_panels.py`
- `docs/agent/tasks/2026-07-29-saxs-static-figure-dirty-projection.md`
- `docs/superpowers/specs/2026-07-29-saxs-static-figure-dirty-projection-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-static-figure-dirty-projection.md`
- `docs/acceptance/2026-07-29-saxs-static-figure-dirty-projection.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, `.superpowers/`, historical
pytest/storage directories, GUI/editor drafts, and all other untracked or
parallel files remain outside this checkpoint.
