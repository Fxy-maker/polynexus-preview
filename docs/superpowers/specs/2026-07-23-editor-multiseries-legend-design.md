# Editor Multi-Series Legend Design

## Goal

Make an object-mode chart with multiple visible plot series immediately
readable by showing a compact legend whose entries use the existing sample
names and remain editable through the ChartEditor.

## Chosen interaction

- When an object-mode figure has two or more visible `plot_series` objects,
  create one persisted legend object only if the document has no explicit
  legend state.
- Each legend entry uses the corresponding series `name` verbatim. The editor
  does not infer, abbreviate, or reformat scientific labels.
- Renaming a plot series through the existing object inspector updates the
  rendered legend on the same refresh.
- The legend remains a normal editor object: its visibility control hides or
  shows it, and direct canvas dragging persists its position.
- A generated legend starts in the upper-right, without a frame. A compact
  two-column layout is used when the entry count warrants it, so dense
  multi-curve figures remain legible without obscuring the data.
- Existing explicit legend visibility and placement always win over automatic
  defaults. Single-series figures do not gain a legend.

## Non-goals

- No changes to static-image or source-preview figures.
- No changes to series data, scientific naming semantics, axes, or export
  formats.
- No new legend editor surface; the current object tree, inspector, visibility,
  and drag paths remain the public interaction model.

## Data flow

The object-document renderer derives eligible series and their labels from the
same visible-object store used by the layer tree. It passes these labels to
Matplotlib when rendering and then applies persisted legend style and geometry.
The existing editor rename command updates the series object name, so the next
render uses the changed label without a second label store.

## Acceptance

- A generated object-mode figure with two named visible series displays a
  legend containing exactly those names by default.
- A single-series figure remains legend-free.
- Renaming a selected series updates its legend entry after the ordinary
  render/refresh path.
- Hiding or dragging the legend persists and is not overwritten by later
  automatic-default evaluation.
- Focused renderer/editor regressions cover default labels, rename sync,
  single-series suppression, and explicit legend state preservation.
