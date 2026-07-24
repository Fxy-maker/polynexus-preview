# Editor Legend Box

## Goal

Make generated ChartEditor legends visually stable on selection and editable as
draggable, resizable Origin-style boxes.

## Boundaries

- Shared legend presentation and generated ChartEditor interaction only.
- Reuse `UpdateStyleCommand` and the existing undo/persist/export path.

## Affected boundaries

- `style.box_size` presentation in shared Matplotlib rendering.
- Generated ChartEditor selection, canvas drag, inspector geometry, and undo.
- Existing legend persistence and export behavior.

## Implementation plan

1. Make persisted legend typography and box dimensions render-authoritative.
2. Draw transient, non-exported selection framing and four handles.
3. Route body and corner drags through the existing undoable style command.
4. Run the focused matrix and changed-file verification, then record evidence.

## Non-goals

- No changes to curve data, axes, static image annotations, or publication
  format contracts.

## Acceptance criteria

- [x] Selection does not change legend columns or font size.
- [x] A selected legend shows a non-exported frame and four resize handles.
- [x] Body and corner drags are persisted and undoable.
- [x] Explicit legend font size survives redraw, save, reload, and export.
- [x] Existing legend rename and automatic layout regressions remain green.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_box'
python -m pytest tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-24-editor-legend-box.md --changed --types
```

## Evidence

- `10d4c61` adds one undoable `UpdateStyleCommand` for legend-corner drags,
  persistent axes-fraction W/H, and a matching transient display-space box.
- 2026-07-24 focused matrix: `272 passed`.
- 2026-07-24 changed-file verifier: passed with
  `PYTEST_ADDOPTS=--basetemp=D:\PolyNexus\.pytest_tmp_legend_box_verify`;
  quality gates: `282 passed` and `103 passed`.
