# Origin Editor Inspector Layout Design

**Date:** 2026-07-17

## Goal

Reorganize the Origin-style chart editor around a canvas-first workflow with a
context-sensitive Inspector panel. The editor keeps its current object,
style, annotation, save, publish, and export capabilities, but presents them
according to the user's current task instead of as one long scrolling form.

## Problem

The current editor builds one `QScrollArea` containing a `QFormLayout`. Object
selection, geometry, style presets, chart style, annotations, zoom, save,
publish, and export controls are placed sequentially in that panel. This makes
the canvas less prominent and forces users to scan unrelated controls.

The editor already distinguishes object-document mode from static-background
mode and already has a figure-entry context. The redesign must make those
states visible and easier to understand without changing the document schema,
rendering model, or figure-entry contract.

## Selected approach

Use a canvas-first split layout:

```text
Header: figure identity | mode | dirty state | undo/redo | save | export

Main area:  canvas (about 70%) | Inspector (about 30%)

Inspector groups: Object | Style | Annotation | Export
Footer: selection hint | operation status | zoom
```

The Inspector remains visible on desktop by default and can be collapsed or
resized. The canvas remains the primary interaction surface.

## Scope

### In scope

- Replace the visually flat side-panel hierarchy with four logical Inspector
  groups.
- Make the Inspector content follow the selected object and current editor
  mode.
- Add a compact header showing figure identity, editing mode, dirty state, and
  primary actions.
- Consolidate save/export presentation while preserving current operations.
- Keep object mode and static-background mode behavior unchanged.
- Preserve existing source-entry, style hydration, annotation persistence, and
  export contracts.
- Add focused UI-state and interaction regression tests.

### Out of scope

- Changing figure document or manifest schemas.
- Replacing the renderer or object model.
- Adding new plotting primitives.
- Implementing a full multi-panel object editor.
- Changing gallery discovery or strict entry routing.
- Redesigning the annotation canvas internals.

## User-facing behavior

### Header

The header shows:

- human-readable figure title, with the figure ID available as secondary text
- `Object Editing` or `Static Background` mode badge
- dirty state: `Saved`, `Unsaved changes`, or `Publishing`
- Undo and Redo actions
- one primary `Save` action
- an `Export` menu containing Save As Copy, PNG, SVG, and Publish when allowed

The current target path remains available in a tooltip or secondary details
area, but is not the primary figure identity shown to the user.

### Inspector groups

#### Object

Shown first for object-document mode. It contains the object list, selected
object summary, editable geometry, and object ordering actions. When no object
is selected, it shows a short instruction and figure-level selection state.

For static-background mode, it shows the annotation object list and makes the
mode limitation explicit rather than presenting disabled chart-object fields
as if they were available.

#### Style

Contains title, axis labels, colour scheme, font size, line width, figure size,
grid, grid alpha, background, and style presets. It should show figure-level
controls when nothing is selected and selected-object controls when the
document supports them.

#### Annotation

Contains text, annotation style, line/arrow/rectangle/highlight tools, crop,
copy/paste, front/back, annotation undo/redo, and zoom controls. Annotation
tools remain available in static-background mode.

#### Export

Contains the current target, output format, resolution where supported, save
as copy, publish status, and the existing export actions. It should explain
the difference between a working edit, a saved copy, and published complete
assets.

Only one group needs to be expanded by default. The last expanded group may
be remembered per editor session, but switching figures must reset to the
default group when the new figure changes mode.

### Canvas and footer

The canvas should occupy most of the available editor area. Selecting an
object on the canvas selects the corresponding Inspector item and selecting an
item in the list highlights the canvas object.

The footer keeps transient feedback visible without competing with the canvas:

- hover hint, such as `Drag point` or `Click to select`
- selected object and operation status
- zoom level and fit controls

## Component boundaries

Keep the existing `ChartEditor` as the composition root, but split the new
presentation responsibilities into focused widgets or mixins:

- `EditorHeader`: identity, mode, dirty state, primary actions
- `EditorInspector`: group navigation and mode-aware content
- `EditorCanvasShell`: canvas, splitter sizing, and canvas/Inspector sync
- `EditorStatusBar`: hover, selection, save, and export feedback

Existing document, render, annotation, and save mixins remain the source of
behavior. The new presentation layer calls their existing handlers instead of
duplicating persistence or rendering logic.

## State and data flow

1. `set_source_figure_entry()` loads the selected figure and establishes the
   existing source-entry context.
2. The editor determines object or static mode using the existing compatibility
   gate.
3. The header receives identity, mode, and target metadata.
4. The Inspector receives the current mode and selected-object payload.
5. Canvas selection updates the Inspector; Inspector selection updates the
   canvas through the existing selection model.
6. Any edit marks the editor dirty and updates the status bar.
7. Save and publish actions reuse the existing save mixin and update dirty and
   revision state from their result.

No new persisted state is required for the first delivery slice. Existing
   edit, annotation, and figure-document persistence remains authoritative.

## Error handling

- If figure identity metadata is missing, show the source filename as a
  fallback and keep the editor usable.
- If object mode is rejected by the existing compatibility gate, show static
  mode and the reason in the mode summary.
- If saving or publishing fails, keep the dirty state and show the error in the
  status bar; do not imply success through a header badge.
- If a selected object disappears after a document refresh, clear selection,
  return the Inspector to figure-level controls, and keep the canvas usable.
- If a panel is too narrow, collapse secondary labels before shrinking the
  canvas below its minimum usable size.

## Performance and accessibility

- Preserve the current canvas renderer and avoid full re-render loops caused by
  panel visibility changes.
- Debounce high-frequency text edits before rendering, while keeping direct
  drag feedback immediate.
- Give header actions, Inspector groups, and selection states keyboard focus
  and accessible names.
- Preserve keyboard operations for Delete, Copy, Paste, and add standard
  shortcuts for Undo, Redo, and Save.

## Testing

- Widget construction test verifies the header, canvas, Inspector, and footer
  are present and the Inspector groups are reachable.
- Mode test verifies object mode exposes chart-object editing and static mode
  exposes annotation editing with an explicit limitation summary.
- Selection synchronization test verifies canvas selection and Inspector list
  selection update one another.
- Dirty-state test verifies an edit changes the header to unsaved and a
  successful save returns it to saved.
- Export presentation test verifies existing Save As, PNG, SVG, and Publish
  handlers remain reachable from the new layout.
- Source-switch regression test verifies figure identity, mode, selection, and
  expanded Inspector group do not leak from the previous figure.
- Existing focused chart-editor, annotation-canvas, save, and strict-entry
  tests must remain green.

## Acceptance criteria

- A user can identify the current figure and editing mode without reading a
  file path.
- The canvas remains the dominant area at the default editor size.
- The user can reach object, style, annotation, and export controls without
  scanning one long unrelated form.
- Selection feedback is visible in both the canvas and Inspector.
- Save state is visible and accurate after edit, save, and publish operations.
- Object/static behavior and persisted output remain backward compatible.
- The redesign is test-covered without introducing a second persistence model.
