# Editor Style Context Hydration Design

**Date:** 2026-07-12

## Goal

Make the chart editor restore style controls from the currently selected
manifest/generated figure document whenever the user switches figures, without
letting the previous figure's edit state leak into the new figure.

## Scope

In scope:

- `ChartEditor.set_source_figure()` context reset and hydration order.
- Generated/object document style fields: title, axis labels, colour scheme,
  font, line width, figure size, grid state, grid alpha, background, and DPI.
- Regression tests for consecutive document switches and static compatibility.

Out of scope:

- Redesigning the chart editor UI.
- Changing style preset storage or the generated document schema.
- Changing static-image annotation behavior.
- Reworking the old editor architecture.

## Current issue

`set_source_figure()` clears the document and then calls `set_output_target()`
before deciding whether the loaded source is a generated/object document.
`set_output_target()` applies `load_figure_edit()` state immediately. The
generated branch later applies document style controls, but fields absent from
the current document can retain values from the previous figure, and the old
edit state can temporarily become the source of truth for a manifest document.

## Selected approach: centralized hydration boundary

Keep the existing mixins and document schema. Add one small editor method that
establishes the style context for the loaded source:

1. Reset style controls to editor defaults at the beginning of
   `set_source_figure()` after old figure state is cleared.
2. Load the current document and determine whether it is generated/object mode.
3. For generated/object documents, hydrate all available style fields from the
   current document exactly once, then render the document.
4. For static files, preserve the existing `load_figure_edit()` overlay and
   static annotation path.
5. Ensure an absent field means “use the reset default”, never “keep the prior
   figure's value”.

The hydration method should be thin and reuse existing `_set_line_edit`,
`_set_combo`, `_set_font_size`, and grid/DPI handling. It should not create a
second style schema or mutate the persisted document during loading.

## Alternatives considered

### A. Centralized reset + document hydration (selected)

One explicit boundary makes source switching deterministic and retains existing
static compatibility. It is small, testable, and avoids changing preset APIs.

### B. Only reorder existing calls

Move `_apply_generated_document_style_controls()` before
`set_output_target()`. This reduces the symptom in some cases but leaves style
reset and partial-field semantics implicit, so stale controls can still survive.

### C. Introduce a standalone `StyleContext` service

This would provide a clean DTO and broader reuse, but it expands the change into
schema and controller layers without being necessary for this bug.

## Error handling

- Missing or malformed style fields keep the reset/default value.
- Invalid DPI keeps the current default and logs through the existing editor
  logger.
- Missing document paths continue through existing static/empty-source paths.
- No style-loading exception should prevent the selected figure from opening.

## Testing

- Unit-level mixin tests verify that document hydration applies current values
  and that omitted fields do not retain a prior context.
- A source-switch regression test loads document A then document B and asserts
  all controls reflect B.
- Existing static save/edit tests remain green.
- Focused editor tests and changed-file verification are required before
  handoff.
