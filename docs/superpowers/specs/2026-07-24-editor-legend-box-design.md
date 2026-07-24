# Editor Legend Box Design

## Goal

Make a generated ChartEditor legend behave as an Origin-style editable box:
selection must not change its visual layout, body drag moves it, and corner
handles resize its available layout area.

## Observed problem

The current legend persists only `loc` and `bbox_to_anchor`.  Its selected
state therefore has no real W/H geometry, and the selection/render paths can
recompute columns or font size differently from the unselected preview.  A
generic style pass can also overwrite an explicitly stored legend font size.

## Design

### Persistent document contract

A legend's `style` gains an optional `box_size` pair in axes-fraction units:
`[width, height]`.  It represents the usable legend layout box whose upper-left
corner is `bbox_to_anchor` with `loc="upper left"`.  Missing `box_size` keeps
the existing automatic layout and remains backwards compatible.

`font_size` remains an explicit style property.  A positive explicit value is
never replaced by responsive compact scaling or the editor-wide tick size.

### Rendering policy

The shared legend presentation policy receives optional box dimensions.  When
a width is present, it chooses the largest safe column count that fits the
known labels inside that width.  Height is kept as a persisted interaction
boundary and protects a minimum readable layout; it does not clip legend text.
Exports and previews use the same stored dimensions, while automatic legends
without a box preserve their current responsive policy.

### Canvas interaction

Selecting a legend overlays a transient blue dashed display-space frame and
four corner handles around the current rendered legend extent.  The overlay is
not a Matplotlib legend frame and does not participate in export.

- Drag inside the frame: move the upper-left anchor.
- Drag a corner handle: update `box_size`, preserving a positive minimum size.
- Release: commit one undoable style update containing only changed anchor and
  box values; Escape restores the pre-drag document.

The inspector exposes the same X, Y, W, and H values for the selected legend.

### Non-goals

- No automatic renaming, curve editing, or axis changes.
- No text clipping, arbitrary border styling, or separate legend panel.
- Static-image annotation mode remains unchanged.

## Acceptance criteria

1. Selecting a legend leaves its columns and font visually unchanged.
2. A selected legend shows a frame and four handles that do not export.
3. Corner drag persists positive W/H, redraws immediately, and is undoable.
4. A stored explicit font size stays effective after selection, redraw, save,
   reload, and export.
5. Existing legend body drag, double-click rename, and automatic responsive
   behavior without `box_size` remain intact.
