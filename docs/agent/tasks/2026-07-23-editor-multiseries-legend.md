# Editor Multi-Series Legend

## Goal

Give generated multi-curve charts a compact default legend based on their
existing sample names, while retaining ordinary ChartEditor rename, visibility,
and drag behavior.

## Boundaries

- `FigureObjectStore` legend materialization rules.
- Generated-document Matplotlib legend layout.
- Focused object-store and ChartEditor regressions.

## Non-goals

- No modification of series data or scientific naming.
- No static-image or source-preview figure changes.
- No new legend control surface or export format work.

## Acceptance criteria

- [ ] Two or more named visible series show one default legend using their
  names verbatim.
- [ ] One series does not gain a legend.
- [ ] Renaming a series refreshes the corresponding legend entry.
- [ ] Explicit legend visibility and drag position remain intact.
- [ ] Five-series legends use a compact two-column arrangement.

## Plan

`docs/superpowers/plans/2026-07-23-editor-multiseries-legend.md`

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_figure_object_store.py tests/test_chart_editor.py -q

$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python scripts/verify.py --task docs/agent/tasks/2026-07-23-editor-multiseries-legend.md --changed --types
python scripts/verify.py --changed --types
```
