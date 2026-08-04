---
task_id: 2026-08-04-saxs-gallery-responsive-layout
kind: gui
status: completed
date: 2026-08-04
title: Fix SAXS gallery clipping and Kratky discoverability
---

## Goal

Ensure the generated SAXS Kratky/I(q)q^2 figure is fully visible in the
figure gallery and prevent gallery cards from being clipped at the right edge.

## Non-goals

- Do not change SAXS figure generation or analysis payloads.
- Do not change gallery filtering, selection, editing, or export behavior.

## Affected boundaries

- `polynexus/gui/widgets/chart_viewer.py`
- `tests/test_chart_viewer.py`

## Implementation plan

1. Reproduce the fixed-three-column overflow with three gallery cards at narrow
   and wide viewport sizes.
2. Reflow thumbnail rows using one, two, or three columns based on viewport
   width, including resize events.
3. Verify the gallery has no horizontal overflow and existing gallery routes
   remain green.

## Acceptance criteria

- [x] Narrow gallery view wraps cards instead of clipping the third card.
- [x] Wide gallery view keeps three cards visible without horizontal overflow.
- [x] Generated `Kratky`/`I(q)q^2` card is discoverable as a complete card.
- [x] Existing gallery and startup tests pass.

## Verification

```powershell
python -m pytest -q tests/test_chart_viewer.py tests/test_main_window_figure_mixin.py tests/test_gui_startup.py
python scripts/verify.py --task docs/agent/tasks/2026-08-04-saxs-gallery-responsive-layout.md --changed --types
git diff --check
```

## Evidence

- RED: fixed-three-column test showed all three thumbnails on one row at 900px.
- GREEN: focused ChartGallery/GUI matrix passed (`29 passed`).

## Pre-existing state

The worktree contains unrelated staged, unstaged, deleted, and untracked user
changes. They remain untouched and are excluded from the checkpoint.
