# Editor strong-feedback interaction design

## Status

The user selected option B, “强反馈模式”, on 2026-07-21. This slice makes
existing editor capabilities visually legible and easier to operate without
changing figure-document schema, scientific rendering, or export behavior.

## Problem

The current editor contains a selection model, layer tree, drag transactions,
and tool actions, but the screen does not make the active target or the next
possible operation obvious. The default tree focus can remain on “背景”, while
canvas annotations have weak or absent selection feedback. Users therefore
cannot reliably tell whether an object is selected, movable, resizable, or
still in a creation gesture.

## Goals

- Make the selected object unmistakable in both static and generated modes.
- Make body movement and handle resizing discoverable without reading docs.
- Keep the toolbar's active tool and one-shot creation state visually explicit.
- Keep the layer tree, canvas selection, and status hint synchronized.
- Preserve existing command history, undo/redo, save/reload, and export paths.

## Non-goals

- No redesign of the scientific plot renderer, axes, or data semantics.
- No new annotation types, document fields, or export formats.
- No replacement of the existing Qt/Matplotlib rendering surfaces.
- No broad inspector redesign in this slice; only feedback needed for direct
  canvas editing is in scope.

## User-visible design

### Canvas feedback

When a text, rectangle, line, arrow, or curve is selected, the canvas shows a
consistent blue selection frame. Box objects show corner handles; segment
objects show endpoint handles; curves also show the control-point handle. Body
hover uses an open-hand cursor, active dragging uses a closed-hand cursor, and
handle hover uses the corresponding resize/curve cursor.

The overlay is transient and excluded from rendered exports. It follows the
same coordinate transform as the object and remains visible during preview
transactions, so dragging down or across the viewport does not make the object
appear to jump.

### Tool and status feedback

The active tool button remains checked and receives an accent treatment. On
tool selection, the status bar gives one short instruction: create, move,
resize, or press Escape to cancel. After selection, it names the object and
describes the available body/handle action. Creation remains one-shot and
returns to Select after commit or cancellation.

### Layer-tree feedback

Canvas selection updates the corresponding tree row and scrolls it into view;
tree selection updates the canvas without changing the viewport. “Background”
is not treated as an active editable target when the user has not selected an
object. Multi-selection remains represented by the existing selection model;
the direct-canvas overlay shows the primary target while the tree preserves
the complete selection set.

## Architecture and data flow

The existing `EditorInteractionController` remains the gesture state owner.
Each canvas adapter emits selection/feedback state, while existing edit-session
commands remain the only mutation and history boundary:

```text
pointer -> hit target -> controller transition -> feedback overlay
                                      |
                                      +-> existing preview transaction
                                      +-> existing edit-session command on release
```

The feedback overlay must not mutate the document. A cancelled or zero-length
gesture leaves no history entry. Locked or unsupported objects show a
not-allowed/status message and remain unchanged.

## Testing and acceptance

- Qt mouse-event tests cover select, hover, body drag, handle drag, Escape,
  and one-shot creation for static and generated annotation objects.
- Focused UI tests assert selected-tree synchronization, active tool styling,
  status instructions, and export exclusion of overlays.
- Existing ChartEditor, AnnotationCanvas, workflow, export, and undo/redo
  suites remain green.

Acceptance is met when a first-time user can answer “what is selected, what can
I drag, and how do I cancel?” from the screen alone, without changing the
underlying figure data or document contracts.
