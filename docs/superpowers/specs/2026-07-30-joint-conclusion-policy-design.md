# Joint Conclusion Policy Design

Date: 2026-07-30
Status: approved conservative implementation boundary
Scope: non-SAXS Joint report semantics only

## Decision

Joint reports expose a JSON-safe `joint_conclusion` classification derived
from the existing reviewer record status and existing validation severities.
The implementation does not interpret the text of reviewer policy decisions.
It preserves `conflict_precedence`, `minimum_evidence`, and
`unresolved_conflict_policy` as reviewer-owned provenance.

## Classification

- `review_required`: the Joint review is missing, invalid, source-mismatched,
  pending, or otherwise not accepted.
- `rejected`: a valid reviewer record is rejected.
- `blocked`: an accepted review exists, but an existing Joint validation or
  technique-confidence issue is `ERROR`.
- `conditional`: an accepted review exists, but an existing issue is `WARN`,
  or the reviewer status is explicitly conditional.
- `accepted`: every selected row has an accepted, source-matching review and
  no existing Joint warning/error issue is present.

Only `accepted` has `allowed=true`. This new projection does not alter the
existing `scientific_review` promotion snapshot, validation formulas, severity
thresholds, figure roles, or numerical results. It is a conclusion/status
surface for Results, History, Export, and future release consumers.

## Provenance

The projection carries each valid row review's record id, batch source ref,
status, policy version, and the three exact Joint policy decision strings. If a
review is absent or invalid, no policy text is invented.

## Failure behavior

Missing/invalid review remains fail-closed as `review_required`. An `ERROR`
cannot be rescued by an accepted review and becomes `blocked`; a `WARN` becomes
`conditional`. Existing source-specific values and conflict rows remain
visible.
