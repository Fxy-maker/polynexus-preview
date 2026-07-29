---
task_id: 2026-07-29-saxs-partial-detector-v2-binding
kind: scientific
status: completed
date: 2026-07-29
title: Bind partial SAXS detector figures to the reviewed V2 runtime
---

# Partial detector V2 Figure binding

## Goal

Allow already-supported static and temperature SAXS detector Figures with
partial non-finite source pixels to enter the existing Reactive Figure V2
sidecar, editor session, and publication export path.

## Non-goals

- No interpolation, padding, pixel repair, or alteration of detector values.
- No change to detector projection, quality levels, physical gates,
  orientation, AI/rescue behavior, or publication roles.
- No V2 enablement for unrelated static or temperature SAXS Figures.
- No GUI-specific technique branching or test-storage cleanup.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_static.py`: detector Figure recipe only.
- `polynexus/core/saxs_engine/figure_temperature.py`: detector Figure recipe
  only.
- `tests/test_saxs_detector_figure_modes.py`: static/temperature V2 sidecar,
  reactive session, and reactive publication regression.

## Acceptance criteria

- [x] Valid partial static and temperature detector definitions declare their
  existing reviewed V2 adapter.
- [x] Pipeline Manifest reports `v2_runtime: ready` and writes a V2 sidecar.
- [x] Reactive loading resolves only the retained finite detector cells; the
  missing cells stay absent/blank and no values are manufactured.
- [x] Reactive publication export creates a non-empty asset.
- [x] Persisted `partial_nonfinite` provenance and diagnostic publication role
  remain unchanged.
- [x] Focused, structured, SAXS-matrix, hygiene, and storage dry-run evidence
  is recorded before the allowlist checkpoint.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md`
- `docs/superpowers/specs/2026-07-29-saxs-partial-detector-v2-binding-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-partial-detector-v2-binding.md`
- `docs/agent/memory/active-work.md`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_detector_figure_modes.py`

## Pre-existing workspace changes

Keep `docs/agent/memory/current-state.md`, the running GUI, historical
pytest/storage directories, `.superpowers/`, GUI/editor drafts, release
artifacts, and every other untracked item outside this checkpoint.

## Implementation plan

1. Add a RED regression that proves a partial detector Figure is not currently
   V2-ready in both static and temperature modes.
2. Bind only the two detector Figure recipes to their existing V2 adapters.
3. Verify the V2 sidecar, sparse reactive scene, and reactive publication
   export through the real FigurePipeline.
4. Run structured verification, SAXS regression coverage, hygiene checks, and
   create an explicit allowlist checkpoint.

## Verification commands

    python -m pytest -q tests/test_saxs_detector_figure_modes.py -k "partial_detector and v2"
    python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_reactive_figure_project_service.py tests/test_reactive_figure_layout.py
    python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md --changed --types
    python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
    python scripts/test_storage.py report --json
    python scripts/test_storage.py clean --older-than-hours 24
    git diff --check

## Verification

Run the commands in the preceding section.  The structured gate is:

    python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md --changed --types

Record focused test, verifier, SAXS matrix, storage dry-run, hygiene, and
checkpoint evidence in this card before marking the task complete.

## Verification evidence

- TDD RED: `python -m pytest -q tests/test_saxs_detector_figure_modes.py -k
  "partial_detector and v2"` returned `2 failed, 7 deselected`; both failures
  were the expected `v2_runtime == not_configured` assertion.
- TDD GREEN: the same command returned `2 passed, 7 deselected`.
- Focused detector/reactive matrix: `17 passed in 5.68s`.
- Structured verifier: task check, memory check, Ruff, compilation, quality
  `287 passed`, preprocessing `106 passed`, and whitespace all passed.
- Fresh complete SAXS matrix using the PowerShell-native enumeration command:
  `567 passed, 6 warnings in 416.22s`, exit code 0.  The literal wildcard form
  did not run tests under PowerShell and was corrected before this result.
- Storage report and clean were dry-runs: 18 artifacts, `0` eligible bytes,
  zero removals.  Six zero-byte legacy repository directories are eligible but
  contribute no eligible bytes; no `--apply` was run.
- `git diff --check` exited 0.  The pending explicit allowlist checkpoint is
  limited to the paths recorded above.
