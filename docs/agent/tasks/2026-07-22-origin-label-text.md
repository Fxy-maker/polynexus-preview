---
id: 2026-07-22-origin-label-text
title: Convert generated text boxes to Origin-style labels
status: planned
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

## Acceptance criteria

- [ ] Selected generated text has a padded frame and four handles tightly
  derived from its rendered extent, never its persisted box dimensions.
- [ ] Dragging the label body keeps the existing Axes-relative move contract.
- [ ] Dragging a text corner previews and commits only `style.font_size` as one
  undoable edit; undo and redo restore the prior and next font sizes.
- [ ] Generated text no longer wraps or clips to the legacy persisted box, and
  the inline editor has one-line height at the rendered label top-left.
- [ ] Double-click editing and selection-free export remain correct.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_figure_text_geometry.py tests/test_figure_render_plan_core.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-22-origin-label-text.md --changed --types
python scripts/verify.py --changed --types
```

## Design reference

`docs/superpowers/specs/2026-07-22-origin-label-text-design.md`
