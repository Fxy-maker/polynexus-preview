# SAXS Series Metric Source-Index Integrity Design

## Goal

Extend the existing series-level Porod, Kratky, invariant, and lamellar
evidence summary with the same conservative source-index integrity facts that
already protect the temperature Guinier sequence.

## Design

`build_series_metric_evidence()` remains an observational aggregator. When a
caller supplies `frame_source_indices`, it validates the supplied positions
against the existing frame count and records detached position lists for
invalid and duplicate indices. A valid integer mapping may be out of order;
that state is recorded as `source_index_order_reordered` and does not lower the
claim level. A length mismatch, invalid value (negative, non-integral, boolean,
non-finite, or non-coercible), or duplicate makes the affected metric summary
`Diagnostic` when usable metric evidence exists, and adds a stable reason code.
No source index is invented or repaired.

When no source mapping is supplied, the existing static and strain behavior is
unchanged. Condition-axis validation, metric values, frame positions, and
existing quality levels remain independent. The new fields are additive,
strict-JSON-safe, detached through `MetricEvidenceSummary`, and round-trip
through `from_dict()`.

## Safety boundary

This slice does not sort frames, recalculate Porod/Kratky/invariant/lamellar
values, add physical thresholds, interpolate, fill missing frames, invoke AI,
apply rescue candidates, or alter Figure/Manifest/Export role decisions. It
only prevents an invalid frame identity mapping from carrying a Trend claim.

## Acceptance

- Valid reordered source indices remain visible and keep the existing Trend
  aggregation behavior.
- Duplicate, invalid, and length-mismatched source mappings are explicit and
  cap a usable metric summary at Diagnostic.
- Missing source mappings remain unchanged and do not generate warnings.
- All new payloads serialize with `json.dumps(..., allow_nan=False)` and survive
  `MetricEvidenceSummary.from_dict()`.
- Focused RED/GREEN, task verification, SAXS matrix, storage dry-run, and an
  explicit allowlist checkpoint are recorded.
