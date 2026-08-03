# SAXS Orientation Feature Tracking Design

**Date:** 2026-08-03
**Status:** Approved for implementation planning
**Depends on:** q-resolved orientation reliability

## Goal

Track the same neutral SAXS q-band feature across an in-situ strain sequence
and report same-feature orientation changes without assuming monotonicity or
assigning chain, lamellar, or void semantics.

## Inputs and ownership

The tracker consumes detached `QResolvedOrientationEvidence` records from Task
1 plus the existing condition-axis and source-index evidence. It does not read
detector pixels, repeat integration, choose masks, infer tensile axes, or
inspect GUI state. Scientific behavior lives in a new focused core module.

## Matching contract

Frames retain original source indices and are ordered through the existing
strain-axis integrity contract. A candidate in adjacent valid frames is
compatible only when:

- both records use the same convention and reference-axis kind;
- both records use the same normalized reference-axis value and reliability-
  policy digest;
- both retain at least three common supported q bins;
- each support-weighted q center lies inside the other candidate's q bounds;
- both local reliability states are not `unavailable`;
- principal-axis separation does not violate the existing configured axis-
  drift gate when both axes are finite.

Matching is mutual and unique. If one candidate has multiple compatible
neighbors, or two candidates claim the same neighbor, the branch is marked
`feature_match_ambiguous` and new track IDs begin. No score threshold silently
selects one ambiguous feature.

Missing frames create a gap. A track may bridge one gap only when the features
on both sides are mutually unique under the same rules; otherwise it splits.

## Sequence DTO

```text
OrientationFeatureObservation
  frame_source_index
  condition_value
  candidate_id
  q_range_nm1
  common_q_bin_ids
  q_center_nm1
  f_principal_raw
  f_reference
  delta_f_from_zero
  delta_stability_interval
  reliability_status
  reason_codes

OrientationFeatureTrack
  track_id
  feature_kind: q_band
  convention
  reference_axis_kind
  reference_axis_deg
  reliability_policy_digest
  observations
  reliability_status
  reason_codes

OrientationSequenceEvidence
  tracks
  zero_reference_source_index
  ambiguous_match_count
  split_count
  missing_frame_indices
  suspected_systematic_harmonic
  systematic_harmonic_metrics
  level
  reason_codes
```

All records are immutable, detached, and strict-JSON-safe. Frame-local Task 1
evidence remains authoritative and unchanged.

## Zero reference and delta

The zero reference is a unique finite strain satisfying the existing numeric
zero convention. If no unique zero frame exists, `delta_f_from_zero` is
unavailable with an explicit reason; the first frame is never substituted.

Delta is calculated only inside one track, with the same convention,
reference-axis kind and value, reliability policy, finite tensile axis where
final Herman is requested, and eligible local evidence. Both frames are
reaggregated from Task 1 additive harmonic terms over the exact intersection
of their ordered q-bin identities; candidate-level values over different q
bounds are never subtracted. The stability interval uses conservative
interval arithmetic from the Task 1 95-percent stability bounds and is labeled
`conservative_stability_bound`, not a paired bootstrap or measurement
confidence interval. If the exact common support or required interval terms
cannot be reconstructed, the delta or its bound remains unavailable.

## Suspected systematic component

The tracker may label a detector-coordinate harmonic as suspected when one
mutually compatible component appears in every valid frame, spans at least
half of the common supported q range, and remains within the existing axis-
drift gate. It reports persistence fraction, q coverage, axis spread, and
strength variation. It never subtracts the component or calls it confirmed.

## Failure behavior

- Ambiguous matches split rather than choose a preferred path.
- Feature switching never inherits the prior feature ID or delta baseline.
- Missing zero strain leaves delta unavailable.
- Missing tensile axis leaves final-axis delta unavailable while preserving
  principal-axis diagnostics.
- Invalid, duplicate, or incoherent frame-source indices leave sequence
  tracking unavailable; list position is never substituted as provenance.
- Artifact-sensitive local evidence remains visible but cannot yield a final
  same-feature delta.
- Diagnostic or artifact-sensitive local evidence cannot be promoted by a
  stable sequence trend.
- A lower five-percent value is permitted and described only with stability
  evidence; monotonicity is not an acceptance criterion.

## Boundaries and tests

Create a core tracker module, append evidence to strain DTOs and series
parameters, and add synthetic plus read-only real-series tests. GUI, AI,
calibration correction, physical feature assignment, and publication
promotion are outside this task.

Tests cover unique matches, crossings, splits, one-frame gaps, duplicate and
missing zero frames, condition reorder provenance, axis-reference mismatch,
interval propagation, suspected-systematic diagnostics, JSON safety, input
immutability, and the real zero/five-percent q-band comparison.

## Acceptance criteria

1. Same-feature deltas exist only for unique compatible tracks.
2. Ambiguity and feature switching fail closed with stable reason codes.
3. Zero strain is never fabricated or used as instrument background.
4. Sequence evidence cannot promote local Diagnostic or Unusable evidence.
5. Existing scalar and frame evidence remain backward compatible.

## Non-goals

- No GUI or axis editor.
- No calibration subtraction.
- No AI ranking.
- No chain, lamellar, or void assignment.
- No monotonic trend enforcement.
