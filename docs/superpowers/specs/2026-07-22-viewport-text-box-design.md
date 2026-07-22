# Viewport-Anchored Text Box Design

**Date:** 2026-07-22
**Status:** Approved direction; implementation plan pending review

## Goal

Make editable text boxes behave like PPT/Origin graph annotations: their
position and size stay fixed relative to the chart canvas while the data axes
zoom, pan, reverse, or switch to logarithmic scales.

## Non-goals

- This change does not alter plot data, axis limits, or scientific values.
- Existing line, curve, rectangle, legend, and plot-series interaction contracts
  remain unchanged except where they share selection/transaction infrastructure.
- Data-bound labels are not removed; they remain a separate future capability.

## Canonical geometry contract

New and edited text objects use an explicit viewport geometry:

```json
{
  "type": "text",
  "coordinate_space": "axes",
  "geometry": {"x": 0.20, "y": 0.65, "width": 0.25, "height": 0.12},
  "text": "Peak",
  "style": {"font_size": 12}
}
```

`x`, `y`, `width`, and `height` are fractions of the target Matplotlib Axes
rectangle. The origin is the lower-left corner; `x`/`y` are normalized to
`[0, 1]` for placement, while width/height are positive normalized extents.
The stored geometry is independent of data coordinates and remains stable on
linear, logarithmic, reversed, and zoomed axes.

The text drawing anchor is derived from this geometry in exactly one shared
helper. The default is left/top with a small visual inset so glyphs do not sit
under the corner handle. Explicit horizontal/vertical alignment remains
supported.

## Interaction architecture

Text boxes use one interaction controller and one transaction state:

1. Convert the persisted Axes-relative `Box` to display pixels through
   `axes.transAxes`.
2. Hit-test the text content/body first; body drags always move the whole Box.
3. Hit-test corner handles only outside the text-content hit region; corner
   drags resize the Box while preserving the opposite corner.
4. During a drag, calculate the new Box entirely in display/axes space, clamp
   it to the Axes rectangle, and render the preview from that same Box.
5. On release, submit one undoable geometry command containing the complete Box;
   Escape restores the original snapshot without creating history.

The same Box drives the artist, selection frame, handles, cursor, inspector
values, hit region, saved document, and subsequent redraw. No drag path will
write directly to a Matplotlib `Text` artist without updating the Box state.

## Legacy compatibility

- Text objects with no `coordinate_space` remain readable.
- On load, legacy data-coordinate text is converted once to Axes-relative
  geometry using the current axes transform and the rendered text extent.
- The converted object is marked `coordinate_space: "axes"` when next saved.
- Existing documents are not rewritten merely by opening them; conversion is
  persisted only after an edit/save operation.
- Legacy unboxed text uses a minimal inferred Box around its rendered extent so
  it can enter the new interaction model without changing its visible text.

## Rendering and export

- Live Matplotlib rendering uses `ax.transAxes` for viewport text and keeps the
  object-to-artist map unchanged.
- Selection frames and handles are editor-only overlays and never enter export.
- PNG/SVG/PDF export renders the text at the persisted Axes-relative position,
  without selection overlays.
- Static image annotations continue using the existing pixel-normalized canvas
  path until that separate mode is migrated.

## Verification and acceptance

Focused tests must cover:

- create, move up, move down, left, and right on a logarithmic axis;
- zoom/pan/reverse axis without changing the text box's screen placement;
- body-vs-handle hit priority and four-corner resize;
- preview, commit, Escape cancellation, undo, redo, reload, and export;
- legacy data-coordinate text conversion and unboxed-text compatibility;
- inspector geometry edits using the same Axes-relative contract.

Acceptance is met when the same persisted Box produces the same visual frame,
text position, hit region, and control values before and after redraw, and when
the focused editor matrix plus `python scripts/verify.py --changed --types`
pass.
