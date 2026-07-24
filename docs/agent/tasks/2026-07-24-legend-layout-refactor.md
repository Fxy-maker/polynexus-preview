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

- [x] Legacy `loc`/two-value and four-value `bbox_to_anchor` documents render
  without visual jumps and are not rewritten on open.
- [x] Auto and fixed legends both resolve through `LegendLayout`.
- [x] Selected frame/handles, hit testing, drag, and inspector use the same
  interaction rectangle.
- [x] Body and corner edits are one undoable transaction and survive reload.
- [x] Formal, legacy, log-axis, multi-series, and static fallback matrices are
  green; transient overlays never enter exports.
- [x] Resolver diagnostics replace silent geometry fallbacks.

## Implementation plan

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

## Evidence

- Task 1 resolver red/green cycle: `5` new compatibility tests plus the
  existing renderer core matrix passed.
- Task 2 formal/legacy parity: renderer core matrix `28 passed`.
- Task 3 selection/geometry: full `tests/test_chart_editor.py` matrix
  `247 passed`.
- Task 4 legend interaction matrix: `29` legend tests and `34` combined
  drag/undo/helper tests passed; fixed edits normalize to `loc="lower left"`.
- Final focused matrix: `292 passed` with an external Windows pytest base
  directory.
- Structured verifier: `python scripts/verify.py --task
  docs/agent/tasks/2026-07-24-legend-layout-refactor.md --changed --types`
  passed; quality gate `282 passed`, preprocessing gate `103 passed`.
- Chromium visual companion was unavailable because the local executable is
  not installed; GUI visual walkthrough remains a manual follow-up.
