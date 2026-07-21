# Editor strong-feedback mode

## Goal

Make selection, dragging, resizing, active tools, and layer-tree state visibly
obvious in the chart editor while preserving existing document and history
contracts.

## Affected boundaries

- Pure chart-editor status and tool feedback helpers.
- Matplotlib-generated selection-frame overlays and export filtering.
- Qt static selection overlays and layer-tree synchronization.
- Focused Qt, renderer, workflow, and repository verification tests.

## Non-goals

- No scientific renderer, axes, data semantics, document schema, or export
  format changes.
- No new annotation types or broad inspector redesign.
- No replacement of the existing interaction controller or edit-session
  command boundary.

## Acceptance criteria

- [ ] Selecting text, rectangle, line, arrow, or curve visibly shows a blue
  frame and the correct handles in both static and generated modes.
- [ ] The status bar and active tool rail explain the current operation,
  including movement, resizing, and Escape cancellation.
- [ ] Canvas selection highlights and scrolls the matching layer-tree row;
  background is not presented as an active editable object by default.
- [ ] Feedback overlays are transient, do not mark the document dirty, and are
  absent from PNG/SVG/PDF/export captures.
- [ ] Existing object geometry, undo/redo, save/reload, and multi-selection
  behavior remain unchanged.
- [ ] Focused and repository verification commands pass.

## Implementation plan

See `docs/superpowers/plans/2026-07-21-editor-strong-feedback.md`.

## Verification

```text
python -m pytest tests/test_chart_editor*.py tests/test_annotation_canvas.py tests/test_figure_render_adapter.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-21-editor-strong-feedback.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitations

- Matplotlib remains the generated chart renderer; feedback overlays are
  intentionally view-only and are rebuilt around the existing render cycle.
