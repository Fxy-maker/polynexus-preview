# SAXS 2D reviewer evidence binding design

## Goal

Bind the existing reviewer-owned `saxs.2d` record to detector and orientation
Figure provenance while preserving the already implemented `saxs.1d` binding.

## Design

Reuse the existing `SAXSConfig.scientific_review` payload and source candidates
already emitted by each `SAXSFrameView`: `source_path`,
`data_quality_report.raw_data_ref`, and `data_quality_report.source_id`.
The shared Figure evidence attachment will build two detached snapshots when a
provider emits both kinds of Figure:

- ordinary 1D Figures use expected scope `saxs.1d`;
- detector/2D/orientation Figures use expected scope `saxs.2d`.

Scope selection is based only on the existing Figure recipe capability and
stable detector/orientation Figure IDs. A review record is accepted only when
the existing record validator, expected scope, status, and every supplied
source match. Missing, malformed, pending, wrong-scope, and partial-source
records remain fail-closed.

## Safety boundary

This is provenance-only. It does not alter detector arrays, masks, geometry,
orientation metrics, 1D metrics, quality levels, physical gates, publication
roles, AI/rescue, Workbench text, Manifest, or Export behavior. No source,
frame, geometry value, or reviewer decision is inferred.

## Acceptance

- A matching accepted `saxs.2d` payload appears on 2D Figure provenance.
- The same payload is a visible scope mismatch on ordinary 1D Figure
  provenance, rather than being interpreted as a 1D decision.
- Partial source matches and missing/invalid records remain fail-closed.
- Existing `saxs.1d` binding and all Figure roles remain unchanged.
- Strict JSON, focused tests, structured verification, SAXS matrix, storage
  dry-run, and an explicit allowlist checkpoint are recorded.
