# Unified editor interaction architecture

## Status

Approved direction from the user on 2026-07-21. This design addresses the
interaction gap between PolyNexus, PowerPoint, and Origin without changing the
scientific rendering or document schema.

## Problem

The editor currently exposes one toolbar over two different interaction
implementations. Static figures use the Qt `AnnotationCanvas`; generated
figures use Matplotlib canvas callbacks split across several mixins. The same
tool therefore has different creation, selection, hit-testing, cursor, and
undo behavior depending on the source mode. Matplotlib navigation can also
compete with annotation gestures.

## Goals

- Make Select the stable default tool in both modes.
- Make creation tools one-shot: complete a gesture, commit one command, and
  return to Select.
- Give text, line, arrow, curve, and rectangle a shared selection/drag/resize
  contract.
- Keep text editing inline and predictable: click/drag to place a box, type,
  Enter commits, Escape cancels.
- Make hover, cursor, selection handles, and status hints describe the same
  operation in both modes.
- Keep `FigureDocument`/`EditSession` as the persistence and undo authority.
- Keep Matplotlib responsible for chart rendering, axes, and export; GUI
  interaction must not depend on Matplotlib navigation state.

## Non-goals

- Replacing Matplotlib's scientific rendering, axes, scales, or export stack.
- Changing figure document object ids, geometry field names, or command history
  semantics.
- Adding general CAD/freehand drawing or changing plot-series data editing.
- Rebuilding the entire ChartEditor window layout in this slice.

## Architecture

### Interaction state

Add a small Qt-independent interaction controller with explicit states:

```text
SELECT_IDLE -> CREATING -> TEXT_EDITING -> SELECT_IDLE
SELECT_IDLE -> BODY_DRAGGING -> SELECT_IDLE
SELECT_IDLE -> HANDLE_DRAGGING -> SELECT_IDLE
any active state -> CANCELLED -> SELECT_IDLE
```

The controller owns only tool, gesture state, pointer coordinates, selected
object id, and the current handle. It emits transition records; it does not
render, mutate the document, or know about Matplotlib internals.

### Canvas adapter contract

Both canvases consume the controller through a narrow adapter contract:

- `set_tool(tool)` and `current_tool()`
- `hit_test(pointer) -> HitTarget | None`
- `begin_create(pointer)`, `update_create(pointer)`, `finish_create(pointer)`
- `begin_drag(target, pointer)`, `update_drag(pointer)`, `finish_drag()`
- `cancel_gesture()`
- `feedback_for(target)` for cursor and status text

The adapters translate accepted gestures into existing `AddObjectCommand`,
`UpdateGeometryCommand`, and replacement/transaction commands. A failed or
cancelled gesture does not create document history.

### Generated chart interaction surface

Generated charts retain the Matplotlib figure as the render surface. The
interaction layer uses the active axes transform only for coordinate mapping;
it owns annotation hit targets and selection handles. Matplotlib navigation is
disabled in object mode. Plot-series selection remains the existing fallback
until its adapter is migrated to the same contract.

### Static annotation surface

`AnnotationCanvas` remains the Qt scene implementation, but its tool lifecycle
and transition notifications are normalized to the same controller contract.
This preserves its existing high-quality pixel-space resize behavior while
removing divergent toolbar semantics.

## User-visible behavior

- Select is active after opening, after completing any creation, and after
  cancelling with Escape.
- Clicking a visible annotation selects it and shows an object frame/handles.
- Dragging inside the object moves it; dragging a handle changes its geometry.
- Text enters inline editing only after a completed placement gesture, and the
  editor is positioned in the same canvas coordinate system as the object.
- The active tool has a checked button, matching cursor, and short status hint.
- The top Matplotlib pan/zoom toolbar is unavailable in generated object mode,
  so a rectangle drag cannot silently become a zoom operation.

## Error handling

- Unsupported or locked objects produce a status hint and remain unchanged.
- Missing transforms or invalid pointer coordinates cancel the gesture safely.
- Empty text commits are discarded and return to Select.
- Existing corrupt-document diagnostics remain the visible load failure path.

## Verification strategy

- Pure controller transition tests cover every state and cancellation path.
- Static and generated adapter tests cover tool lifecycle and command proposals.
- Qt tests send actual `QMouseEvent` press/move/release sequences to the
  canvas, including text, line, curve, and rectangle interactions.
- Existing ChartEditor workflow, export, undo/redo, and document compatibility
  tests remain part of the changed/type verifier.
