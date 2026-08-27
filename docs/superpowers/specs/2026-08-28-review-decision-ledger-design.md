# Evidence Review Decision Ledger

## Goal

Give every evidence package one explicit, editable review ledger that records
human decisions for Results/Discussion scope without changing immutable
provider evidence.

## Design

Package creation writes `review-decision.json` from the generated ARS
`human_review` items. Each item starts with `decision: "pending"` and retains
the evidence id, requested action, and reason. The ledger also stores package
identity and reviewer metadata. ARS writing input references this file and
reports its pending status.

The ledger is an external decision record, not a scientific recalculation.
Editing it cannot change metric values, source hashes, or evidence roles. A
future reviewer/editor may replace pending decisions with accepted,
conditional, or rejected values; malformed or stale ledgers must be ignored or
rejected rather than treated as approval.

## Boundaries

- No automatic promotion of diagnostic metrics.
- No mutation of `evidence.json`, citation metrics, or run manifests.
- Existing packages without the file remain readable as historical packages.

## Acceptance

- New packages contain a deterministic `review-decision.json`.
- ARS input references the ledger and exposes its pending status.
- Every generated decision is pending and linked to an existing evidence item.
- Package and existing evidence validation remain unchanged for historical data.
