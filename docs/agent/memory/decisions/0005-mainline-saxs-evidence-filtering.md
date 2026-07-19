---
kind: decision
status: active
date: 2026-07-12
title: Incremental SAXS evidence-filtering rollout
---

# Decision 0005: Incremental SAXS evidence-filtering rollout

Date: 2026-07-12

## Decision

Use `origin/main` as the canonical SAXS provider base and implement the approved path A rollout: preserve the current provider API and figure IDs, add evidence-backed filtering and role propagation incrementally, and keep temperature and strain as separate commits.

## Rationale

The integration branch replaces the current SAXS provider with a much larger architecture rewrite. Directly replaying it would combine provider, result-contract, and scientific publication changes that cannot be reviewed as one safe merge. The current mainline already owns the shared publisher and production cutover boundary.

## Contract

- `SAXSFrameView` is the read-only evidence boundary.
- `FigureEligibilityDecision` derives `main`, `si`, or `diagnostic` only from emitted evidence.
- Missing evidence defaults to SI; explicit errors or paper-candidate rejection veto main promotion.
- Mixed completed temperature/strain results and incomplete declared series remain unsupported/incomplete and never fall back to static.
- The provider must not re-run analysis or repair missing scientific values.

## Deferred

Representative-frame selection, curated multi-panel packs, full integration-provider parity, DSC/WAXS migration, Unified Tables, GUI wiring, and PR #9 closure remain separate reviewed work.
