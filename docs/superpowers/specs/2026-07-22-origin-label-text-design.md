# Origin-style generated text labels

## Decision

Generated text annotations will use an Origin-style label interaction rather
than a persistent user-sized text rectangle. A label's rendered bounds follow
its text and font metrics. Selection shows a tight transient frame and corner
handles; the frame is never part of export output.

## User interaction

- In the normal canvas, a label renders as text only.
- Selecting a label shows a small padded frame that follows the rendered text
  extent, with four corner handles.
- Dragging the text body moves the label while retaining its Axes-relative
  anchor.
- Dragging any corner handle scales the font size proportionally. The label
  keeps its opposite corner fixed in display space for the duration of the
  drag, then redraws using the resulting font metrics.
- Double-click opens the existing inline editor at the label's top-left edge.
  Enter commits the displayed `text`; Escape cancels.

## Geometry and persistence

- `coordinate_space: "axes"` remains the coordinate contract for new and
  migrated generated text labels.
- A label persists its anchor (`x`, `y`), `text`, and `style.font_size`.
  Persisted `width`/`height` remain accepted for legacy compatibility but no
  longer define a visible empty text area for an Origin-style label.
- Font scaling derives from display-space handle movement and is clamped to a
  readable range. It is committed as one undoable style edit, rather than as a
  geometry resize command.
- Renderer, preview, selection, hit testing, export, Inspector font control,
  and undo/redo use the same font-size value.

## Compatibility and scope

- Existing text objects remain readable. On their next generated-document
  redraw, their rendered text extent becomes the visible selection boundary.
- Legacy data-coordinate text keeps its existing migration-on-save behavior.
- Lines, curves, rectangles, legends, plot series, static-image annotations,
  scientific data, and axis semantics are out of scope.

## Validation

- Add focused tests for tight label selection bounds, body movement, corner
  font scaling, one-command undo/redo, and double-click text editing.
- Verify that exports contain no selection frame or handles.
- Run the focused ChartEditor matrix and both repository verifier commands.
