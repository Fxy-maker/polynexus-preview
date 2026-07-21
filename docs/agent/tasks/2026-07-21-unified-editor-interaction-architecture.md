# Unified editor interaction architecture

## Goal

Close the interaction gap with PowerPoint and Origin by giving static and
generated charts one predictable tool, selection, drag, resize, text-edit, and
cancel contract.

## Affected boundaries

- ChartEditor toolbar/tool routing and generated-canvas gesture handling.
- `AnnotationCanvas` tool lifecycle and shared edit-session command proposals.
- New Qt-independent interaction controller and focused GUI regression tests.
- No scientific analysis, figure document schema, or export semantics.

## Non-goals

- No replacement of Matplotlib's render/export engine.
- No freehand/CAD toolset or plot-series data editing redesign.
- No deletion of pre-existing user drafts, worktrees, or runtime data.

## Acceptance criteria

- [x] Select is the default and creation tools return to Select after commit or
  cancellation in both static and generated modes.
- [x] Text, line, arrow, curve, and rectangle share the same body-drag,
  handle-drag, cursor, and status-feedback contract.
- [x] Generated object mode cannot enter Matplotlib pan/zoom while using an
  annotation tool.
- [x] Text placement opens an inline editor at the placed box; Enter commits,
  Escape cancels, and empty text creates no object.
- [x] Static and generated edits still use the existing edit-session commands,
  undo/redo, save, reload, and export paths.
- [x] Real Qt mouse-event tests cover the user-visible workflows.

## Implementation plan

1. Add a Qt-independent controller and tests for Select/Creating/TextEditing/
   Dragging/HandleDragging/Cancelled transitions.
2. Normalize `ChartEditor.set_tool()` and `AnnotationCanvas.set_tool()` around
   the controller, including one-shot creation and cancel feedback.
3. Route generated annotation hit targets through the controller while keeping
   Matplotlib as the renderer and using existing edit commands for mutations.
4. Add unified selection-frame/handle feedback and inline text placement tests
   for both canvas modes.
5. Run focused GUI tests, the task verifier, and the default changed/type
   verifier; update durable memory and create an explicit checkpoint.

## Verification

```text
python -m pytest tests/test_editor_interaction_controller.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py -q
python scripts/verify.py --task docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md --changed --types
python scripts/verify.py --changed --types
```

## Evidence

- The controller and renderer-neutral generated hit-target adapter are covered
  by focused unit tests.
- Static creation and dragging are covered by real `QMouseEvent` sequences;
  generated creation, text placement, body dragging, handle dragging, cancel,
  and undo/redo remain covered by the ChartEditor workflow matrix.
- Focused interaction and workflow matrix: `115 passed`; all ChartEditor and
  AnnotationCanvas regressions: `465 passed`.
- Structured and default verifiers pass with Ruff, compile checks, quality gate
  `282 passed`, and preprocessing gate `103 passed`.

## Known limitations

- Generated rendering and the existing object-specific geometry helpers remain
  Matplotlib-backed by design; the new adapter standardizes the interaction
  target and lifecycle without changing scientific rendering or document
  schema semantics.
