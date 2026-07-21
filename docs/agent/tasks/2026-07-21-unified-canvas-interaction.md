# Unified canvas interaction

## Goal

Deliver the user-approved unified canvas interaction: text, rectangle, line,
arrow, and curve share the same dragged geometry, stable viewport, selection
feedback, movement/resizing, and one-step undo in generated and static modes.

## Affected boundaries

- ChartEditor generated Matplotlib interaction and `FigureRenderAdapter`.
- Static `AnnotationCanvas` Qt scene interaction.
- Shared editor geometry helpers and focused GUI regression tests.

## Non-goals

- No replacement of PySide6, Matplotlib, or the scientific rendering stack.
- No change to data-source binding, analysis semantics, or figure-document
  object ids.
- No deletion, merge, push, deploy, or cleanup of existing user drafts.

## Implementation plan

1. Add and test immutable `Box`, `Segment`, and `Curve` records with legacy
   payload adapters.
2. Route generated text and rectangle creation, selection frames, body drags,
   and text corner resizing through `Box` while preserving the viewport.
3. Route static text and rectangle creation through the same normalized box
   contract while preserving existing Qt scene undo and export behavior.
4. Run the focused cross-mode matrix and repository verifier, then record
   evidence and known limitations.
- No scientific analysis, data-source semantics, renderer replacement, or
  destructive cleanup of user drafts.

## Acceptance criteria

- [x] A text drag uses one box for preview, inline input, selection handles,
  commit, save, and reload.
- [x] Text and rectangles can be moved by their body and resized by handles;
  lines/arrows/curves keep endpoint/control-point editing.
- [x] Reversed drags are valid and zero-size clicks use a visible minimum box.
- [x] Creating, moving, or resizing an object does not change axis limits,
  scale types, figure size, or apparent plot zoom.
- [x] Each completed gesture creates one undoable edit; Escape creates none.
- [x] Static and generated exports exclude transient previews, frames, handles,
  and the inline editor.
- [x] Existing editor workflow and document compatibility tests remain green.

## Verification

Use the independent temporary directory while the local preview server owns the
repository `.pytest_tmp` directory:

```text
python -m pytest tests/test_editor_geometry.py tests/test_editor_interaction_controller.py tests/test_chart_editor_workflow.py tests/test_annotation_canvas.py tests/test_figure_render_adapter.py -q --basetemp D:\\PolyNexus\\.pytest_tmp_alt
python scripts/verify.py --task docs/agent/tasks/2026-07-21-unified-canvas-interaction.md --changed --types
python scripts/verify.py --changed --types
```

## Evidence

- 2026-07-21: Added immutable shared geometry records in commit `e34ed75`.
- 2026-07-21: Generated box preview, text anchoring, and text resize behavior
  landed in commits `814d9f5` and `d24cc8b`.
- 2026-07-21: Static reversed text/rectangle creation now uses the normalized
  box contract in commit `d0b297b`.
- Focused cross-mode matrix: `141 passed` with four existing Matplotlib tight-
  layout warnings on logarithmic text tests.
- Structured verifier passed with the independent basetemp override:
  `PYTEST_ADDOPTS=--basetemp=D:\\PolyNexus\\.pytest_tmp_alt python scripts/verify.py
  --task docs/agent/tasks/2026-07-21-unified-canvas-interaction.md --changed
  --types`; quality gate `282 passed`, preprocessing gate `103 passed`, and
  whitespace checks passed.
- Default verifier was also attempted without the override and was blocked by
  WinError 5 while the running local preview server owns `.pytest_tmp`; no
  source assertion failed in that run.

## Known limitations

- The repository default `pytest.ini` basetemp remains unsuitable while the
  local preview server is serving from `.pytest_tmp`; use the documented
  independent basetemp override until that process is stopped.
- Matplotlib text wrapping remains renderer-native; the persisted box controls
  selection, movement, and resizing, while line wrapping follows Matplotlib's
  `wrap` behavior.
