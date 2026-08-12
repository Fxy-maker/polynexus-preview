# Project Workflow Recovery V4 Acceptance

Date: 2026-08-13

V4 adds `ProjectWorkflowService.resume(run_id)` and
`approve_context_correction(...)`. Resume validates persisted request/plan
identity and current source hashes before reusing the deterministic route.
Context corrections require an explicit approval marker and approver, are
stored as new request parameters, and are shown in writing input as metadata,
never as raw instrument facts.

Packaging multiple runs also emits a `cross_technique_evidence_set` (or
same-technique series) membership relation. This is a relation between
explicitly selected evidence runs, not an inferred sample or batch identity.

## Verification

- Recovery plus project workflow matrix: `28 passed`.
- `git diff --check`: passed.
- Task-level structured verifier: required before checkpoint.

## Limits

Retry does not change provider algorithms or automatically accept scientific
interpretation. Missing or changed sources fail closed.
