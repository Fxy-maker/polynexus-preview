---
id: 2026-07-22-origin-label-text
title: Convert generated text boxes to Origin-style labels
status: completed
scope: GUI interaction, rendering, document compatibility
---

## Goal

Make generated text annotations behave as compact Origin-style labels: their
selection frame follows the rendered glyphs, their corner handles change font
size, and their existing double-click editor remains a single-line input.

## Non-goals

- Do not alter plot data, axes, scientific semantics, or export formats.
- Do not change line, arrow, curve, rectangle, legend, plot-series, or static
  image annotation interactions.
- Do not rewrite legacy documents merely by opening them, remove legacy
  `width`/`height`, or modify pre-existing untracked drafts.

## Affected boundaries

- Generated ChartEditor text rendering, selection overlays, corner-drag style
  transactions, and the shared inline `QLineEdit` placement path.
- Qt workflow and core figure-render regression coverage for generated labels.
- No scientific-analysis, data schema, static annotation, or export-format
  boundary changes.

## Acceptance criteria

- [x] Selected generated text has a padded frame and four handles tightly
  derived from its rendered extent, never its persisted box dimensions.
- [x] Dragging the label body keeps the existing Axes-relative move contract.
- [x] Dragging a text corner previews and commits only `style.font_size` as one
  undoable edit; undo and redo restore the prior and next font sizes.
- [x] Generated text no longer wraps or clips to the legacy persisted box, and
  the inline editor has one-line height at the rendered label top-left.
- [x] Double-click editing and selection-free export remain correct.

## Implementation plan

1. Add regression coverage for unwrapped label rendering, tight rendered
   selection overlays, font-size corner drags, and compact inline text entry.
2. Render Axes-relative generated text as labels, then base selected overlays
   on the rendered text extent instead of legacy box geometry.
3. Route text corner drags through previewed and undoable font-size updates
   while retaining Axes-relative label-body movement.
4. Make the shared inline `QLineEdit` use a font-metric one-line height and
   record verification evidence in this task card and active-work memory.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_figure_text_geometry.py tests/test_figure_render_plan_core.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-22-origin-label-text.md --changed --types
python scripts/verify.py --changed --types
```

## Verification evidence

- TDD RED: `test_generated_text_box_uses_compact_single_line_inline_editor`
  failed as expected before the implementation (`240 != 24`).
- Focused Qt workflow regression: `3 passed` for compact-height creation,
  double-click top-edge/Enter commit, and Escape cancellation.
- Full label matrix: `87 passed`; the four existing Matplotlib tight-layout
  warnings cover log-axis text tests.
- Structured verifier passed: task-card validation, memory check, Ruff,
  compile, quality gate (`282 passed`), preprocessing gate (`103 passed`), and
  whitespace check.
- Default changed/type verifier passed with the same Ruff, compile, quality,
  preprocessing, and whitespace checks.

## Known limitation

- A running GUI must be restarted before manual visual inspection; the
  automated coverage verifies the Qt workflow offscreen only.

## Design reference

`docs/superpowers/specs/2026-07-22-origin-label-text-design.md`
