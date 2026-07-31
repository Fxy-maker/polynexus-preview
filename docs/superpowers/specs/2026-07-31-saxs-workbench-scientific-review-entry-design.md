---
title: SAXS Workbench reviewer-owned scientific review entry
date: 2026-07-31
status: approved
---

# SAXS Workbench Scientific Review Entry

## Decision

Expose the existing `saxs.1d` and `saxs.2d` reviewer-owned contracts from the
Results Workbench through an explicit scope choice. The system must not infer
whether a current SAXS run is scientifically a 1D or 2D review case from
technique-specific algorithm state.

## Flow

1. The core returns the review scopes available for the current technique
   context. For SAXS this is the ordered pair `saxs.1d`, `saxs.2d`; no mode or
   detector interpretation is inferred.
2. The Workbench asks the reviewer to choose one of those scopes.
3. The existing generic `ScientificReviewDialog` renders the required keys
   from the core contract and validates the record.
4. The existing run-scoped SampleDB update persists the record and immutable
   promotion snapshot. History, Figure, Manifest, and Export consumers see
   the same evidence payload.

## Safety boundaries

- The scope choice is reviewer input, not an AI or heuristic decision.
- Saving a record never recalculates q/I, changes quality levels, changes
  physical gates, runs rescue, or changes publication roles.
- `pending`, `conditional`, `rejected`, `stale`, invalid, missing-source, and
  cancelled flows remain non-promoting through the existing contract.
- The existing single-scope mappings for IR, NMR, and Joint are unchanged.
- No default decision text is supplied for geometry, beam center, mask,
  saturation, orientation, sequence identity, or missing-repeat policy.

## Acceptance

- Core exposes deterministic SAXS scope options without changing the
  fail-closed single-scope resolver.
- The Workbench shows the review action for a persisted SAXS run, requests an
  explicit 1D/2D choice, and does nothing when the choice is cancelled.
- A selected SAXS scope reuses the existing validated dialog and persists a
  source-linked snapshot against exactly one run.
- Focused RED/GREEN, task verification, SAXS regression, diff check, and an
  explicit allowlist checkpoint are recorded.
