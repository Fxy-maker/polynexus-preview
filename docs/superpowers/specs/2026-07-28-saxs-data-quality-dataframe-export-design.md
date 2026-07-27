# SAXS Data-Quality DataFrame and CSV Export Design

**Date:** 2026-07-28
**Status:** implemented; checkpointed at `b0c63d7`
**Related task:** `docs/agent/tasks/2026-07-28-saxs-data-quality-dataframe-export.md`

## Goal

Make the existing q/I `DataQualityReport` visible in tabular exports while
keeping the nested report authoritative and preserving all current analysis
semantics.

## Contract

Add `_data_quality_csv_fields(report)` to
`polynexus/core/saxs_engine/saxs_output_helpers.py`. It returns these fixed
keys in a stable mapping:

```text
Data_quality_source_id
Data_quality_raw_data_ref
Data_quality_processed_data_ref
Data_quality_processing_config_ref
Data_quality_level
Data_quality_reason_codes
Data_quality_actions
Data_quality_low_q_truncated
Data_quality_original_point_count
Data_quality_finite_point_count
Data_quality_usable_point_count
Data_quality_invalid_point_count
Data_quality_nonfinite_q_count
Data_quality_nonpositive_q_count
Data_quality_nonfinite_intensity_count
Data_quality_nonpositive_intensity_count
Data_quality_duplicate_q_count
Data_quality_nonmonotonic_q
```

`reason_codes` and `actions` preserve their emitted order and use `|` as the
flat separator. Enum-like `level` values use their `.value` when available.
Boolean fields are copied only when they are actual booleans; missing or
malformed reports return the same keys with `None`. Numeric counts and source
references are copied, never recalculated or interpreted.

Temperature and strain `to_dataframe()` merge the fields from each point's
existing `data_quality_report`. Static `_result_to_params_dict()` merges the
fields from the result's existing report. The nested report remains untouched,
and row/frame order and all existing columns remain unchanged.

## Scientific boundary

This is a provenance projection only. It does not create a second quality
language, add thresholds, repair data, promote levels, execute rescue, or alter
figure/publication eligibility.

## Verification

Tests must cover populated reports, deterministic list ordering, literal
booleans, missing reports, row alignment, static parameter projection, strict
CSV writing, and existing SAXS mode-evidence regressions. The exact SAXS matrix
and structured task verifier are required before the explicit checkpoint.
