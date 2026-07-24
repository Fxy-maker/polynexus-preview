# Editor Legend Box

## Goal

Make generated ChartEditor legends visually stable on selection and editable as
draggable, resizable Origin-style boxes.

## Boundaries

- Shared legend presentation and generated ChartEditor interaction only.
- Reuse `UpdateStyleCommand` and the existing undo/persist/export path.

## Non-goals

- No changes to curve data, axes, static image annotations, or publication
  format contracts.

## Acceptance criteria

- [ ] Selection does not change legend columns or font size.
- [ ] A selected legend shows a non-exported frame and four resize handles.
- [ ] Body and corner drags are persisted and undoable.
- [ ] Explicit legend font size survives redraw, save, reload, and export.
- [ ] Existing legend rename and automatic layout regressions remain green.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_box'
python -m pytest tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-24-editor-legend-box.md --changed --types
```
