# SAXS 1D reviewer evidence binding for static and strain design

## Goal

Extend the existing `saxs.1d` reviewer evidence snapshot from the temperature
Figure provider to static and strain 1D Figure providers, using exactly the
same source-matching and fail-closed contract.

## Design

Static and strain providers will read the already optional
`SAXSConfig.scientific_review` mapping through `configured_saxs_1d_review()`
and pass it to the existing `attach_saxs_figure_evidence()` boundary. The
projection in `figure_evidence.py` remains the sole implementation of review
restoration, source matching, detached JSON-safe serialization, and aggregate
decision reasons.

The source set is the provider's existing frame sequence. Static one-frame and
static batch paths bind in loaded frame order; strain binds in its existing
frame order. Each frame may match only an already-emitted `source_path`,
`data_quality_report.raw_data_ref`, or `data_quality_report.source_id`.
Accepted review evidence requires every emitted frame to match. No source,
frame, condition, or reviewer decision is inferred.

## Safety boundary

This task does not change `QualityLevel`, Guinier/Porod/Kratky/invariant/
lamellar values, detector/orientation behavior, quality gates, AI/rescue,
Figure publication roles, Workbench text, Manifest, Export, or `saxs.2d`.
The review snapshot is evidence only; it never promotes a Figure or result.

## Acceptance

- Static and strain Figure provenance includes the same strict-JSON review
  snapshot when the config exposes the payload.
- Missing, malformed, pending, wrong-scope, and partial-source records remain
  fail-closed with the shared reasons.
- Existing static/strain role and source-index/position assertions remain
  unchanged.
- Temperature behavior remains covered by the previous task and does not
  receive a second implementation path.
- The task has fresh RED/GREEN, exact SAXS, structured verifier, diff, storage
  dry-run, and explicit allowlist evidence.
