---
kind: task
status: completed
date: 2026-07-29
title: Preserve finite SAXS detector pixels in Figure projection
---

# SAXS detector Figure dirty projection

## Goal

Keep the strain detector Figure evidence usable when a loaded 2D image has
individual malformed pixels, while leaving all analysis and quality decisions
unchanged.

## Non-goals

- No interpolation, padding, pixel replacement, geometry inference, mask
  inference, saturation inference, or automatic rescue.
- No change to `analyze_anisotropy()` or orientation evidence.
- No change to physical thresholds, quality levels, eligibility, publication
  roles, AI/rescue, or detector quality reports.
- No edits to real datasets, generated outputs, scratch directories, or the
  parallel staged release packet.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: sampled detector Figure data
  projection only.
- `tests/test_saxs_figure_evidence_binding.py`: focused detector regression.

## Acceptance criteria

- [x] A mixed finite/non-finite detector image retains every finite sampled
  pixel with its original sampled coordinates.
- [x] No invalid value reaches the detector Figure source or strict JSON
  serialization.
- [x] An all-invalid, empty, non-2D, or unreadable detector image remains
  unavailable and records the existing failure path.
- [x] Existing orientation, quality, publication, and Figure contracts remain
  unchanged.
- [x] Focused, structured, SAXS-matrix, hygiene, and storage dry-run evidence is
  recorded before checkpoint.

## Implementation plan

1. [x] Add the mixed-pixel regression and run it RED.
2. [x] Filter non-finite sampled detector pixels in the projection boundary only.
3. [x] Run focused detector/Figure regressions and the structured verifier.
4. [x] Run a fresh bounded SAXS matrix; report a timeout/no-summary as a limitation,
   never as a pass.
5. [x] Run `test_storage.py report` and dry-run `clean` only.
6. [x] Create one explicit allowlist checkpoint without touching parallel staged
   files.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_detector_dirty_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_publication_pack_upgrade.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-detector-figure-dirty-projection.md --changed --types
python -m pytest -q tests/test_saxs_*.py
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The SAXS matrix uses an external basetemp and is counted as passing only with
a fresh pytest summary and exit code `0`. `test_storage.py --apply` is not
permitted.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-detector-figure-dirty-projection.md`
- `docs/superpowers/specs/2026-07-29-saxs-detector-figure-dirty-projection-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-detector-figure-dirty-projection.md`

## Pre-existing workspace changes

The staged release packet, staged `docs/agent/memory/active-work.md`, modified
`docs/agent/memory/current-state.md`, historical pytest/storage directories,
`.superpowers/`, and other untracked files are intentionally outside this task
and must remain untouched.

## Verification evidence

- TDD RED: `1 failed, 13 deselected`; the old projection rejected the mixed
  non-finite image and omitted the detector source.
- TDD GREEN/focused matrix: `55 passed in 12.35s` across Figure evidence,
  detector orientation, 2D propagation, and publication-pack tests.
- Structured verifier: exit `0`; task card, memory, Ruff, compile, type
  baseline, whitespace, quality `287 passed`, and preprocessing `106 passed`.
- Fresh SAXS matrix: `541 passed, 6 warnings in 358.32s (0:05:58)`, exit `0`.
  Warnings were the existing Arial glyph and EDF geometry-header warnings.
- Storage report and clean: dry-run only; `313` artifacts, `40` eligible,
  `273` protected, and `0` removed. `test_storage.py --apply` was not run.
- Task-specific `git diff --check`: passed.

## Known limitations

This checkpoint only recovers finite pixels for the strain Figure detector
projection. It does not repair detector geometry, masks, saturation, azimuthal
orientation inputs, or analysis results. The anisotropy path remains
fail-closed for non-finite required inputs, and the existing physical and
publication gates remain authoritative.
