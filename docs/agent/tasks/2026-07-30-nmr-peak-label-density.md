---
task_id: 2026-07-30-nmr-peak-label-density
kind: gui-scientific-presentation
status: completed
date: 2026-07-30
title: Keep dense NMR peak labels readable
---

# NMR peak label density

## Goal

Improve NMR spectrum Editor readability when many peaks are close together,
without hiding measured peak lines or changing scientific assignment and Xc
contracts.

## Non-goals

- Do not change peak detection, deconvolution, assignment, calibration, or Xc.
- Do not discard peak data or assignment rows.
- Do not reinterpret the solid-C assignment-limited policy.
- Do not touch SAXS code, tests, data, or temporary directories.

## Affected boundaries

- `polynexus/core/nmr_engine/figure_provider.py`: display-only label cap and
  recipe provenance.
- `tests/test_nmr_figure_provider.py`: assert all peak lines remain while
  dense canvas labels are capped.
- NMR task/acceptance evidence and the focused verification checkpoint.

## Implementation plan

1. Add a RED regression with more peaks than the canvas label budget.
2. Keep every peak line and assignment row, while limiting only rotated ppm
   labels to the most prominent peaks.
3. Record the label policy in the figure recipe and verify NMR lifecycle,
   figure, Results Workbench, and native Editor routes.
4. Create one explicit changed-file allowlist checkpoint.

## Acceptance criteria

- [x] Dense spectra have a bounded number of rotated canvas ppm labels.
- [x] Every input peak still has a vertical marker and remains available in
  assignment/data consumers.
- [x] The figure recipe records the display-only label limit.
- [x] Scientific assignment, Xc, publication role, and source provenance are
  unchanged.
- [x] Focused tests, task verifier, and native Editor evidence pass.

## Verification

```powershell
python -m pytest -q tests/test_nmr_figure_provider.py tests/test_nmr_engine.py
python -m pytest -q tests/test_native_gui_real_route_capture.py -k 'nmr.solid_c'
python scripts/verify.py --task docs/agent/tasks/2026-07-30-nmr-peak-label-density.md --changed --types
git diff --check
```

## Evidence

- TDD RED: the dense-peak regression observed `16` canvas labels instead of
  the intended display budget.
- NMR figure provider: `7 passed`.
- NMR engine/evidence slice: `32 passed, 129 deselected`.
- Results table/Joint provenance slice: `27 passed`.
- Native Windows Qt `nmr.solid_c`: `1 passed, 16 deselected in 21.63s`, exit
  `0`; capture root:
  `D:\PolyNexus_native_nmr_label_density_20260730`.
- The recipe records `peak_label_limit=10`; all peak lines and assignment rows
  remain present. Scientific review remains `review_missing` for the native
  fixture and no solid-C conclusion was promoted.

## Explicit changed-file allowlist

- `polynexus/core/nmr_engine/figure_provider.py`
- `tests/test_nmr_figure_provider.py`
- this task card
- `docs/acceptance/2026-07-30-nmr-peak-label-density.md`
