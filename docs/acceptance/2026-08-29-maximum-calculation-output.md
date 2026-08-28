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

## Group table checkpoint

`polynexus.core.project_workflow.result_table` now provides a shared
`ResultTableRow`/`GroupResultTable` DTO. It preserves one row per selected source
file and computes count, population standard deviation, mean, and CV separately
for each exact condition value. Mixed techniques or condition axes are rejected;
different values on the same axis remain separate groups rather than being
averaged. JSON and flat CSV-row projections retain source row IDs.

Focused group-table coverage: **3 passed**.

## Six-sample replay coverage (read-only)

The existing six-sample replay at
`D:\PolyNexus-six-sample-replay-20260827-v007` was inspected without rerunning
providers or modifying its raw directory. Across persisted run manifests, the
status inventory is **52 `review_required`, 1 `blocked`, and 1 `failed`**. The
reviewable steps contain non-empty result parameters in every case:

| Technique | Persisted steps | Inventory leaves |
| --- | ---: | ---: |
| DSC | 22 | 1,436 (1,370 scalar, 44 series, 22 object) |
| FTIR/IR | 246 | 14,760 scalar |
| SAXS | 6 | 1,500 (1,272 scalar, 222 series, 6 object) |
| WAXS | 6 | 30 scalar |

The stored replay does not include NMR steps. The one failed and one blocked
status are preserved as existing replay findings and require a separate
scientific/provider investigation; this audit does not relabel them.

This is a coverage replay of persisted public results, not a fresh provider
rerun. A fresh six-sample rerun remains optional because it is expensive and
would rewrite external generated outputs.

## Shared result-table closure

The shared `GroupResultTable` DTO is consumable by both result entry points.
The GUI adapter presents per-file rows, condition-scoped statistics, and
warning diagnostics while retaining source row IDs. The project-workflow CLI
projection exposes the same DTO under `analysis.result_tables`; no values are
recalculated or inferred by either consumer.

Verification: 91 focused tests passed (3 skipped); task verification passed
quality 313 and preprocessing 157, with Ruff, compile, and whitespace checks
green.
