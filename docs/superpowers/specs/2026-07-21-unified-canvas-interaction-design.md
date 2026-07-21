# Unified Canvas Interaction Design

## Problem

The editor currently combines several interaction surfaces: Qt widgets for
tool and inline-text feedback, Matplotlib artists for generated-figure
previews, and `AnnotationCanvas` for static-image annotations. Those surfaces
do not share one geometry contract. A text drag can therefore show a screen
pixel rectangle while the persisted text object uses data coordinates; the
subsequent redraw can change the apparent scale and the final text bounds do
not feel like the box the user dragged.

The same risk exists for rectangles, lines, curves, and arrows whenever a
preview, selection frame, or persisted object is calculated by a different
layer.

## Goal

Make the editor feel like one canvas-first tool, similar to PowerPoint or
Origin, by giving text, rectangle, line, arrow, and curve a shared creation,
selection, movement, resize, cancellation, and undo contract in both static
and generated modes.

## Non-goals

- Do not replace PySide6 or Matplotlib.
- Do not rewrite scientific analysis, figure generation, or export semantics.
- Do not change the figure-document schema unless an optional backward-
  compatible geometry field is required.
- Do not add freehand drawing, CAD constraints, or a separate history system.
- Do not remove the current static/generated compatibility paths in one step.

## Design principles

1. One source of geometry truth: a drag is represented in normalized data
   coordinates as soon as the pointer is interpreted by the active canvas.
2. One visible boundary: preview, inline text input, selection frame, and
   resize handles are derived from the same geometry object.
3. Stable viewport: creating or previewing an object must preserve the active
   axis limits, scale type, figure size, and canvas position.
4. One lifecycle: `Select -> Creating -> TextEditing -> Selected` with
   `Escape` returning to `Select`, and `Enter`/commit creating one history
   command.
5. Renderer-neutral interaction: Qt and Matplotlib render the surface, but
   neither renderer owns edit-session history or object-specific decisions.

## Proposed architecture

### 1. Shared geometry contract

Introduce a small editor interaction geometry record in the existing editor
interaction layer. It represents one of:

- `Box(x, y, width, height)` for text and rectangles;
- `Segment(x1, y1, x2, y2)` for lines and arrows;
- `Curve(x1, y1, control_x, control_y, x2, y2)` for curves.

The record is always in the active axes' data coordinate system. Conversion to
screen pixels happens only at the canvas adapter boundary. Legacy document
objects continue to be read through the current normalization helpers and are
converted into this record before interaction.

### 2. Unified interaction controller

Extend the existing `EditorInteractionController` so both
`AnnotationCanvas` and generated-object interactions use the same transitions:

```text
Select
  -> Creating(tool, start_geometry)
  -> TextEditing(box, pending_payload)       [text only]
  -> Selected(object_id, geometry)
  -> Dragging(object_id, geometry)
  -> Resizing(object_id, handle, geometry)
  -> Select                                  [cancel]
```

The controller emits proposals only. Existing `EditSession` commands remain
the authority for persistence, undo, redo, and dirty state.

### 3. Canvas adapter boundary

Keep two rendering adapters, but give them the same narrow contract:

- convert pointer pixels to data coordinates;
- draw and clear a transient preview from a geometry record;
- draw and clear a transient selection frame/handles;
- map a geometry record to a Qt input rectangle;
- preserve and restore the viewport snapshot.

The generated adapter must render previews without adding them to the figure
document or allowing them to participate in autoscaling. The static adapter
uses the same geometry record for `QGraphicsItem` previews and persisted
annotations.

### 4. Text as a first-class box

Text placement uses the exact dragged `Box` for all stages:

1. Drag creates a data-space box and a matching transient frame.
2. The inline editor is positioned from that same box through the adapter and
   raised above the canvas.
3. Enter commits one text object carrying the same `x`, `y`, `width`, and
   `height` semantics.
4. The committed text object keeps the frame/handles contract, so its body can
   move and its corners can resize it.
5. A click without a meaningful drag uses a documented minimum box; it does
   not silently switch to a different placement model.

### 5. Viewport stability

At the beginning of a create/drag/resize transaction, capture x/y limits,
axis scale types, and figure/canvas dimensions. During preview and commit,
restore the snapshot after rendering. Any autoscale introduced by a new
Matplotlib artist is disabled or immediately corrected at the adapter
boundary. The interaction controller never calls figure-wide redraw logic
directly.

### 6. Selection and feedback

The selected object ID is the only selection authority. The object tree,
inspector, canvas frame, status label, and cursor are projections of that ID.
An empty selection is explicitly rendered as “未选择对象” / “No object
selected”; “背景” remains only an explicit background-edit entry.

## User-facing behavior

- Selecting Text, Rectangle, Line, Arrow, or Curve keeps the plot viewport
  fixed.
- Dragging shows the final object boundary, not a separate temporary shape.
- Text input appears inside that boundary and accepts typing immediately.
- Enter creates one object and selects it; Escape leaves no object and restores
  Select mode.
- Selected objects show the same blue frame and handles in both modes.
- Body drag moves the whole object; corner/endpoint handles resize or reshape
  it according to its type.
- Undo removes the whole transaction in one step.

## Compatibility and failure handling

- Documents with legacy `x/y`, `bounds`, or top-level geometry continue to be
  normalized into the shared record.
- Missing or invalid geometry cancels the transaction with a visible status
  message and does not create a partial object.
- A failed render restores the viewport snapshot and leaves the last committed
  document unchanged.
- Transient previews, frames, and input widgets are excluded from all export
  paths.

## Testing strategy

Add tests before each implementation slice:

1. Qt mouse-event tests for real text and rectangle drags, including widget
   stacking and stable axis limits.
2. Controller transition tests for create, text edit, commit, cancel, move,
   resize, and one-command undo.
3. Cross-mode tests asserting the same geometry record produces equivalent
   persisted bounds in static and generated documents.
4. Regression tests for log axes, reversed drag direction, zero-size clicks,
   legacy text objects, and Escape during inline editing.
5. Export tests confirming transient artists and input widgets never enter
   output.

## Acceptance criteria

- Text, rectangle, line, arrow, and curve share one tested interaction
  lifecycle in static and generated modes.
- Creating a text object does not change x/y limits, scale type, or apparent
  plot size.
- The visible drag boundary equals the persisted object's editable boundary.
- Text can be typed, moved, resized, cancelled, undone, saved, and reloaded.
- Existing editor workflow, export, and document compatibility tests remain
  green.
