---
kind: task
status: completed
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

## Implementation plan

1. Add failing layout and action-surface assertions for readable tool buttons,
   non-scrolling inspector tabs, and object actions beside the layer tree.
2. Rebalance the editor shell, enlarge and group the left tool rail, and apply
   theme-token styling for active, hover, pressed, and disabled states.
3. Add the object action strip using the existing visibility, lock, alignment,
   distribution, grouping, and deletion callbacks.
4. Run the focused editor matrix and repository verifiers, then record the
   exact evidence and known cross-module Qt limitation.

## Acceptance criteria

- [x] Canvas uses available height without a large empty lower region.
- [x] Left tool rail has readable localized labels, grouped actions, active
      states, and accessible tooltips.
- [x] Inspector tabs are visible without horizontal scrolling at normal widths.
- [x] Object-tab action strip exposes visibility, lock, align, distribute,
      group, ungroup, and delete using existing command routes.
- [x] Existing editor behavior and shortcuts remain compatible.
- [x] Focused tests and the repository verifier pass.

## Verification

```bash
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_tool_icons.py tests/test_chart_editor_context_style_mixin.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-20-editor-visual-polish.md --changed --types
python scripts/verify.py --changed --types
```

## Known limitation

Pixel-level comparison of editor screenshots is not part of this task; layout
contracts and widget state are verified through Qt tests.

The single-file editor suite passed (`238 passed`) and the workflow suite passed
(`19 passed`). A combined invocation of those two Qt-heavy modules can still
hit a Windows Qt access violation in the pre-existing `LayerTreeItem.setData`
compatibility path; the failure is non-assertion, varies by test position, and
was isolated from the new layout/action-surface tests (`34 passed`).
