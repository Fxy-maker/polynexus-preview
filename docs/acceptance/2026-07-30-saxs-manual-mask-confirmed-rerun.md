# SAXS Manual Mask Confirmed Rerun Acceptance

Date: 2026-07-30
Task: `2026-07-30-saxs-manual-mask-confirmed-rerun`

## Outcome

Accepted as an atomic core boundary. An explicitly edited detector mask is
serialized as a detached JSON-safe candidate and reaches existing SAXS
preprocessing only after explicit confirmation. Pending, malformed, or
unconfirmed candidates fail closed. The raw detector image, existing quality
gates, physical gates, and publication gates remain authoritative.

## Evidence

- Focused TDD coverage covers strict serialization, pending no-op behavior,
  digest mismatch rejection, confirmed isotropic propagation, and confirmed
  sector/azimuthal propagation.
- Task-scoped verification passed with quality `292 passed` and preprocessing
  `106 passed`; Ruff, compile, type baseline, memory, and whitespace checks
  also passed.
- Exact SAXS matrix, using all current `tests/test_saxs_*.py` files, passed
  `636` tests with `6` warnings in `540.67s`; exit code `0`.
- Storage report was dry-run only: `54` artifacts, `15802078628` bytes,
  `emergency=false`, `eligible_bytes=0`, and no report failures.
- Storage clean was dry-run only: `Eligible: 0 bytes`, `Cleanup failures: 0`,
  and `removed=0`.
- `git diff --check` passed.

## Scope Limits

This checkpoint does not add a GUI mask editor, automatic mask inference,
interpolation, morphology, AI calls, new scientific thresholds, or automatic
rescue. Full/boundary release verification is not claimed here; its separate
current-head evidence remains open where documented.

## Checkpoint

The source, regression test, design/spec/plan, task card, acceptance note, and
active-work entry are committed together through the explicit task allowlist.
No push, merge, dataset edit, or storage apply was performed.
