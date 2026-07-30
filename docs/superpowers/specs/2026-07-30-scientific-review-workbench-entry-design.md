# Scientific Review Workbench Entry Design

## Goal

Connect the existing reviewer-owned, fail-closed review contract to the
Results Workbench so a reviewer can persist a decision against the exact
analysis run under review.

## Design

`polynexus.core.scientific_review` remains the only authority for supported
scopes, required decision keys, validation, and promotion snapshots. It gains
small read-only helpers for the GUI to obtain the required fields and map the
current technique/submodule to a gated scope. The GUI never branches on
algorithm state.

The Workbench opens a generic dialog with fields for record id, reviewer,
review date, policy version, source references, status, conditions, and the
scope-specific decision values. Decision values are edited as JSON-safe text
fields. The dialog constructs `ScientificReviewRecord`, calls the core
validator, and returns the serialized record only after validation succeeds.

The main window attaches the record to the current run payload and calls a
SampleDB update method. The database update is one transaction: it preserves
the existing summary/evidence, adds the serialized record and the derived
`review_decision` snapshot, and updates neither figure files nor publication
roles. History and export already traverse the run payload; their existing
presentation adapter therefore displays the same snapshot after refresh.

## Failure and safety behavior

- No current run or no gated scope: the action is disabled.
- Cancel or invalid record: no database write and no in-memory mutation.
- Missing or mismatched source refs: the saved record remains non-promoting
  under `promotion_decision`.
- Accepted records are provenance, not an automatic scientific conclusion;
  a later explicit rerun/republication remains responsible for Figure role
  changes.
- SAXS scopes are excluded from this task even though the shared core contract
  knows about them.

## Testing

Core tests assert the public schema is stable and the context mapping is
fail-closed. Database tests assert one run changes while a second run and its
figure/provenance payload remain unchanged. GUI tests exercise the dialog
model through Qt's offscreen application and assert invalid input cannot emit
a record. Existing scientific review, IR, NMR, Joint, History, and Export
matrices remain the regression boundary.
