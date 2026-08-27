# Package Context and ARS Consistency — Acceptance

## Result

Package creation now collects deduplicated `approved_context_corrections` from
persisted run manifests. `ars-writing-input.json` exposes the same values under
`project_context`, labels their status/approver, and explicitly sets
`is_instrument_fact: false`.

## Verification

- Project ARS handoff and package regression matrix: `39 passed`.
- Structured verifier and quality gates: pending final checkpoint.

## Boundary

This change does not alter numerical calculations, metric eligibility, figure
selection, or sample identity inference. Context is an explicit user/AI
statement that helps ARS interpret the selected groups, not evidence extracted
from instrument bytes.
