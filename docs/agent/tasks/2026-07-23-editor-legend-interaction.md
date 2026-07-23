# Editor Legend Interaction

## Goal

Finish the generated-chart legend interaction: responsive compact presentation,
layout-stable selection, and batch sample-name editing on double-click.

## Affected boundaries

- Shared Matplotlib legend presentation policy.
- ChartEditor generated preview rendering and pointer routing.
- Qt modal input lifecycle and generated-document undo/persistence path.
- Focused renderer and editor regressions.

## Non-goals

- No changes to source data, scientific analysis, series style, legend drag,
  export formats, static overlays, or read-only previews.
- No generic inline rich-text system or new inspector styling surface.

## Acceptance criteria

- [ ] Five automatic named series use two columns on wide canvases and a
  smaller single-column legend inside the plot on narrow canvases.
- [ ] A normal legend click selects it without altering bounds, placement, or
  persisted legend style.
- [ ] Double-click opens one name field per represented series; Enter commits
  all nonblank edits through one undoable document change and refreshes once.
- [ ] Esc/Cancel leaves the figure document untouched.
- [ ] Preview and formal renderer share the same automatic presentation policy.
- [ ] Existing default names, visibility, drag, selection overlay, and export
  behavior remain green.

## Implementation plan

`docs/superpowers/plans/2026-07-23-editor-legend-interaction.md`

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_figure_object_store.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py -q

$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python scripts/verify.py --task docs/agent/tasks/2026-07-23-editor-legend-interaction.md --changed --types
python scripts/verify.py --changed --types
```

## Working contract

- Preserve the existing untracked drafts and diagnostics.
- Apply only the explicit legend-interaction file allowlist to task commits.
- Do not push, merge, deploy, remove data, or modify generated runtime output.
