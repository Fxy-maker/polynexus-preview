# Project Release Decision Design

Date: 2026-07-30
Status: approved continuation of the scientific-release boundary design
Scope: non-SAXS release workflow only

## Goal

Provide an auditable project-level release decision record for one SampleDB
batch. The record can reference the IR mapping, NMR solid-C, Joint, and shared
GUI evidence that the reviewer considered without pretending that any one
analysis run owns the final publication decision.

## Non-goals

- Do not decide IR coordinates, ROI semantics, NMR assignments, Xc policy, or
  Joint conflict precedence in software.
- Do not promote a diagnostic or assignment-limited figure automatically.
- Do not alter SAXS code, tests, evidence, or release state.
- Do not replace the existing run-scoped `ScientificReviewRecord` entries.

## Data model

The existing immutable `ScientificReviewRecord(scope="release")` remains the
public record contract. Its required decisions are:

- `release_decision`: exactly `approve`, `conditional`, or `reject`;
- `conditions_or_followups`: a non-empty audit statement, including `none`
  when no follow-up is required.

For non-pending records, `status` maps to the decision: `accepted` means
`approve`, `conditional` means `conditional`, and `rejected` means `reject`.
The record's reviewer, date, policy version, and source refs remain mandatory.

SampleDB adds an append-only `scientific_release_reviews` table keyed by
`record_id` and linked to a `batch_id`. Each row stores the validated record
JSON, its decision snapshot JSON, and creation time. A batch may have multiple
records; the latest record is the display projection, while earlier records
remain available for audit.

## Flow

```text
current persisted run
    -> Results Workbench opens project release dialog
    -> reviewer enters release record and source refs
    -> core validation + release/status consistency check
    -> append record to SampleDB(batch_id)
    -> latest snapshot is projected into current Results/History/Export context
```

The projection is display/provenance only. Saving a release record does not
rewrite figure roles, `paper_conclusion_ready`, numeric results, or source
evidence. An absent or invalid record remains visible as not approved.

## UI and persistence boundaries

- `ScientificReviewDialog` is reused with the `release` scope so the core
  schema remains one source of truth.
- Results Workbench exposes a separate release action when the current result
  has a persisted run and batch id. It is distinct from the IR/NMR/Joint
  scientific-review action.
- `SampleDB` owns transaction and append-only storage. It validates the
  serialized release record before inserting it and returns the latest record
  for run/history consumers.
- History and Export receive a detached JSON-safe `scientific_release`
  projection. They never infer release state from a button or from figure role.

## Failure behavior

- Unknown batch: no row is written and the UI reports that the release target
  is unavailable.
- Malformed record or snapshot: no row is written.
- Inconsistent status/decision: validation fails closed.
- No release record: existing run output remains available and the export
  explicitly reports `release_missing`.

## Verification

Focused tests cover status/decision validation, append-only round-trip,
latest-record hydration, Workbench target selection, and export/history
provenance. SAXS tests and files are excluded from this task's allowlist.
