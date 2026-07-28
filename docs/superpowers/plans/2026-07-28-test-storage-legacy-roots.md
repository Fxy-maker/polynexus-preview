# Test-storage legacy roots implementation plan

## Goal

Make historical Windows test-output roots visible to the existing dry-run-first
storage report and cleanup flow without scanning arbitrary user directories or
touching protected data.

## Scope

- `scripts/test_storage.py`: exact legacy-root discovery, explicit overrides,
  and active-pytest protection.
- `tests/test_test_storage.py`: discovery and cleanup safety regressions.
- `AGENTS.md` and `README.md`: operator-facing storage contract.

## Plan

- [x] Define exact automatic prefixes and explicit root overrides.
- [x] Keep externally discovered legacy artifacts protected while pytest is
  active; preserve dry-run as the default.
- [x] Add focused tests for root resolution, discovery, and protection.
- [x] Run focused tests, task-scoped verifier, and diff checks.
- [x] Create one explicit allowlist checkpoint (`b657ccc`).

## Verification

Focused storage matrix: `10 passed` on 2026-07-29. The task-scoped verifier
passed with quality `283 passed` and preprocessing `106 passed`; the allowlist
checkpoint is `b657ccc`. A read-only C-drive inventory currently reports 441
matching legacy directories totalling approximately 164.42 GiB. Cleanup is
still gated on a no-active-pytest dry-run and explicit `--apply`.
