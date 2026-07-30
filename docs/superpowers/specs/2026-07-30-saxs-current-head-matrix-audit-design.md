---
title: Current-head SAXS matrix audit after Workbench provenance checkpoint
date: 2026-07-30
status: implemented
---

# Current-head SAXS Matrix Audit

## Decision

Run every repository test file matching `tests/test_saxs_*.py` against the
current checkout after checkpoint `fd9bb3d`. Accept the result only when pytest
prints a complete summary and exits with code `0`.

## Scope

This is verification-only. It checks that the Workbench detector-provenance
presentation checkpoint does not regress the existing SAXS quality, analysis,
transport, consumer, and lifecycle contracts.

## Boundaries

- No production code, thresholds, quality levels, physical gates, rescue, AI,
  publication roles, real data, generated outputs, or GUI behavior changes.
- No full repository release claim is inferred from a SAXS-only matrix.
- Tool timeouts, setup errors, access violations, and process exits without a
  pytest summary are recorded as incomplete evidence.
- Existing parallel worktree changes remain outside this audit.

## Acceptance

- The complete current `test_saxs_*.py` file set is enumerated and executed.
- A complete pytest summary and exit code are recorded verbatim.
- Any failure is classified by actual output rather than inferred from process
  state.
- Task verification and diff hygiene are run after the matrix.
