---
kind: task
status: in_progress
date: 2026-07-20
title: Chart editor visual polish and interaction surface
---

# Chart editor visual polish

## Goal

Make the editor visually coherent and comfortable for frequent chart editing,
with a readable left tool rail, balanced canvas/inspector layout, and common
object actions placed beside the layer tree.

## Non-goals

- Do not change scientific rendering or figure-document semantics.
- Do not add a second command path around `EditSession`.
- Do not edit generated outputs, real datasets, or unrelated GUI pages.

## Affected boundaries

- `ChartEditor` shell layout and inspector drawer
- Editor tool rail and contextual style surface
- Object inspector action strip
- Theme-aware editor widget styling
- Focused Qt regression tests

## Acceptance criteria

- [ ] Canvas uses available height without a large empty lower region.
- [ ] Left tool rail has readable localized labels, grouped actions, active
      states, and accessible tooltips.
- [ ] Inspector tabs are visible without horizontal scrolling at normal widths.
- [ ] Object-tab action strip exposes visibility, lock, align, distribute,
      group, ungroup, and delete using existing command routes.
- [ ] Existing editor behavior and shortcuts remain compatible.
- [ ] Focused tests and the repository verifier pass.

## Verification

```bash
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_tool_icons.py tests/test_chart_editor_context_style_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-visual-polish.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitation

Pixel-level comparison of editor screenshots is not part of this task; layout
contracts and widget state are verified through Qt tests.
