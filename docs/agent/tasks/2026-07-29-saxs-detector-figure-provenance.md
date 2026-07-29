---
kind: task
status: completed
date: 2026-07-29
title: Explain partial SAXS detector Figure recovery
---

# SAXS detector Figure projection provenance

## Goal

Record deterministic sampled-pixel counts for partial detector Figure
recovery, so a reviewer can distinguish complete projection from a projection
with sampled non-finite pixels omitted.

## Non-goals

- No detector re-analysis, geometry calibration, beam-center inference, mask or
  saturation inference.
- No new thresholds, quality levels, physical gates, publication roles, AI
  calls, rescue decisions, interpolation, or pixel replacement.
- No changes to orientation calculations or raw detector quality reports.
- No edits to real data, generated outputs, scratch, or parallel workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: internal projection counts and
  main Figure recipe provenance.
- `tests/test_saxs_figure_evidence_binding.py`: mixed-pixel provenance
  regression.

## Acceptance criteria

- [x] Mixed finite/non-finite sampled detector data records sampled, retained,
  and non-finite counts with `partial_nonfinite` status.
- [x] Fully finite sampled data records `complete` status.
- [x] Counts are keyed by existing frame index, detached, and strict JSON-safe.
- [x] All-invalid/unreadable detector frames retain the existing fail-closed
  failure path without fabricated provenance.
- [x] Existing focused, structured, SAXS, storage, and allowlist evidence is
  recorded before checkpoint.

## Implementation plan

1. [x] Add the mixed-pixel provenance regression and run it RED.
2. [x] Extend the private detector projection with sampled/retained/non-finite
   counts and pass them to the existing main recipe.
3. [x] Run focused detector/Figure tests and the structured verifier.
4. [x] Run a fresh bounded SAXS matrix and storage report/clean dry-runs only.
5. [x] Create one explicit allowlist checkpoint without touching pre-existing
   workspace changes.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_detector_provenance_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_publication_pack_upgrade.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-detector-figure-provenance.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix uses a PowerShell-expanded file list and an external
basetemp. It is counted as passing only with a fresh pytest summary and exit
code `0`; `test_storage.py --apply` is not permitted.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-detector-figure-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-detector-figure-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-detector-figure-provenance.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, and all other untracked or parallel files remain
outside this checkpoint.

## Verification evidence

- TDD RED: `1 failed` with the expected missing
  `detector_projection_quality` recipe field. An initial selector typo ran
  `0 selected` and was not counted as RED.
- Focused GREEN/consumer matrix: `57 passed in 8.46s`.
- Structured verifier: exit `0`; task/memory, Ruff, compile, type baseline,
  whitespace, quality `287 passed`, and preprocessing `106 passed`.
- Fresh SAXS matrix: `543 passed, 6 warnings in 269.04s (0:04:29)`, exit `0`.
  Warnings are the existing Arial glyph and EDF geometry-header warnings.
- Storage report and clean: dry-run only; `335` artifacts, `40` eligible,
  `295` protected, and `0` removed. `test_storage.py --apply` was not run.

## Known limitations

The counts describe only the deterministic Figure sampling grid, not all raw
detector pixels. They do not validate geometry, masks, saturation, orientation,
or scientific publication readiness; those existing physical and human review
gates remain authoritative.
