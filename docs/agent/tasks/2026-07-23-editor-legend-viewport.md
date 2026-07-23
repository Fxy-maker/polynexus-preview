# Editor Legend Viewport and Typography

## Goal

Prevent long legends from shrinking formal ChartEditor plots and make legend
font size a persistent, undoable editor property.

## Affected boundaries

- Shared legend policy and formal Matplotlib rendering context.
- Manifest-backed ChartEditor preview construction.
- Figure-object edit capability and existing style-command flow.

## Non-goals

- No changes to plot data, series styles, axes, legend drag coordinates,
  publication file formats, or a new dedicated legend panel.

## Acceptance criteria

- [x] Five long sample names in a narrow formal editor viewport select a safe
  layout without collapsing the plot area.
- [x] Wide publication output keeps its independent intended layout.
- [x] Legend font size is enabled, saved, undoable, and identical in preview
  and export.
- [x] Explicit legend font size overrides automatic compact scaling.
- [x] Existing legend selection, drag, rename/cancel, and text double-click
  regressions remain green.

## Implementation plan

1. Make the pure legend policy account for visible label width and optional
   preview viewport width.
2. Supply live canvas width only to the manifest ChartEditor preview renderer.
3. Enable and render the existing legend `style.font_size` through the normal
   style-command/undo pipeline.
4. Verify focused renderer/editor coverage and repository checks.

Detailed steps: `docs/superpowers/plans/2026-07-23-editor-legend-viewport.md`.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_figure_edit_capabilities.py tests/test_figure_object_store.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_manifest_editor_shared_plan.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-23-editor-legend-viewport.md --changed --types
python scripts/verify.py --changed --types
```

## Completion evidence

- 2026-07-23: focused editor/render matrix passed (`291 passed`).
- 2026-07-23: structured and default changed/type verification passed.  The
  repository's configured `.pytest_tmp` directory has an inherited Windows
  access restriction, so those verifier invocations used an explicit isolated
  `PYTEST_ADDOPTS=--basetemp=D:\PolyNexus\.pytest_tmp_verify`; no existing
  scratch directory was modified.

## Working contract

- Preserve existing untracked drafts and diagnostics.
- Commit only the explicit task allowlist; do not push, merge, deploy, or edit
  generated runtime output.
