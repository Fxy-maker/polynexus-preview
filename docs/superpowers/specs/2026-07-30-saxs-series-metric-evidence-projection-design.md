# SAXS Series Metric Evidence Projection Design

## Goal

Keep the existing SAXS series metric source-index integrity facts visible in
Figure/Manifest provenance while preserving the authoritative Export payload.

## Design

Extend the existing `_COMMON_EVIDENCE_FIELDS` allowlist in
`figure_evidence.py` with the three already-defined
`MetricEvidenceSummary` fields:

- `duplicate_source_index_indices`
- `invalid_source_index_indices`
- `source_index_order_reordered`

The projection remains detached, read-only, and strict-JSON-safe through the
existing `_project_mapping()` path. Export remains on its existing
`_quality_object_payload()` and `_jsonable()` path; no second serializer or
consumer-specific reconstruction is added.

## Safety boundary

This is a transport-only change. It does not recalculate metrics, alter
quality levels, add thresholds, sort or repair frames, interpolate, invoke AI,
apply rescue candidates, or change publication roles. Unknown evidence fields
remain excluded by the existing explicit allowlists.

## Acceptance

- Figure evidence preserves the three source-index fields for a series metric.
- Manifest-backed Figure provenance carries the same detached projection.
- `quality_evidence.json` continues to preserve the same fields through Export.
- Projection outputs remain strict JSON-safe and do not mutate source mappings.
- Existing field filtering and all SAXS scientific semantics remain unchanged.
