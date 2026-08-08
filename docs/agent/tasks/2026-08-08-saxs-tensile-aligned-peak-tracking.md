---
task_id: 2026-08-08-saxs-tensile-aligned-peak-tracking
kind: scientific
status: checkpointed
date: 2026-08-08
title: Track SAXS long-period peaks along the configured tensile axis
---

# SAXS Tensile-Aligned Peak Tracking

## Goal

Track and expose lamellar q/L peaks along the configured tensile axis and its
transverse direction so directional changes are not hidden by the total-profile
long period.

## Non-goals

- Do not replace or reinterpret legacy total `L_nm`.
- Do not infer tensile axis from a principal scattering axis.
- Do not change Herman formula or reliability gates.
- No calibration inference, publication promotion, push, merge, or deployment.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_results_table_service.py`
- Task design, plan, and durable agent-memory records.

## Implementation plan

1. Lock the directional q/L and fail-closed contracts with synthetic tests.
2. Build support-aware tensile/transverse profiles from canonical 2D sectors,
   preserving fixed-sector preprocessing and finite chi-bin width.
3. Transport the diagnostic values through batch DTOs and Diagnostics without
   changing the primary results table.
4. Verify synthetic, real-EDF smoke, focused regression, and changed files.

## Acceptance criteria

- [x] Canonical 2D synthetic data with distinct axial/transverse peaks yields
  distinct aligned q/L fields.
- [x] Missing tensile axis or canonical 2D support fails closed for aligned fields.
- [x] Existing total and fixed detector-sector outputs remain unchanged.
- [x] GUI Diagnostics exposes aligned fields without expanding the primary table.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py tests/test_saxs_feature_orientation_foundation.py
python scripts/verify.py --changed --types
git diff --check
```

## Implementation evidence

- The existing total peak and fixed meridional/equatorial peaks remain intact.
- New tensile/transverse fields are diagnostics-only and require a finite
  configured axis plus canonical 2D intensity, q, chi, and support arrays.
- Canonical chi boundary bins use fractional angular-overlap weights. Exact
  fixed-sector matches reuse the already normalized/smoothed legacy profile;
  arbitrary sectors apply the same normalization/smoothing stages.
- Focused SAXS batch/results/orientation matrix: `175 passed` after review
  repairs; final rerun is part of the checkpoint gate.
- Independent scientific/code review closed with `0 Critical / 0 Important`.
- Final post-review structured changed/type verifier passed quality `297`,
  preprocessing `157`, Ruff, compile, task/memory validation, and whitespace.
- Real EDF smoke data under the external user dataset was read-only. With
  `tensile_axis_deg=90` and `q_bragg_max=1.0`, tensile q/L matched meridional
  q/L and transverse q/L matched equatorial q/L on all five frames.

## Review repairs

- Reject non-positive/non-monotonic q axes and noncanonical chi range, order,
  uniqueness, or spacing before any fixed-sector shortcut.
- Reject missing, Boolean, complex, string, object, malformed, negative, or
  non-finite support; positive support over non-finite intensity also fails
  closed.
- Require at least five supported q bins inside the configured Bragg search
  window before reusing a fixed profile.
- Use exact bin/sector interval intersection so coarse 8/10-bin chi maps retain
  the requested pi-periodic angular width.
- Preserve configured axis metadata and report `sector_data_missing` when the
  per-frame sector payload is absent.

Scientific review remains required before treating aligned peaks as publication
results; the configured tensile-axis convention is detector-image clockwise
degrees and must be verified against beamline geometry.

## Pre-existing workspace state

The worktree was clean when this atomic task started. No external dataset or
unrelated repository file was modified.
