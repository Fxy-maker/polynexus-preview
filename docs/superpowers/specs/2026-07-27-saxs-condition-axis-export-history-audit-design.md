# SAXS condition-axis Export/History boundary audit design

## Decision

Treat the existing `MetricEvidenceSummary.condition_axis` mapping as opaque
provenance at Export and History boundaries. The boundaries may normalize it to
strict JSON, but must not sort values, fill positions, infer a transition, or
change its quality level.

The export path remains authoritative through
`quality_evidence.json`. History keeps the same evidence in the existing
`parameters.metric_evidence` field and the nested result payload; no schema
migration is needed.

If a public quality DTO is supplied directly to the generic History JSON
normalizer, it must use its existing `to_dict()` method. This is transport
normalization, not a new scientific interpretation.

## Evidence shape

The regression uses an axis with finite values, a missing value represented by
`None`, source/frame positions, and an explicit diagnostic defect. Assertions
compare the full axis mapping and verify the caller's input remains unchanged.

## Safety boundary

Existing physical gates and usability levels remain the authority. A diagnostic
or empty axis is evidence for review only; this task cannot rescue a frame or
authorize a figure.
