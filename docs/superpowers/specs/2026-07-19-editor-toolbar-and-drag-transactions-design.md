# Editor Toolbar and Drag Transaction Design

Date: 2026-07-19
Status: approved for implementation under the active editor-improvement Goal

Toolbar icons are generated as small vector `QIcon`s at runtime, with action
text retained as tooltip and accessibility text. Generated drag motion is a
preview-only mutation while a session is active. The original object is kept
in the drag state; release submits a `ReplaceObjectCommand` against the
session's original document, yielding one history entry. Cancel restores the
preview snapshot and submits nothing.
