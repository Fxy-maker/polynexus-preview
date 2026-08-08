# SAXS Orientation Evidence Projection

## Goal

Expose the per-frame detector-plane orientation evidence used to produce
`f_Herman_raw`, so equal-looking values can be audited against the consumed
axis, harmonic strength, q annulus, and azimuthal support.

## Non-goals

- Do not change the Herman formula, q-window selection, or effective tensile-axis gate.
- Do not promote detector-plane diagnostics to a publication-ready 3D orientation.
- Do not infer missing raw 2D data from `results_table.tsv`.
- No push, merge, deployment, or source-data mutation.

## Affected boundaries

- `saxs_anisotropy` orientation result/evidence contract.
- SAXS strain `_batch_data` frame DTO construction.
- SAXS result-table diagnostic projection.
- Focused regression tests and durable memory.

## Acceptance criteria

- [x] Each strain frame carries axis degree/source, harmonic strength and significance,
      effective bins, azimuthal coverage, cosine-squared average, and isotropic baseline
      when present; missing values remain explicit `None`.
- [x] The evidence contract serializes `orientation_cos2_avg` without changing
      reliability classification.
- [x] The GUI Diagnostics section includes the new scalar fields while the primary
      table contract remains unchanged.
- [x] Existing orientation, batch, and result-table regression tests pass.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py tests/test_saxs_q_resolved_orientation_reliability.py
python scripts/verify.py --changed --types
git diff --check
```

## Scientific review boundary

The fields are provenance/diagnostic evidence only. A reviewer must still
inspect the original 2D detector sectors and tensile-axis calibration before
using them for a scientific conclusion.
