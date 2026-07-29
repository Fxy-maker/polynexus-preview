# SAXS Scientific Review Scopes Design

Date: 2026-07-29
Status: approved for implementation after user selected the two-scope design
Parent goal: the PolyNexus SAXS quality and analysis system

## Goal

Extend the shared immutable `ScientificReviewRecord` contract with two
independent SAXS reviewer-owned scopes: `saxs.1d` for sequence/metric
interpretation and `saxs.2d` for detector/geometry/orientation applicability.
This slice establishes only the schema and fail-closed validation boundary.

## Non-goals

- Do not change SAXS formulas, fitting windows, quality thresholds, physical
  gates, `QualityLevel`, publication roles, or AI/rescue behavior.
- Do not infer reviewer values from existing SAXS evidence.
- Do not attach records to engine results or change Workbench, Figure,
  Manifest, Export, or GUI behavior in this slice.
- Do not promote a diagnostic or unusable result merely because a record is
  structurally accepted; consumer-specific promotion gates are later tasks.
- Do not modify real datasets, generated outputs, scratch directories, or
  unrelated GUI changes.

## Contract

The existing frozen record, JSON-safe serializer, and pure promotion decision
remain the only implementation mechanism. The new scope names and required
decision keys are:

| Scope | Required reviewer-owned decisions |
| --- | --- |
| `saxs.1d` | `sequence_axis_policy`, `frame_identity_policy`, `missing_repeat_policy`, `metric_claim_scope`, `promotion_rule` |
| `saxs.2d` | `geometry_reference`, `beam_center_policy`, `mask_policy`, `saturation_policy`, `orientation_applicability`, `promotion_rule` |

Decision values are opaque JSON-safe reviewer values. The contract validates
presence, not scientific meaning. A pending record may omit decisions so it
can be created before review. Every non-pending record must contain every key
for its scope, plus reviewer, date, policy version, and source references.

Only an `accepted` record with matching scope and source reference can return
`allowed=True`. Pending, conditional, rejected, stale, malformed, missing,
scope-mismatched, or source-mismatched records remain denied with the existing
stable fail-closed reasons.

## Boundary behavior

The scope names are independent. An accepted `saxs.1d` record cannot satisfy a
`saxs.2d` request, and vice versa. Existing scopes and their required keys are
unchanged. Since no engine consumer is changed, all current SAXS scientific
acceptance and publication decisions remain exactly as before.

## Verification

- Focused tests prove both scope schemas, pending omission, accepted complete
  records, and cross-scope denial.
- Existing shared review tests remain green.
- The structured verifier and exact SAXS test-file matrix are run before the
  checkpoint.
- The checkpoint uses an explicit allowlist and excludes all pre-existing
  GUI, memory `current-state.md`, scratch, and storage directories.

## Follow-up boundary

Later tasks may consume `saxs.1d` and `saxs.2d` records only after their
consumer-specific promotion semantics and evidence source bindings are
specified. This schema task does not authorize those changes.
