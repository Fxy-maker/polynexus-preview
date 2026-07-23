# Editor Legend Interaction Design

**Date:** 2026-07-23
**Status:** Approved for implementation

## Goal

Make multi-series legends feel stable and directly editable in the chart editor:
they must adapt gracefully to a narrow canvas, a click must not change their
appearance, and a double-click must let the user rename each represented
series.

## User-visible behavior

- Automatic multi-series legends show source sample names by default.
- On a wide canvas, legends with more than three entries may use two columns.
  On a narrow canvas they use one column, a smaller readable font, and remain
  inside the upper-right plot area rather than spanning the canvas.
- A single click selects the legend and synchronizes the object tree and
  inspector, but does not recompute its presentation or change its size.
- A double-click on a legend opens a compact modal name editor with one input
  per represented series. Enter accepts all edits; Escape or Cancel leaves the
  document unchanged.
- Accepting names updates the corresponding `plot_series.name` values in one
  undoable operation, redraws once, and immediately refreshes the legend.
- Selection and editing outlines remain editor-only overlays and are excluded
  from normal renderer/export output.

## Architecture

Legend layout is a presentation policy shared by the editor preview renderer
and `MatplotlibFigureRenderer`. It derives only the column count and font size
from the actual available canvas/figure width and number of visible handles;
it never changes the persisted legend geometry (`loc` or
`bbox_to_anchor`). Explicit document `style.ncol` remains an override for
manually configured legends.

The editor adds a legend-specific double-click route next to the existing text
editing route. The modal works with the legend's visible `plot_series` objects,
not the legend object itself, so it preserves legend drag/hide semantics and
the established source-name model.

## Boundaries and non-goals

- This change does not add a generic rich-text editor, inline canvas text
  fields, or additional legend styling controls.
- It does not alter series data, colors, visibility, legend drag behavior, or
  export file formats.
- It does not change a user-selected legend position. Responsive layout is
  visual presentation only.
- Static-image overlays and read-only previews are outside this generated
  figure-document workflow.

## Error handling

- If a legend has no eligible plot series, double-click does nothing and the
  existing selection remains intact.
- Blank names use the existing series naming fallback, avoiding unusable empty
  legend entries.
- Closing or cancelling the dialog applies no document mutation and creates no
  undo entry.

## Verification

Focused tests will cover both preview and export render paths for responsive
legend policy, click stability, and editor dialog save/cancel semantics. The
task then runs the established ChartEditor, figure-store, and render-plan
regression matrix, followed by the structured and default repository checks.

## Acceptance criteria

1. A narrow multi-series canvas renders a compact, single-column, in-plot
   legend in both editor preview and exported figure rendering.
2. A normal-width preview retains the intended two-column layout for five
   sample series.
3. Selecting a legend does not alter its rendered bounding box or layout.
4. Double-click presents editable names; Enter commits all names with one
   undoable change and immediate visual refresh; Escape commits none.
5. Existing legend visibility, dragging, source-name defaults, and export
   behavior remain covered by regression tests.
