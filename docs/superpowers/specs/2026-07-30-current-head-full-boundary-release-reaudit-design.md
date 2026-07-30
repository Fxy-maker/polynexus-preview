---
title: Current-head full and boundary release re-audit
date: 2026-07-30
status: implemented
---

# Current-head Full/Boundary Release Re-audit

## Decision

Run the repository's authoritative `verify.py --changed --types --full
--boundary` command on the current HEAD after the latest SAXS and shared review
checkpoints. Accept full/boundary evidence only when the command returns zero,
pytest prints a complete summary, and the boundary audit completes.

## Scope

This is a read-only release-evidence re-audit. It exists to classify the
current checkout, not to repair or bypass a failing test, Qt crash, setup
permission error, or timeout.

## Boundaries

- No production code, scientific thresholds, quality levels, physical gates,
  AI/rescue policy, publication roles, real datasets, or generated outputs are
  changed.
- Parallel uncommitted files remain outside the checkpoint allowlist but are
  part of the current checkout being honestly audited.
- A SAXS-only result remains SAXS evidence; a full/boundary result remains
  automated release evidence and does not replace human scientific or visual
  approval.
- Any incomplete process state is recorded as incomplete, never as a pass.
