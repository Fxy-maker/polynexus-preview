# SAXS 2D Evidence Mode Propagation Design

**Date:** 2026-07-27
**Status:** Approved for implementation as the next Goal atomic task
**Goal:** Carry existing detector-quality and orientation evidence through static, temperature, and strain SAXS modes without inventing 2D data or changing scientific algorithms.

## Scope

The existing 2D contract already produces JSON-safe `detector_quality_report`
and `orientation_evidence` fields on `AnisotropyResult`. This task closes the
transport boundary from an existing result object to frame/point DTOs, mode
summaries, Workbench diagnostics, persisted history parameters, and the
reproducible export bundle.

The recommended approach is a shared transport helper. The helper deep-copies
the existing evidence fields and never interprets, repairs, recalculates, or
promotes them. Static batches and condition series use conservative summaries
that preserve missing-frame counts and source reason codes.

## Alternatives considered

1. Patch each mode independently. This minimizes the first edit but duplicates
   the contract and makes static/temperature/strain behavior drift.
2. Use one shared transport helper and add mode-specific summary builders.
   This reuses the existing 1D transport boundary while keeping detector and
   orientation semantics separate. This is the selected approach.
3. Replace all quality fields with a new generic 2D DTO. This would require a
   broad compatibility migration and is outside the current atomic task.

## Data contract

`SAXSResult`, `TemperaturePointResult`, and `StrainPointResult` may carry:

- `detector_quality_report`: the existing detector/sector-map report;
- `orientation_evidence`: the existing orientation metric evidence.

The shared copy helper includes these fields alongside the existing 1D quality
fields. Copies are deep copies, so GUI, history, and export consumers cannot
mutate analysis objects through a parameters payload.

For a mode summary, each field is present only when at least one frame supplies
that evidence. A summary records frame count, evidence coverage, level counts,
conservative level, applicability, source reference, source reason codes, and
detector source kinds where available. Missing frames remain missing; partial
coverage is Diagnostic. Orientation remains a separately named top-level
`orientation_evidence` summary and is never folded into generic 1D
`metric_evidence` or interpreted as a material mechanism.

When no 2D evidence exists, no synthetic summary is emitted. This preserves
the distinction between “not supplied” and “supplied but unusable”.

## Mode behavior

- Static single frame: transport the two fields unchanged when present.
- Static batch: attach fields to the corresponding frame row and aggregate
  each field without creating a temperature or strain trend.
- Temperature: copy evidence from each successful `SAXSResult` into the
  corresponding `TemperaturePointResult`; aggregate by source index so the
  temperature sort cannot misalign evidence.
- Strain: copy evidence into each `StrainPointResult` and aggregate by point
  order. Existing `sector_data_list` behavior is untouched.
- Workbench: existing nested-diagnostic rendering displays the two non-scalar
  fields in the Diagnostics section. The review risk/next text remains driven
  by the established 1D metric evidence and does not turn orientation into a
  generic trend claim.
- History: the existing parameters persistence path stores the copied fields
  without a second interpretation layer.
- Export: `quality_evidence.json` includes the fields at mode and frame level;
  static batch summaries use the same conservative aggregation as parameters.

## Error and safety behavior

No 2D calculation is invoked by this task. An absent, malformed, or failed
upstream result yields an absent field or an explicitly downgraded summary;
the 1D result and legacy numeric orientation fields remain intact. All new
payloads must pass strict `json.dumps(..., allow_nan=False)` through the
existing export conversion.

## Verification

The task must first add focused RED tests for shared copying, partial static
batch aggregation, temperature source-index alignment, strain propagation,
Workbench diagnostics, history persistence, and export provenance. Then run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_2d_propagation'
python -m pytest tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-2d-evidence-propagation.md --changed --types
```
