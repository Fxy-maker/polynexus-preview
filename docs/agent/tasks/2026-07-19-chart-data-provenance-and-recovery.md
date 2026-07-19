---
kind: task
status: completed
date: 2026-07-19
title: Chart data provenance and historical recovery
---

# Chart data provenance and historical recovery

## Goal

Make every chart viewer opened from the active gallery resolve and display the
data belonging to that figure, and make the explicit historical recovery view
use the real gallery widget without runtime type mismatches.

## Non-goals

- Do not change scientific analysis results or figure generation semantics.
- Do not enable recursive discovery in the normal active gallery.
- Do not redesign the editor, export workflow, or object model in this task.
- Do not edit generated figures, real datasets, or user runtime directories.

## Context

The figure document already stores `data_sources`, `data_ref`, `run_root`, and
manifest context. The current viewer can display raw data only when callers
pass an unrelated `raw_data` payload, while the gallery's standalone viewer
does not pass any data. The historical recovery path creates `ChartViewer` but
calls `load_entries`, which belongs to `ChartGallery`.

## Acceptance criteria

- [x] A gallery-opened viewer resolves the selected figure's own data sources.
- [x] A missing or unreadable source produces an explicit status message and
      does not silently display another figure's data.
- [x] A viewer opened for a selected figure receives its entry/document context.
- [x] The historical recovery view instantiates a widget that implements
      `load_entries` and keeps recovery entries separate from active gallery state.
- [x] Regression tests cover source selection, missing-source behavior, and the
      real recovery widget contract.

## Affected boundaries

- [x] GUI/viewer workflow
- [x] Figure document/data-source boundary
- [x] Historical recovery boundary
- [x] Automated tests

## Implementation plan

1. Add a pure data-source resolver/service for figure documents.
2. Make `ChartViewer` accept figure entry/document context and load exact data.
3. Route standalone gallery viewing through `ChartGallery` or a shared gallery
   view wrapper that supports both entries and full-size preview.
4. Add focused regression tests and run the task-scoped verifier.

## Verification

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-19-chart-data-provenance-and-recovery.md --changed --types
```

## Risks and compatibility

- Legacy figures without a document remain viewable as images; their data tab
  reports unavailable provenance instead of guessing from the current result.
- Existing `open_chart_viewer(..., raw_data=...)` callers remain compatible while
  the entry/document path becomes the preferred source.

## Evidence

- Focused viewer/provenance/recovery suite: `43 passed`.
- Task-scoped verifier: `python scripts/verify.py --task docs/agent/tasks/2026-07-19-chart-data-provenance-and-recovery.md --changed --types` passed.
- The verifier also passed the core quality gate (`281 passed`) and
  preprocessing optimization gate (`103 passed`).

## Memory impact

- Update `docs/agent/memory/active-work.md` with the verification evidence.
- Add a decision entry only if the new source-resolution contract changes the
  existing figure document boundary.
