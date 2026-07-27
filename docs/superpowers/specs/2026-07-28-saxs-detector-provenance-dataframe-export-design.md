# SAXS Detector Provenance DataFrame and CSV Export Design

**Date:** 2026-07-28
**Status:** Implemented; checkpointed at `4d09085`
**Related task:** `docs/agent/tasks/2026-07-28-saxs-detector-provenance-dataframe-export.md`

## Goal

Make per-frame detector provenance visible in tabular exports while retaining
the nested quality report as the authoritative evidence contract.

## Design

Add `_detector_provenance_csv_fields(report)` to the existing SAXS output helper
module. It returns a stable mapping with these keys:

```text
Detector_source_kind
Detector_quality_level
Detector_reason_codes
Geometry_provenance_source
Geometry_field_sources
Geometry_provenance_validity
Mask_provenance_source
Mask_configured
Mask_shape
Mask_provenance_validity
```

The geometry field-source string is sorted by field name and joined as
`field:source|...`; the mask shape is `heightxwidth` only for a two-item shape,
otherwise empty/None. Missing reports return the same keys with None values.
No status is inferred from the values. `not_assessed` is copied literally.

Temperature and strain `to_dataframe()` merge these fields into each existing
row using that point's already aligned raw-detector report. Static
`_result_to_params_dict()` merges the same fields for the parameter CSV. This
does not change `quality_evidence.json`, row ordering, source indices, or any
quality level.

## Verification

Tests cover populated and missing reports, deterministic ordering, strict
literal validity, temperature/strain row alignment, static CSV projection, and
existing mode-evidence regressions. The exact SAXS matrix and structured task
verifier are required before the explicit checkpoint.
