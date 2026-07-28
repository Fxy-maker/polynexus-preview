---
id: 2026-07-22-viewport-text-box-refactor
title: Refactor generated text boxes to viewport-anchored interaction
status: completed
scope: architecture, GUI interaction, document compatibility
---

## Goal

Replace the split data-coordinate text-box interaction with one Axes-relative
Box contract that behaves predictably on logarithmic and reversed charts.

## Non-goals

- Do not change plot data, axis limits, or scientific analysis semantics.
- Do not redesign line, curve, rectangle, legend, plot-series, or static-image
  annotation interactions.
- Do not rewrite legacy documents merely by opening them; migration is
  persisted only after an edit/save operation.

## Acceptance criteria

- [x] Text box position and size remain visually stable when axes scale or limits
  change.
- [x] Moving down works on logarithmic axes and does not get intercepted by the
  top-left handle when the pointer is over text content.
- [x] Body movement and corner resizing are separate, predictable transactions.
- [x] Preview, commit, cancel, undo/redo, reload, inspector, and export all use the
  same geometry.
- [x] Existing legacy text documents remain readable and convert on edit/save.
- [x] Focused regression tests and the repository verifier pass.

## Affected boundaries

- Modify generated text geometry/render/hit/preview/inspector paths and the
  shared document conversion boundary.
- Do not redesign line, curve, plot-series, or static-image annotation tools.
- Do not modify real regression data, generated outputs, or user runtime files.

## Implementation plan

1. Add the shared Axes-relative text-box contract and preserve legacy document
   normalization.
2. Render and preview marked text boxes through `axes.transAxes`, including
   editor-only frames and handles.
3. Route text body/handle hit testing and drag preview through Axes geometry,
   with body priority over handles for marked text.
4. Keep one undoable geometry command for release, route Inspector edits through
   the same box, and convert legacy text only when saving.
5. Run focused tests, the structured verifier, and diff/type checks; record
   evidence in durable memory.

## Verification

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_figure_text_geometry.py tests/test_figure_document.py tests/test_figure_render_plan_core.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-22-viewport-text-box-refactor.md --changed --types
python scripts/verify.py --changed --types
```

## Evidence

- Axes-relative text creation, rendering, selection overlays, log-axis body
  movement, one-command commit/undo, Inspector edits, legacy save conversion,
  and renderer export behavior are covered by the focused matrix.
- Current focused matrix: `132 passed, 4 warnings in 18.27s` with the same
  pre-existing Matplotlib tight-layout
  warnings from legacy log-axis tests.
- Structured verifier recheck exited `0`, including Ruff, compile, memory
  checks, quality gate `287 passed`, preprocessing gate `106 passed`, type
  baseline, and whitespace checks.
- The implementation checkpoint is `93c17c4`; this documentation-only closure
  preserves that existing production checkpoint.

## Known limitations

- The full desktop GUI acceptance pass was not performed in this checkpoint;
  use the canonical launcher from `D:\PolyNexus` before relying on live visual
  behavior.
- The existing `.pytest_tmp` permission issue remains when a separate local
  process owns that directory; all evidence above uses the isolated
  `D:\PolyNexus\.pytest_tmp_alt` base directory.

## Design reference

See `docs/superpowers/specs/2026-07-22-viewport-text-box-design.md`.
