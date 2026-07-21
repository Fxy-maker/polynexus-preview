# Navigation toolbar interaction conflict

## Goal

Prevent Matplotlib's pan/zoom navigation toolbar from intercepting direct
annotation gestures in generated object-edit mode.

## Affected boundaries

- ChartEditor layout mode switching and tool-selection routing.
- Generated object-mode canvas gestures and layout/workflow regression tests.

## Non-goals

- No removal of Matplotlib navigation from static preview mode.
- No changes to annotation geometry, document schema, or scientific plotting.

## Acceptance criteria

- [x] The navigation toolbar is hidden while generated object editing is
  active.
- [x] Switching to an annotation tool exits any active pan/zoom mode.
- [x] Generated object-mode canvas gestures are no longer converted into a
  Matplotlib zoom rubber-band.
- [x] Existing layout and workflow tests remain green.

## Implementation plan

1. Reproduce the orange zoom rubber-band and confirm the running process uses
   the canonical source worktree.
2. Add a regression test for generated-mode toolbar visibility and navigation
   mode reset.
3. Deactivate navigation mode on tool changes and hide the navigation toolbar
   for generated object editing.
4. Run focused tests and the repository changed/type verifier.

## Verification

```text
python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-21-navigation-toolbar-interaction-conflict.md --changed --types
```
