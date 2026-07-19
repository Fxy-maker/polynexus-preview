# Batch Alignment and Grouping Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

Alignment and grouping are document edits, not canvas-side mutations. Each
command snapshots the full object list and applies the whole operation in one
`EditSession` entry. Alignment shifts geometry while preserving width, height,
and line endpoint distance. Grouping adds a stable `group_id` to selected
objects; ungrouping removes it. Locked or unsupported objects fail before any
mutation. The GUI only passes ordered selected ids and uses the first id for
existing single-selection compatibility.
