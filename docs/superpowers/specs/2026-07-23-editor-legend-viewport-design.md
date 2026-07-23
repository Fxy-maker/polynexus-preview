# Editor Legend Viewport and Typography Design

**Date:** 2026-07-23
**Status:** Approved for implementation

## Goal

Make long multi-series legends usable in the live ChartEditor without changing
the intended export layout, and make legend type size a real editable,
undoable document property.

## Chosen approach

The formal renderer will accept an optional editor-only viewport width. Export
and publication calls keep using their figure-plan width. When previewing a
manifest-backed document, ChartEditor supplies its actual drawable canvas
width before the renderer creates the legend, so the same rendering policy is
used with the correct context rather than resizing an already-chosen layout.

The policy will choose the widest usable column arrangement by measuring the
rendered legend against a strict viewport budget. If two long-name columns
would encroach on the plot region, it falls back to one column before the axes
are laid out. A normal export remains free to use two columns when its larger
publication canvas has room.

## Legend type controls

- `style.font_size` becomes supported for `legend` objects and is exposed
  through the existing selection font-size control.
- A user-selected legend font size is persisted, undoable, and honored by
  editor preview and formal export.
- Automatic compact scaling applies only when a legend has no explicit font
  size. It never silently overwrites the user's chosen value.
- Existing drag position, visibility, series-name dialog, and selection-only
  overlay behavior remain unchanged.

## Boundaries

- No changes to plot data, axis scales, series names, or publication asset
  formats.
- No separate legend editor panel. The existing font-size field remains the
  single visible size control; automatic column selection stays responsive.
- The persisted position (`loc`, `bbox_to_anchor`) remains independent of
  viewport layout and is not mutated during redraw.

## Acceptance criteria

1. The screenshot-shaped case—five long sample names in a narrow formal
   ChartEditor viewport—keeps a readable plot area and uses a non-overflowing
   legend arrangement.
2. The same document rendered for a wide formal export still has the intended
   publication layout.
3. Selecting a legend enables the existing font-size field; changing it
   updates only that legend, survives redraw/export, and can be undone.
4. Automatic responsive sizing never replaces an explicit legend font size.
5. Existing text double-click, legend drag, visibility, rename/cancel, and
   multi-panel filtering regressions remain green.

## Verification

Tests will exercise both manifest-backed formal preview and export contexts,
plus legend style edit/undo/export round trips. The final task runs the
existing object-store, formal renderer, ChartEditor, and structured verifier
matrix.
