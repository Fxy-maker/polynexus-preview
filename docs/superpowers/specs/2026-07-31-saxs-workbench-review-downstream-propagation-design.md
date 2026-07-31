---
title: SAXS Workbench review downstream evidence propagation
date: 2026-07-31
status: approved
---

# SAXS Workbench Review Downstream Evidence Propagation

## Problem

The Results Workbench saves a validated scientific-review record and its
decision snapshot into the current `AnalysisResult` and the run-scoped
SampleDB row. SAXS Figure/Manifest and Export consumers currently read only
`engine.cfg.scientific_review`. A review saved after analysis can therefore be
visible in History while a Figure definition or `quality_evidence.json`
constructed from the same current result omits it.

## Decision

Use one read-only consumer adapter for the existing review payload:

1. Prefer `engine.result.metadata["scientific_review"]`, because this is the
   current Workbench-applied run snapshot.
2. If that result metadata is absent, retain the existing
   `engine.cfg.scientific_review` lookup for older direct-engine callers.
3. Never merge, infer, or synthesize records between the two locations.
4. Pass the selected record through the existing `build_saxs_review_evidence`
   and `promotion_decision` source/scope/status checks. Mismatch, invalid,
   missing, pending, conditional, rejected, or stale records remain detached
   evidence with `allowed: false` and their existing reason.

The same adapter is used by Figure provenance and SAXS Export quality
evidence. FigurePipeline persists the unchanged recipe evidence into the
Manifest-backed document. No existing figure role or promotion decision is
modified.

## Non-goals and safety boundaries

- Do not write review data from Figure or Export consumers.
- Do not update existing files on disk from this slice; a pre-existing Figure
  document is not silently rewritten by export.
- Do not change SAXS calculations, data-quality levels, physical gates,
  AI/rescue behavior, publication roles, or History persistence.
- Do not treat an accepted review as publication approval; it remains only the
  existing scope-specific review evidence.
- Do not infer `saxs.1d` versus `saxs.2d`; the record's declared scope is still
  checked by the existing consumer contract.

## Acceptance

- A Workbench-applied result review reaches a newly built SAXS Figure recipe.
- The same recipe evidence survives FigurePipeline persistence into its
  Manifest-backed `figure.pnfig.json` document.
- A Workbench-applied result review reaches Export `quality_evidence.json`.
- Configuration-only callers retain the previous behavior.
- Source/scope mismatch remains fail-closed.
- Focused RED/GREEN tests, task verification, SAXS regression, diff check,
  storage dry-runs, and an explicit changed-file allowlist checkpoint are
  recorded.
