# Legend Object Geometry

## Goal

Replace the split legend placement interpretations with one runtime
`LegendGeometry` so the visible legend, selection frame, handles, hit testing,
drag/resize preview, undo/redo, persistence, and export always agree.

## Non-goals

- Replacing Matplotlib as the plotting/export backend.
- Changing static-image annotations, scientific data, axes scales, or panel
  semantics.
- Adding new legend styling controls beyond existing font/column presentation.

## Affected boundaries

- Core legend geometry/import/serialization under `polynexus/core/figures/`.
- Shared Matplotlib renderer and legacy generated-document renderer.
- `FigureRenderAdapter` display-space measurement and overlays.
- Generated ChartEditor selection, preview, drag, undo, and status paths.
- Legend, renderer, editor, and export regression tests.

## Acceptance criteria

- [ ] Runtime code uses one `LegendGeometry`; no editor path directly interprets
  `loc`, `bbox_to_anchor`, or `box_size`.
- [ ] New saves use `style.legend_geometry`; legacy fields are read only by one
  importer and remain readable during migration.
- [ ] The selection frame and handles equal the live legend display bounds.
- [ ] Body move and corner resize keep content, frame, handles, and hit testing
  synchronized during preview and after commit.
- [ ] Resize scales font content continuously; body move does not change font.
- [ ] One undo/redo restores position, size, font, and column presentation.
- [ ] Multi-series, single-series suppression, log axes, static fallback, and
  export-overlay isolation remain green.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_object'
python -m pytest tests/test_legend_geometry.py tests/test_legend_layout.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py tests/test_chart_editor_status_service.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-24-legend-object-geometry.md --changed --types
python scripts/verify.py --changed --types
```

## Pre-existing files intentionally untouched

The untracked `.superpowers/`, `.pytest_tmp_*`, dated design/acceptance drafts,
and unrelated local diagnostics remain outside this task's allowlist.

## Design reference

`docs/superpowers/specs/2026-07-24-legend-object-geometry-design.md`
