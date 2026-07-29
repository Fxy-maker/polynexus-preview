# SAXS 1D reviewer evidence binding design

## Goal

Consume an explicitly supplied `saxs.1d` reviewer record at the existing
temperature 1D Figure-evidence boundary, preserving a detached, fail-closed
review snapshot without changing scientific analysis or publication behavior.

## Input and source binding

`SAXSConfig.scientific_review` is an optional serialized
`ScientificReviewRecord` payload. The consumer restores it through the shared
`review_record_from_payload()` contract. It does not infer reviewer decisions
from Guinier values or other evidence.

For each existing temperature frame, source candidates are taken in this
order, only when already emitted and non-empty: `SAXSFrameView.source_path`,
`data_quality_report.raw_data_ref`, and `data_quality_report.source_id`. The
record must be accepted for every frame in the sequence. A frame with no
available source candidate cannot be promoted by a record for another frame.
No path, source ID, frame, or run-level reference is fabricated.

## Evidence contract

The existing `quality_provenance` payload gains a detached `scientific_review`
mapping containing the shared decision reason, record ID, scope, policy
version, observed source references, and per-frame binding decisions. The
aggregate `allowed` value is true only when the record is structurally valid,
has scope `saxs.1d`, status `accepted`, matches every existing frame source,
and no frame is unbound. Missing, malformed, pending, wrong-scope, or
source-mismatched records remain diagnostic evidence with the shared
fail-closed reasons.

## Explicit safety boundary

This slice is evidence-only. It does not alter `QualityLevel`, Guinier/Rg
values, sequence evidence, physical checks, AI candidates, rescue behavior,
Figure publication roles, or result validation. Static and strain consumers,
`saxs.2d`, GUI review hints, and test storage are outside this slice.

## Verification boundary

TDD covers accepted matching records, missing/invalid/source-mismatch states,
temperature source-index ordering, and preservation of existing Figure roles.
The structured verifier and exact SAXS matrix are required before the explicit
allowlist checkpoint. Storage inspection remains report/clean dry-run only.
