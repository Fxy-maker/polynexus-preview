---
title: Current-head real SAXS lifecycle and 2D boundary re-audit
date: 2026-07-30
status: implemented
---

# Current-head Real SAXS Boundary Re-audit

## Decision

Replay the existing read-only PAD8 2D scientific-acceptance contract and the
real published SAXS Static/Temperature/Strain lifecycle on current HEAD using
C:-isolated basetemps. Require complete pytest summaries and exit code `0` for
each shard before recording automated evidence.

## Scope and boundaries

- Read-only use of existing fixtures and public analysis/persistence paths.
- No new detector calibration, mask/orientation interpretation, thresholds,
  rescue, AI calls, frame fabrication, interpolation, role promotion, or
  reviewer values.
- A passing contract confirms conservative transport and fail-closed behavior;
  it does not grant instrument-level scientific or publication approval.
- D: test storage remains untouched because it is full; no `--apply` runs.
