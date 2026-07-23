# Editor Multi-Series Legend

## Goal

Give generated multi-curve charts a compact default legend based on their
existing sample names, while retaining ordinary ChartEditor rename, visibility,
and drag behavior.

## Affected boundaries

- `FigureObjectStore` legend materialization rules.
- Generated-document Matplotlib legend layout.
- Focused object-store and ChartEditor regressions.

## Non-goals

- No modification of series data or scientific naming.
- No static-image or source-preview figure changes.
- No new legend control surface or export format work.

## Acceptance criteria

- [x] Two or more named visible series show one default legend using their
  names verbatim.
- [x] One series does not gain a legend.
- [x] Renaming a series refreshes the corresponding legend entry.
- [x] Explicit legend visibility and drag position remain intact.
- [x] Five-series legends use a compact two-column arrangement.

## Implementation plan

1. Constrain automatic legend materialization to two or more named, visible
   plot-series objects, without replacing an existing legend object.
2. Give a newly materialized legend compact persisted placement and column
   defaults, then render those defaults through the existing Matplotlib path.
3. Add offscreen regressions for unmodified sample names, rename
   synchronization, one-series suppression, and preserved explicit state.
4. Run the focused matrix and required repository verification, then record
   the exact evidence in agent memory.

Detailed steps: `docs/superpowers/plans/2026-07-23-editor-multiseries-legend.md`.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_figure_object_store.py tests/test_chart_editor.py -q

$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python scripts/verify.py --task docs/agent/tasks/2026-07-23-editor-multiseries-legend.md --changed --types
python scripts/verify.py --changed --types
```
