---
kind: task
status: completed
date: 2026-07-19
title: Chart gallery search, sorting, batch export, and revision status
---

# Chart gallery search, sorting, batch export, and revision status

## Goal

Make the active chart gallery usable for larger runs by adding search, stable
sorting, explicit working/published revision status, and selected-item batch
export without changing manifest-only discovery.

## Non-goals

- Do not enable recursive historical discovery in the active gallery.
- Do not alter figure generation, publication, or scientific semantics.
- Do not delete or overwrite source assets during batch export.

## Acceptance criteria

- [x] Search filters the visible entries by title, id, status, or error.
- [x] Sorting supports title and revision status while preserving selection.
- [x] Each card shows working/published revision status when available.
- [x] Users can select cards and batch-export only selected assets.
- [x] Focused gallery regression tests cover search, sorting, status, and batch
      export.

## Affected boundaries

- [x] ChartGallery presentation and filtering
- [x] Gallery asset export boundary
- [x] Automated tests

## Implementation plan

1. Add failing gallery management tests.
2. Implement search/sort state, card selection, revision badge, and selected
   export.
3. Run the task-scoped verifier and create an atomic checkpoint.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-chart-gallery-search-sort-batch.md --changed --types
```

## Memory impact

Update `docs/agent/memory/active-work.md` with exact gallery test and verifier
results.

## Evidence

- Gallery management and existing chart viewer suite: `26 passed`.
- Active gallery remains manifest-only; historical recovery remains explicit.
