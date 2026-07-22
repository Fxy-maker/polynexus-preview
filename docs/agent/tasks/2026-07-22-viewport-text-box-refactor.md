---
id: 2026-07-22-viewport-text-box-refactor
title: Refactor generated text boxes to viewport-anchored interaction
status: design-approved
scope: architecture, GUI interaction, document compatibility
---

## Goal

Replace the split data-coordinate text-box interaction with one Axes-relative
Box contract that behaves predictably on logarithmic and reversed charts.

## Acceptance criteria

- Text box position and size remain visually stable when axes scale or limits
  change.
- Moving down works on logarithmic axes and does not get intercepted by the
  top-left handle when the pointer is over text content.
- Body movement and corner resizing are separate, predictable transactions.
- Preview, commit, cancel, undo/redo, reload, inspector, and export all use the
  same geometry.
- Existing legacy text documents remain readable and convert on edit/save.
- Focused regression tests and the repository verifier pass.

## Boundaries

- Modify generated text geometry/render/hit/preview/inspector paths and the
  shared document conversion boundary.
- Do not redesign line, curve, plot-series, or static-image annotation tools.
- Do not modify real regression data, generated outputs, or user runtime files.

## Verification commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus\.pytest_tmp_alt'
python -m pytest tests/test_chart_editor_workflow.py tests/test_chart_editor_curve.py tests/test_figure_text_geometry.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-22-viewport-text-box-refactor.md --changed --types
```

## Design reference

See `docs/superpowers/specs/2026-07-22-viewport-text-box-design.md`.
