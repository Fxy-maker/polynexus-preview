# LegendLayout Refactor

## Goal

Replace the editor's split legend geometry interpretations with one resolved
`LegendLayout`, while preserving old documents and the current visual output.

## Non-goals

- No new legend styling or separate Qt legend widget.
- No changes to static-image annotations, curve data, axes algorithms, or
  publication export contracts.

## Affected boundaries

- New pure resolver under `polynexus/core/figures/`.
- Shared figure render-plan/formal/legacy legend presentation.
- `FigureRenderAdapter` selection, hit testing, overlays, and handles.
- ChartEditor drag transactions, inspector geometry, persistence, and export.

## Acceptance criteria

- [ ] Legacy `loc`/two-value and four-value `bbox_to_anchor` documents render
  without visual jumps and are not rewritten on open.
- [ ] Auto and fixed legends both resolve through `LegendLayout`.
- [ ] Selected frame/handles, hit testing, drag, and inspector use the same
  interaction rectangle.
- [ ] Body and corner edits are one undoable transaction and survive reload.
- [ ] Formal, legacy, log-axis, multi-series, and static fallback matrices are
  green; transient overlays never enter exports.
- [ ] Resolver diagnostics replace silent geometry fallbacks.

## Required workflow

1. Write failing resolver/compatibility tests, then implement the pure model.
2. Wire formal and legacy renderers and add renderer parity tests.
3. Wire selection/hit testing/drag/inspector and add transaction tests.
4. Verify persistence/export/static fallback and update memory.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_legend_refactor'
python -m pytest tests/test_legend_layout.py tests/test_figure_render_plan_core.py tests/test_chart_editor.py tests/test_chart_editor_generated_object_helpers.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-24-legend-layout-refactor.md --changed --types
python scripts/verify.py --changed --types
```

## Pre-existing files intentionally untouched

The untracked `.superpowers/`, `.pytest_tmp_*`, and dated design/acceptance
drafts already present in the worktree remain outside this task's allowlist.
