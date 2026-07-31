# SAXS 2D Review Context Projection Design

## Goal

Expose a detached, strict-JSON reviewer context for existing SAXS 2D detector
and orientation evidence. The context is an evidence transport DTO; it does
not calculate, repair, classify, promote, or approve scientific results.

## Boundary

The adapter accepts an existing SAXS result, engine wrapper, or parameters
mapping and reads only already-emitted fields. It may project:

- detector quality level, source kind, shape/count summaries, coverage,
  saturation availability, beam-center availability, reason codes, and the
  existing geometry/mask provenance;
- orientation metric level, applicability, fit evidence, physical checks, and
  reason codes;
- the existing scientific acceptance audit summary and its physical/method
  gate evidence;
- an existing `ScientificReviewRecord` or serialized review decision for the
  `saxs.2d` scope, including the existing scope/source-match reason.

The output excludes q/I arrays, detector pixels, source paths, file contents,
and unknown prompt or analysis fields. It is detached and serializable with
`json.dumps(..., allow_nan=False)`.

## Contract

The public helper is:

```python
build_saxs_2d_review_context(
    source: Any,
    *,
    source_ref: str = "",
    scientific_review: Any = None,
) -> dict[str, Any]
```

The returned envelope has `schema_version="saxs-2d-review-v1"`,
`technique="SAXS"`, `scope="saxs.2d"`, `status`, `reason_codes`,
`detector`, `geometry`, `mask`, `beam_center`, `orientation`, `gates`, and
`scientific_review` fields. Missing evidence is represented as unavailable or
`not_assessed` with reason codes. Existing `Diagnostic` and `Unusable` levels
remain unchanged and can only lower the envelope status.

The helper never raises for malformed optional evidence. A malformed review
record is represented as `review_invalid`; a missing record is
`review_missing`; a wrong scope or source is preserved as
`scope_mismatch`/`source_mismatch`. The helper never turns an accepted review
into a publication or Figure role decision.

## Workbench boundary

`build_saxs_results_presentation()` adds the DTO under a new
`saxs_2d_review_context` field on `ResultsTablePresentation`. Existing risk,
next-step, table, and scientific-review text generation remains unchanged.
The GUI consumes the DTO as presentation data and does not branch on SAXS
algorithm internals.

## Non-goals

- no detector geometry, mask, beam-center, orientation, q, or intensity
  calculation;
- no new physical threshold, quality threshold, interpolation, imputation,
  frame repair, or source inference;
- no AI call, candidate generation, rescue, rerun, config mutation, or
  publication authorization;
- no change to Figure, Manifest, Export, History, or existing review
  persistence semantics;
- no edit to real data, generated output, storage artifacts, or parallel
  memory/worktree files.

## Verification design

Tests cover complete evidence, missing/not-assessed evidence, Diagnostic and
Unusable degradation, accepted review, scope/source mismatch, raw-field
exclusion, strict JSON, input immutability, and Workbench DTO compatibility.
