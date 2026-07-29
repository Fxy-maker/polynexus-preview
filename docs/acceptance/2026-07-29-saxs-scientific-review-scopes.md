# SAXS Scientific Review Scopes Acceptance

Task: `docs/agent/tasks/2026-07-29-saxs-scientific-review-scopes.md`
Design: `docs/superpowers/specs/2026-07-29-saxs-scientific-review-scopes-design.md`
Status: implementation verified and checkpointed; no SAXS scientific promotion
has occurred

## Intended acceptance boundary

This slice will prove that the shared review contract can represent two
independent SAXS review scopes:

- `saxs.1d`: sequence axis, frame identity, missing-repeat handling, metric
  claim scope, and promotion rule.
- `saxs.2d`: geometry reference, beam center, mask, saturation, orientation
  applicability, and promotion rule.

The values remain reviewer-owned opaque JSON-safe data. The software will only
validate structure and preserve the existing fail-closed gate.

## Evidence to record

- TDD RED: `5 failed, 10 passed`; the expected failure was unsupported SAXS
  scopes.
- TDD GREEN: `15 passed in 0.13s` for `tests/test_scientific_review.py`.
- Structured verifier exited `0`: quality `290` and preprocessing `106`.
- Exact SAXS matrix exited `0`: `575 passed, 6 warnings in 518.52s`.
- `git diff --check` exited `0`.
- Storage dry-run found `40` artifacts, `0` eligible bytes, and removed `0`.
- The SAXS allowlist was selectively staged because same-file policy/provenance
  edits remain in the worktree; no unrelated hunk was included.

## Explicit limitations

This does not establish that any real SAXS dataset is scientifically accepted.
It does not validate beam geometry, mask correctness, orientation meaning,
Guinier/metric interpretation, or reviewer decision values. Those require
separate evidence-bound consumer tasks and human scientific review.
