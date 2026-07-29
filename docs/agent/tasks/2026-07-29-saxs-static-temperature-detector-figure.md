---
task_id: 2026-07-29-saxs-static-temperature-detector-figure
kind: scientific
status: completed
date: 2026-07-29
title: Add conservative static and temperature SAXS detector Figures
---

# Static and temperature SAXS detector Figure projection

## Goal

Expose existing static and temperature detector-image inputs as detached,
diagnostic 2D Figure definitions with deterministic finite-pixel provenance.

## Non-goals

- No detector re-analysis, geometry/mask/saturation inference, orientation
  calculation, interpolation, pixel replacement, frame fabrication, new
  threshold, quality-level change, publication-role promotion, AI call, or
  rescue action.
- No changes to the existing strain detector Figure, analysis results,
  quality contracts, Manifest schema, Export schema, real data, generated
  output, scratch, or parallel workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_detector.py`: shared read-only detector
  sampling and provenance DTOs.
- `polynexus/core/saxs_engine/figure_static.py`: static diagnostic Figure.
- `polynexus/core/saxs_engine/figure_temperature.py`: temperature diagnostic
  Figure.
- `polynexus/core/saxs_engine/figure_common.py` and
  `polynexus/core/saxs_engine/figure_provider.py`: detector scientific axis
  labels.
- `tests/test_saxs_detector_figure_modes.py`: focused regressions.

## Acceptance criteria

- [x] Static supported detector images produce a diagnostic 2D Figure with
  finite sampled pixel coordinates and log-intensity values.
- [x] Temperature supported detector images use the existing representative
  frame selection and preserve frame/condition provenance.
- [x] Mixed non-finite pixels retain finite samples and record sampled,
  retained, non-finite counts with `partial_nonfinite` status.
- [x] Unsupported, unreadable, malformed, empty, or all-invalid images do not
  produce an empty or fabricated detector Figure.
- [x] Existing 1D definitions, analysis/quality/orientation semantics, and
  publication roles remain unchanged; the new definition is diagnostic only.
- [x] All new recipe/source payloads pass `json.dumps(..., allow_nan=False)`.
- [x] Focused, structured, exact SAXS, hygiene, storage dry-run, and explicit
  allowlist checkpoint evidence are recorded.

## Implementation plan

1. [x] Add focused static and temperature tests for the missing detector Figure
   and run them RED against the current providers.
2. [x] Add the shared projection module and mode-specific diagnostic definitions.
3. [x] Run focused tests GREEN, then the task verifier and fresh SAXS matrix.
4. [x] Run storage `report` and dry-run `clean` only; do not use `--apply`.
5. [x] Audit the diff against this allowlist and create one checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_temperature_detector_focus'
python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_static_figure_panels.py tests/test_saxs_temperature_figure_panels.py tests/test_saxs_publication_pack_upgrade.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-static-temperature-detector-figure.md --changed --types
python -m pytest -q tests/test_saxs_*.py
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The exact SAXS matrix counts as passing only with a fresh complete pytest
summary and exit code `0`. A timeout, no-summary process exit, or historical
result is recorded as a limitation, never as a pass.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_detector.py`
- `polynexus/core/saxs_engine/figure_common.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_detector_figure_modes.py`
- `docs/agent/tasks/2026-07-29-saxs-static-temperature-detector-figure.md`
- `docs/superpowers/specs/2026-07-29-saxs-static-temperature-detector-figure-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-static-temperature-detector-figure.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, GUI/editor drafts, release packet files, and all
other untracked or parallel files remain outside this checkpoint.

## Known limitations

This Figure projection describes only the deterministic sampled image pixels.
It is not detector validation, geometry calibration, orientation acceptance,
or publication readiness. Existing physical and human-review gates remain
authoritative.

## Verification evidence

- TDD RED: `2 failed, 2 passed in 0.38s`; both failures were the expected
  missing `saxs.*.detector.2d` definitions.
- Focused detector/static/temperature Figure and 2D consumer matrix:
  `81 passed` with exit code `0`.
- Structured verifier exited `0`; task card, memory, Ruff, compile, type
  baseline, quality `287 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Fresh exact SAXS matrix using PowerShell-expanded `test_saxs_*.py` paths:
  `563 passed, 6 warnings in 333.12s`, exit code `0`. Warnings were the
  existing Arial glyph and EDF geometry-header warnings.
- Storage report/clean were non-mutating dry-runs: 14 legacy artifacts,
  15,746 eligible bytes, 8 eligible entries, 6 younger entries, and
  `removed=0`; `test_storage.py --apply` was not run.
- `git diff --check` exited `0`. The explicit allowlist checkpoint is created
  by the task commit; its hash is reported in the handoff.
