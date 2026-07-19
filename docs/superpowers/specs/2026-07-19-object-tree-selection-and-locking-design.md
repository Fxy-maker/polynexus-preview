# Object Tree Selection and Locking Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

The object tree remains a presentation of the canonical figure document. Its
filter and selection state are UI state, while lock/unlock is a document edit
and therefore must use `EditSession` and an undoable command. Multi-selection is
represented as an ordered tuple of ids; the first id remains the compatibility
`object_id` used by existing Inspector and renderer code until batch commands
are introduced.

Filtering must not delete or mutate document objects. It rebuilds the list from
the session snapshot and keeps the background row visible so users can clear
selection. Locked objects remain selectable and visible, but normal style,
geometry, delete, and reorder controls are disabled by existing capabilities.
