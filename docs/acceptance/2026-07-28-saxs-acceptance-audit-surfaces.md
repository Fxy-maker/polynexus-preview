# SAXS acceptance audit surface binding

Date: 2026-07-28
Task: `docs/agent/tasks/2026-07-28-saxs-acceptance-audit-surfaces.md`

## Result

The existing read-only SAXS `scientific_acceptance_audit` now travels through
the three downstream software surfaces without being recalculated:

- Workbench renders status/reasons as advisory risk/next text and leaves input
  parameters unchanged.
- Static, temperature, and strain Figure/Manifest providers attach a detached
  strict-JSON snapshot under `recipe.evidence.quality_provenance` while
  preserving figure IDs and publication roles.
- `quality_evidence.json` includes the existing audit only when it is present
  in `result.parameters`; missing audits remain absent.

## Verification

- Final TDD RED after fixture correction: `3 failed, 1 passed`; failures were
  the missing Workbench, Figure, and Export bindings.
- Focused GREEN: `4 passed in 0.18s`.
- Surface/provider matrix: `15 passed in 4.46s`.
- Exact SAXS matrix: `449 passed, 6 warnings in 154.00s`.
- Structured verifier exited `0` with quality `287 passed`, preprocessing `106
  passed`, Ruff, compile, type baseline, task/memory, and whitespace checks
  passing.
- `git diff --check` passed.
- `python scripts/test_storage.py report --json` completed in dry-run mode;
  no cleanup or deletion was performed.
- Full/boundary verification was not run for this atomic task and is not
  claimed.

## Boundary

This is transport and advisory presentation only. No SAXS metric, physical
threshold, publication role, AI behavior, frame alignment, or scientific
interpretation changed; scientific and final release review remain open.

The explicit allowlist checkpoint hash is recorded in the final handoff.
