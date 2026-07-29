---
kind: task
status: completed
date: 2026-07-30
title: Preserve SAXS representative selection features for dirty profiles
---

# SAXS representative selection dirty profile

## Goal

Keep valid area and maximum-intensity evidence available to deterministic SAXS
representative-frame selection when individual q/I tokens are malformed.

## Non-goals

- No change to representative-frame limits, condition ordering, transition
  ranking policy, minimum separation, manual override validation, or frame
  indices.
- No interpolation, value replacement, q/I sorting in place, frame creation,
  AI call, rescue decision, or core analysis re-run.
- No changes to quality levels, physical metrics, publication roles, or release
  authorization.
- No edits to real datasets, generated outputs, scratch, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_selection.py`: representative selection
  intensity-feature projection.
- `tests/test_saxs_figure_selection_dirty_input.py`: focused q/I regression.

## Acceptance criteria

- [x] A malformed q or intensity token no longer erases all usable area/max
  features for that frame.
- [x] Existing aligned-prefix, finite-pair, sorting, integration, maximum,
  and fail-closed behavior remains intact.
- [x] Representative selection output and source arrays remain unchanged apart
  from retaining valid feature evidence.
- [x] Structured, SAXS, storage dry-run, diff, and allowlist evidence is
  recorded before checkpoint.

## Implementation plan

1. Add a focused malformed-profile test for `_intensity_features()` and run it
   RED against the existing whole-array conversion.
2. Import the existing numeric projection helper and replace only the two
   whole-array conversions in `_intensity_features()`.
3. Run focused GREEN, structured verification, the fresh SAXS matrix, storage
   dry-runs, diff audit, and explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_rep_selection_dirty_focus'
python -m pytest -q tests/test_saxs_figure_selection_dirty_input.py
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-representative-selection-dirty-profile.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix is the PowerShell-expanded `test_saxs_*.py` list with an
external basetemp. It counts as passing only with a final pytest summary and
exit code `0`. No storage `--apply` command is allowed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_selection.py`
- `tests/test_saxs_figure_selection_dirty_input.py`
- `docs/agent/tasks/2026-07-30-saxs-representative-selection-dirty-profile.md`
- `docs/superpowers/specs/2026-07-30-saxs-representative-selection-dirty-profile-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-representative-selection-dirty-profile.md`
- `docs/acceptance/2026-07-30-saxs-representative-selection-dirty-profile.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, checkpoint history,
historical pytest/storage directories, `.superpowers/`, `tests/_tmp_phase3/`,
GUI/editor drafts, and all other untracked or parallel files remain outside
this task checkpoint.

## Verification evidence

- TDD RED: `1 failed` with the expected `(nan, nan)` from the whole-array
  conversion.
- Focused GREEN: `9 passed in 0.16s`.
- Structured verifier: exit `0`; task/memory checks, Ruff, compile, type
  baseline, quality `290 passed`, preprocessing `106 passed`, whitespace, and
  `git diff --check` passed.
- Fresh SAXS matrix: `594 passed, 6 warnings in 400.98s (0:06:40)`, exit code
  `0`. Warnings are the existing Arial glyph and EDF geometry-header warnings.
- Storage remained dry-run only: `54` artifacts, `14367454080` bytes,
  `eligible_bytes=0`; clean reported `Eligible: 0 bytes` and
  `Cleanup failures: 0`. No `test_storage.py --apply` ran and no directories
  were removed or migrated.
- The prior full/boundary attempt after `765bda3` remains a timeout without a
  final summary and is not attributed to this task.
