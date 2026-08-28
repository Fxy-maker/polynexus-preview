# Maximum deterministic calculation output — inventory checkpoint

## Purpose

This checkpoint records what the current Core exposes before group-table work.
It is an output-coverage audit, not a scientific promotion decision.

## Current inventory boundary

`ComputeResult.field_inventory()` and serialized
`ComputeRun.to_dict()["result"]["field_inventory"]` now enumerate every metric
leaf already emitted by a provider. Scalar values are preserved, series are
identified with their item count, nested paths are explicit, and declared
missing fields can be represented without fabricating values. Units and
scientific meaning are intentionally not inferred by this inventory.

## Technique coverage map

| Technique | Existing deterministic outputs observed | Current shared visibility | Remaining gap |
| --- | --- | --- | --- |
| DSC | Thermal events, Tg/Tm/Tc, enthalpy, crystallinity when reference is supplied, multi-peak and isothermal/non-isothermal kinetics | Provider parameters plus new field inventory | Add an explicit stable field catalog and group statistics |
| FTIR | Spectrum, peak detection/fitting, band/index metrics, temperature-2D and mapping outputs | Provider parameters, canonical capabilities, new field inventory | Standardize field metadata and group statistics; material assignment remains AI/human scope |
| SAXS | Profile/structure metrics, Guinier/Porod/Kratky/invariant/lamellar, temperature/strain/orientation diagnostics | Provider parameters, metric evidence, new field inventory | Standardize all nested metrics and group statistics; calibration/applicability remain warnings/evidence limits |
| WAXS | Peaks, crystallinity, Scherrer/W-H and temperature/strain outputs | Provider parameters, evidence projection, new field inventory | Standardize all nested metrics and group statistics; physical support remains an evidence limit |
| NMR | Peak count/area/FWHM/SNR, generic regions, solid 13C phase/Xc when supported, existing relaxation/computed-shift helpers | Provider parameters and new field inventory | Relaxation/computed-shift routes are not yet unified as shared capabilities; ARS writing projection is deferred |

## Contract tests

- `tests/test_result_field_inventory.py` verifies scalar, series, nested, and
  explicitly missing fields.
- `tests/test_compute_service.py::test_compute_run_serializes_result_field_inventory`
  verifies the field inventory is visible in the shared serialized `ComputeRun`.
- Focused result/ComputeRun matrix: **49 passed, 3 skipped**.

## Boundary

This inventory does not calculate new scientific quantities and does not infer
units, material identity, grouping, literature assignments, or manuscript use.
The next checkpoint adds explicit condition-scoped per-file/group tables over
these already emitted values.
