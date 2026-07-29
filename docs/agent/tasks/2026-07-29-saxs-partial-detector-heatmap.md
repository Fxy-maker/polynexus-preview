---
task_id: 2026-07-29-saxs-partial-detector-heatmap
kind: scientific
status: completed
date: 2026-07-29
title: Render partial static and temperature SAXS detector Figures
---

# Partial detector FigurePipeline rendering

## Goal

Carry existing mixed finite/non-finite static and temperature detector Figure
projections through the production renderer, Manifest, and Export boundaries
without inventing missing pixels.

## Non-goals

- No interpolation, padding, reshaping, pixel replacement, or frame repair.
- No changes to SAXS analysis, quality levels, physical thresholds, orientation
  evidence, AI/rescue semantics, publication roles, or Manifest schema.
- No relaxation of ordinary heatmap regular-grid validation.
- No cleanup or migration of existing test/storage/scratch directories.

## Affected boundaries

- polynexus/core/figures/renderer.py: explicit masked partial detector grid.
- polynexus/core/saxs_engine/figure_static.py: detector object capability.
- polynexus/core/saxs_engine/figure_temperature.py: detector object capability.
- Focused renderer and SAXS FigurePipeline regressions.

## Acceptance criteria

- [x] A detector heatmap with missing coordinate cells renders only when it has
  allow_partial_detector_grid: true.
- [x] Missing cells remain masked/blank; no source values are interpolated or
  filled.
- [x] Ordinary heatmaps without the opt-in still fail on incomplete grids.
- [x] Static and temperature partial detector Figures produce ready Manifest
  entries with exported assets.
- [x] Persisted detector provenance still reports partial_nonfinite with the
  original sampled/retained/non-finite counts.
- [x] All existing SAXS physical, quality, publication, and AI/rescue contracts
  remain unchanged.
- [x] Fresh structured verification, SAXS matrix, hygiene, storage dry-run, and
  explicit allowlist checkpoint evidence are recorded.

## Implementation plan

1. Add RED tests for explicit partial detector masking, strict ordinary
   heatmap rejection, and static/temperature FigurePipeline readiness.
2. Implement the renderer opt-in and mark only the two detector providers as
   partial-safe.
3. Run focused tests, structured verification, the fresh SAXS matrix, hygiene,
   and storage dry-run.
4. Update durable memory and create the explicit allowlist checkpoint.

## Explicit changed-file allowlist

- docs/agent/tasks/2026-07-29-saxs-partial-detector-heatmap.md
- docs/superpowers/specs/2026-07-29-saxs-partial-detector-heatmap-design.md
- docs/superpowers/plans/2026-07-29-saxs-partial-detector-heatmap.md
- polynexus/core/figures/renderer.py
- polynexus/core/saxs_engine/figure_static.py
- polynexus/core/saxs_engine/figure_temperature.py
- tests/test_figure_render_plan_core.py
- tests/test_saxs_detector_figure_modes.py
- docs/agent/memory/active-work.md

## Pre-existing workspace changes

Keep docs/agent/memory/current-state.md, historical pytest/storage
directories, .superpowers/, GUI/editor drafts, release packet files, and all
other unrelated untracked files outside this task checkpoint.

## Verification commands

    python -m pytest -q tests/test_figure_render_plan_core.py -k "partial_detector or strict_missing_grid"
    python -m pytest -q tests/test_saxs_detector_figure_modes.py -k "pipeline or manifest"
    python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-partial-detector-heatmap.md --changed --types
    python -m pytest -q tests/test_saxs_*.py
    python scripts/test_storage.py report --json
    python scripts/test_storage.py clean --older-than-hours 24
    git diff --check

Storage commands are report/dry-run only; test_storage.py --apply is not part
of this task.

## Verification

The required verification commands are:

    python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-partial-detector-heatmap.md --changed --types
    python -m pytest -q tests/test_saxs_*.py
    python scripts/test_storage.py report --json
    python scripts/test_storage.py clean --older-than-hours 24
    git diff --check

The exact command output, exit codes, warnings, and any timeout limitation will
be recorded here before the checkpoint.

## Verification evidence

- TDD RED: renderer 1 failed, 1 passed; static/temperature pipeline 2 failed;
  failures were the expected incomplete-grid rejection.
- GREEN focused matrix: 68 passed with exit code 0.
- Structured verifier: task-check valid; Ruff, compile, type baseline, quality
  287 passed, preprocessing 106 passed, and whitespace all passed.
- Fresh SAXS matrix: 565 passed, 6 warnings in 332.26s, exit code 0.
- Storage report and clean were non-mutating dry-runs: 16 artifacts, 15,746
  eligible bytes, 0 removed. No --apply was run.
- git diff --check exited 0. Checkpoint: `2a6933b`. Existing current-state,
  scratch, and unrelated untracked files remain outside the allowlist.
