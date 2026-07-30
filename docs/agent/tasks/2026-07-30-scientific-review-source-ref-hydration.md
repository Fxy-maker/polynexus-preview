---
task_id: 2026-07-30-scientific-review-source-ref-hydration
kind: scientific-semantics
status: verified
date: 2026-07-30
title: Preserve nested source references in the scientific review entry
---

# Scientific Review Source Reference Hydration

## Goal

Keep reviewer source references visible when a restored IR mapping or other
non-SAXS result stores its source identifier inside nested analysis evidence.

## Non-goals

- Do not change scientific review scopes, required decisions, or promotion rules.
- Do not infer coordinate, ROI, assignment, or publication semantics.
- Do not modify Figure roles, manifests, real datasets, or SAXS files.
- Do not delete or clean test data.

## Affected boundaries

- Results Workbench source-reference extraction.
- Restored `AnalysisResult` and history payload traversal.
- Focused non-SAXS GUI regression coverage.

## Implementation plan

1. Add a regression test for a source identifier nested in mapping evidence.
2. Hydrate the existing review source-reference list from the shared evidence
   traversal without changing scientific review semantics.
3. Verify the focused Workbench suite, native IR route, and task-scoped checks.

## Acceptance criteria

- [x] Nested `analysis_evidence` source identifiers are included once and
      remain source-linked after history restore.
- [x] Existing metadata and current-file source references remain unchanged.
- [x] Scientific review dialog behavior and fail-closed promotion behavior
      remain unchanged.
- [x] Native IR mapping route can open the review entry with the hydrated
      source reference.

## Verification

```powershell
python -m pytest tests/test_scientific_review_workbench.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-source-ref-hydration.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_scientific_review_workbench.py`
- `docs/agent/tasks/2026-07-30-scientific-review-source-ref-hydration.md`
- `docs/agent/memory/active-work.md`
