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

## Implementation plan

1. Introduce `LegendGeometry` as the single importer and runtime geometry
   snapshot, retaining legacy placement parsing only at that boundary.
2. Route the shared renderer, generated renderer, display adapter, selection
   frame, handles, hit testing, and drag previews through measured live bounds.
3. Make body moves and corner resizes use one geometry transaction, with corner
   resize scaling font size continuously and undo restoring geometry and style.
4. Canonicalize edited and saved legend styles to `legend_geometry`, removing
   legacy keys after migration while keeping legacy-only documents readable.
5. Run the focused legend/editor matrix and both structured and default
   repository verification commands; record manual visual review limitations.

## Acceptance criteria

- [x] Runtime code uses one `LegendGeometry`; no editor path directly interprets
  `loc`, `bbox_to_anchor`, or `box_size`.
- [x] Edited saves use `style.legend_geometry`; legacy-only documents are read
  through one importer and remain readable during migration.
- [x] The selection frame and handles equal the live legend display bounds.
- [x] Body move and corner resize keep content, frame, handles, and hit testing
  synchronized during preview and after commit.
- [x] Resize scales font content continuously; body move does not change font.
- [x] One undo/redo restores position, size, font, and column presentation.
- [x] Multi-series, single-series suppression, log axes, static fallback, and
  export-overlay isolation remain green.

## Verification evidence

- Focused legend/editor matrix: `297 passed`.
- Core style migration regression: `54 passed` (included in the matrix's
  relevant core coverage).
- `git diff --check`: passed.
- The viewport-resize regression keeps the live legend, selection frame, and
  four handles aligned after a figure/canvas resize.
- Structured verifier: `python scripts/verify.py --task docs/agent/tasks/2026-07-24-legend-object-geometry.md --changed --types` passed.
- Default verifier: `python scripts/verify.py --changed --types` passed.

## Known limitations

- Manual GUI walkthrough of static images, log axes, and multi-series legends is
  still required after restarting the desktop process; the optional Chromium
  visual companion is unavailable in this environment.

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
