# SAXS 2D reviewer evidence binding implementation plan

## Task 1: Define the RED boundary

- [x] Add shared-attachment tests with ordinary and detector/2D Figure
  definitions using an accepted `saxs.2d` payload.
- [x] Assert accepted 2D evidence, ordinary-1D scope mismatch, and partial
  source fail-closed behavior without changing publication roles.
- [x] Run the focused tests and confirm the missing scope-aware implementation
  is the reason for failure.

## Task 2: Implement the shared projection

- [x] Generalize the existing reviewer projection to accept an explicit
  expected scope while preserving the `saxs.1d` public wrapper.
- [x] Select `saxs.2d` only for existing detector/2D/orientation Figure recipes
  and IDs; keep all other definitions on `saxs.1d`.
- [x] Keep the output detached and strict-JSON-safe.
- [x] Run GREEN and the adjacent Figure evidence regressions.

## Task 3: Verify and checkpoint

- [x] Run the focused SAXS matrix, task verifier, exact SAXS matrix, diff
  hygiene, and storage report/clean dry-run.
- [x] Update this task card and durable memory with exact evidence.
- [x] Create one explicit changed-file allowlist checkpoint.
