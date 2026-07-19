# Chart Gallery Search, Sort, Batch, and Revision Status Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

`ChartGallery` remains a manifest-entry consumer. Search and sorting operate on
the current `_all_entries` snapshot and never discover new files. Each card has
an independent batch checkbox; the normal current-card selection remains the
preview/editor route. Selected export copies only selected asset paths and
never overwrites an existing destination. Revision status is derived from the
entry's working/published revision fields and remains informational.
