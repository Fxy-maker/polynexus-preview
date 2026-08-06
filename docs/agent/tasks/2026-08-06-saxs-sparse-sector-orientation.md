# SAXS Sparse Sector Orientation Recovery

## Goal

Allow valid sparse 2D sector maps from real EDF detector geometry to reach
Herman/anistropy analysis without treating unsupported bins as measured data.

## Non-goals

- Do not fill unsupported bins with fabricated intensity values.
- Do not relax validation for non-finite values in supported bins.
- Do not alter orientation thresholds, detector quality gates, or real datasets.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_anisotropy.py`: support-aware input and
  azimuthal weighting.
- `polynexus/core/saxs_engine/saxs_strain.py`: canonical sector validation.
- `tests/test_saxs_sparse_sector_orientation.py`: regression coverage.

## Acceptance

- A sector map with NaN only where support is zero produces finite raw Herman
  evidence when the annulus is supported.
- A sector map with NaN in a supported bin remains unusable.
- Existing SAXS tests and `python scripts/verify.py --changed --types` pass.

## Acceptance criteria

- [x] Sparse EDF sector maps preserve finite Herman raw evidence when NaN
  occurs only in zero-support bins.
- [x] Non-finite values in supported bins remain fail-closed.
- [x] Existing SAXS quality and orientation tests remain green.

## Implementation plan

1. Add a failing regression for sparse sector maps and supported-bin corruption.
2. Make canonical sector and anisotropy validation support-aware.
3. Prevent NaN multiplied by zero from contaminating azimuthal weighting.
4. Run focused tests, real EDF reproduction, and the structured verifier.

## Verification

```powershell
pytest -q tests/test_saxs_sparse_sector_orientation.py
pytest -q tests/test_saxs_preprocess.py tests/test_saxs_batch_parameters.py tests/test_saxs_strain_sector_fail_closed.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_results_table_service.py
python scripts/verify.py --task docs/agent/tasks/2026-08-06-saxs-sparse-sector-orientation.md --changed --types
```

## Implementation status

- [x] TDD RED: sparse unsupported-bin regression failed before the fix.
- [x] GREEN: sparse and supported-nonfinite regressions pass; adjacent SAXS
  matrix is `109 passed`.
- [x] Real EDF reproduction reaches `analyze_anisotropy` and reports
  `f_Herman_raw_mean=0.4729`; effective Herman remains gated when reliability
  or tensile-axis evidence is unavailable.
- [x] Structured verifier passes task check, Ruff, compile, quality `297`,
  preprocessing `107`, type baseline, and whitespace checks.
