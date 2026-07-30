---
task_id: 2026-07-30-scientific-review-workbench-entry
kind: scientific-semantics
status: verified
date: 2026-07-30
title: Add a Results Workbench entry point for reviewer-owned decisions
---

# Scientific Review Workbench Entry

## Goal

Allow a reviewer to create and persist a validated `ScientificReviewRecord`
from the Results Workbench without bypassing the existing fail-closed
promotion contract.

## Non-goals

- Do not invent IR coordinates, ROI bounds, NMR assignments, Xc values, or
  Joint conflict precedence.
- Do not promote an existing Figure/Manifest when a record is merely saved.
- Do not add technique-specific scientific algorithms to GUI event handlers.
- Do not read, modify, or clean SAXS source, tests, evidence, or scratch data.

## Affected boundaries

- Core review contract: public scope schema and context normalization.
- SampleDB: immutable serialized review payload attached to one analysis run.
- GUI: generic Results Workbench dialog and run-scoped save action.
- History/Export: existing payload traversal must expose the saved decision.

## Implementation plan

1. Expose the existing review scope schema through read-only core helpers.
2. Persist one validated review payload and promotion snapshot transactionally
   on the selected analysis run.
3. Add a generic scope-driven Qt dialog and connect it to the gated Results
   Workbench review action.
4. Verify that History/Export presentation sees the same snapshot while Figure
   assets and publication roles remain unchanged.

## Acceptance criteria

- [x] Gated scopes expose their required decision keys through a public core
      contract; GUI does not duplicate the scientific key list.
- [x] The dialog validates reviewer, date, policy, source refs, status, and
      required decisions through `ScientificReviewRecord` before save.
- [x] Saving updates only the selected run's JSON evidence/summary and keeps
      the record source-linked; unsaved or invalid input leaves the run intact.
- [x] History and export presentation show the same review snapshot.
- [x] No Figure role changes occur as a side effect of saving a record.
- [x] Focused tests cover valid save, invalid save, missing scope, and
      source-linked round-trip; non-SAXS regressions remain green.

## Verification

```powershell
python -m pytest tests/test_scientific_review.py tests/test_scientific_review_workbench.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-workbench-entry.md --changed --types
git diff --check
```

## Verification result

`python scripts/verify.py --task docs/agent/tasks/2026-07-30-scientific-review-workbench-entry.md --changed --types` passed. Task and memory checks, Ruff, compile, quality `290 passed`, preprocessing `106 passed`, and whitespace all passed. No changed file matched the phased type-check baseline.

## Explicit changed-file allowlist

- `polynexus/core/scientific_review.py`
- `polynexus/data/sample_db.py`
- `polynexus/gui/scientific_review_dialog.py`
- `polynexus/gui/main_window_results_mixin.py`
- `tests/test_scientific_review.py`
- `tests/test_scientific_review_workbench.py`
- `docs/agent/tasks/2026-07-30-scientific-review-workbench-entry.md`
- `docs/superpowers/specs/2026-07-30-scientific-review-workbench-entry-design.md`
- `docs/superpowers/plans/2026-07-30-scientific-review-workbench-entry.md`
- `docs/acceptance/2026-07-30-scientific-review-workbench-entry.md`
- `docs/agent/memory/active-work.md`
