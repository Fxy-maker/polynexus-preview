# Editor Interaction Reliability

## Goal

Make direct chart editing predictable for text, rectangles, lines, and curves,
while keeping the canvas stable during tool changes and preserving reliable
undo/redo behavior.

## Non-goals

- Do not change scientific analysis, data-source resolution, figure rendering
  semantics, or export formats.
- Do not redesign the editor's visual theme or add new annotation types.
- Do not remove or rewrite the existing edit-session/public command contracts.

## Affected boundaries

- `polynexus/gui/widgets/annotation_canvas.py`: scene coordinates, selection,
  geometry handles, curve control points, zoom, and local annotation history.
- `polynexus/gui/widgets/chart_editor_context_style_mixin.py` and layout
  construction: context-bar visibility without changing canvas geometry.
- `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py` and edit
  session routing: one committed transaction per completed drag and consistent
  undo/redo routing.
- Focused Qt regression tests under `tests/`.

## Implementation plan

1. Reproduce each reported interaction through the existing public test seams
   and inspect the full coordinate/transaction path before changing code.
2. Add failing regression tests for text and rectangle creation/selection/
   movement/resizing, line endpoint preservation, curve control-point range,
   context-bar layout stability, undo/redo transaction count, and selection
   zoom invariance.
3. Fix scene geometry so all movable objects use stable scene coordinates and
   selection handles update the stored geometry without implicit fitting.
4. Give curves a useful default control point and preserve editable control
   coordinates independently from the endpoints.
5. Keep context-style controls in a fixed-height or overlay surface so their
   visibility cannot resize the canvas stack.
6. Commit drag changes through the existing edit-session/annotation transaction
   boundary once on release, with redo invalidation only after a real edit.
7. Run focused tests, the structured verifier, the default verifier, and record
   known Qt limitations without overstating coverage.

## Acceptance criteria

- [x] A text object and rectangle can be selected, moved, and resized with handles;
  their geometry changes in the intended direction.
- [x] Moving a line preserves independently editable endpoints and never collapses
  its horizontal/diagonal geometry merely because the pointer moved downward.
- [x] A curve can be bent substantially beyond the previous fixed ~20 px default;
  its control point can be moved without changing zoom.
- [x] Showing or hiding the bottom context style controls leaves the canvas widget's
  geometry unchanged.
- [x] One completed drag creates one undoable edit; undo restores the prior state
  and redo restores the edited state.
- [x] Selecting a curve leaves zoom level and view transform unchanged.
- [x] Existing focused editor, workflow, render, and export tests remain green.

## Verification

```text
python -m pytest tests/test_annotation_canvas.py tests/test_chart_editor_curve.py tests/test_chart_editor_workflow.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-interaction-reliability.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitations

- Existing multi-file Qt-heavy test combinations may still expose the documented
  Windows Qt access violation in the legacy `LayerTreeItem.setData()` path;
  stable focused batches must be reported separately if that persists.
