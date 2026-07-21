# Editor strong-feedback mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make selection, dragging, resizing, active tools, and layer-tree state visibly obvious in the PolyNexus chart editor while preserving existing document and history contracts.

**Architecture:** Keep `EditorInteractionController` and `EditSession` as the state and mutation authorities. Add pure status-hint helpers, a renderer-owned transient selection frame, and a small tree/toolbar synchronization layer; overlays are recreated with the figure and never enter documents or exports.

**Tech Stack:** Python 3.12+, PySide6, Matplotlib, existing `FigureRenderAdapter`, Qt offscreen tests, pytest, Ruff.

---

### Task 1: Make tool and selection status explicit

**Files:**

- Modify: `polynexus/gui/chart_editor_status_service.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_status_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Test: `tests/test_chart_editor_status_service.py`
- Test: `tests/test_chart_editor_layout.py`

- [ ] **Step 1: Add failing pure status tests.**

  Add cases asserting that each creation tool reports a short creation/cancel
  instruction and that a selected text/rectangle/line/curve reports body and
  handle operations. The tests should call pure helpers with values such as
  `("rectangle", "矩形")` and assert the returned text contains “拖动” and
  “Esc” without constructing Qt widgets.

- [ ] **Step 2: Run the focused tests and confirm the helper API is missing.**

  Run:

  ```text
  python -m pytest tests/test_chart_editor_status_service.py -q -k 'tool_hint or selection_hint'
  ```

  Expected: collection or assertion failure because the new status helpers do
  not exist.

- [ ] **Step 3: Implement pure status helpers and connect them to the editor.**

  Add `build_editor_tool_hint(tool)` and
  `build_editor_selection_hint(object_type, label)` to the status service.
  Update `ChartEditorGeneratedStatusMixin` with `_set_editor_tool_hint()` and
  `_set_editor_selection_hint()` that write to the existing `_status_label`.
  Call the tool helper from `ChartEditorEditSessionMixin.set_tool()` after a
  successful shared-tool change, and call the selection helper from the
  generated/static selection callbacks. Keep the existing warning, drag, and
  cancel messages higher priority than the idle tool hint.

- [ ] **Step 4: Strengthen the active toolbar styling without changing layout.**

  In `_EditorContextToolbar`, set a dynamic `editor-tool-active` property on
  the checked tool button and add a focused stylesheet rule using the existing
  blue accent. Keep the 78px rail width and action ids unchanged so existing
  shortcuts/tests remain compatible.

- [ ] **Step 5: Run status and layout tests.**

  Run:

  ```text
  python -m pytest tests/test_chart_editor_status_service.py tests/test_chart_editor_layout.py -q
  ```

  Expected: all existing layout tests plus the new status tests pass.

- [ ] **Step 6: Commit the status slice.**

  ```text
  python scripts/auto_commit.py --message "feat(editor): clarify tool feedback" --files polynexus/gui/chart_editor_status_service.py polynexus/gui/widgets/chart_editor_generated_status_mixin.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/widgets/chart_editor_layout_mixin.py tests/test_chart_editor_status_service.py tests/test_chart_editor_layout.py
  ```

### Task 2: Add visible generated-object selection frames

**Files:**

- Modify: `polynexus/gui/figure_render_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_selection_mixin.py`
- Test: `tests/test_figure_render_adapter.py`
- Test: `tests/test_chart_editor_workflow.py`

- [ ] **Step 1: Add failing frame tests.**

  Extend the adapter tests to select a text, rectangle, line, and curve and
  assert that the returned overlay artists have a `pn-selection-frame:<id>` gid
  and are separate from the persisted object artists. Add a workflow assertion
  that the frame exists after `_select_generated_object(id, "canvas")` and is
  absent from the artist list captured during export.

- [ ] **Step 2: Implement renderer-neutral frame creation.**

  Add `FigureRenderAdapter.add_selection_frame(ax, figure_object)` returning
  transient Matplotlib artists. Use `bounds` or top-level geometry for boxes;
  use the endpoint/control-point extent for lines and curves; use the rendered
  text artist window extent converted through `ax.transData.inverted()` when
  available, with a small data-space fallback. Style every frame with a blue
  dashed line, no fill, a high z-order, and the `pn-selection-frame:<id>` gid.
  Do not register frames in `_object_id_to_artists`.

- [ ] **Step 3: Add frames before existing handles.**

  In `_add_generated_selection_handles()`, call the new adapter method before
  `add_selection_handles()`. Ensure generated redraws clear old transient
  overlays by rebuilding the figure as they do today. Keep selection handles,
  hover handles, and current handles unchanged for geometry hit-testing.

- [ ] **Step 4: Preserve export behavior and verify the frame visually.**

  Extend the existing export-overlay test to assert that selection-frame gids
  are absent from `Figure.savefig` captures and that the selection remains
  active after export. Run:

  ```text
  python -m pytest tests/test_figure_render_adapter.py tests/test_chart_editor_workflow.py -q -k 'selection or export'
  ```

- [ ] **Step 5: Commit the generated-frame slice.**

  ```text
  python scripts/auto_commit.py --message "feat(editor): show generated selection frames" --files polynexus/gui/figure_render_adapter.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py polynexus/gui/widgets/chart_editor_generated_selection_mixin.py tests/test_figure_render_adapter.py tests/test_chart_editor_workflow.py
  ```

### Task 3: Synchronize static feedback and the layer tree

**Files:**

- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/chart_editor_object_list_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- Test: `tests/test_annotation_canvas.py`
- Test: `tests/test_chart_editor_layout.py`
- Test: `tests/test_chart_editor_workflow.py`

- [ ] **Step 1: Add failing Qt feedback tests.**

  Send real `QMouseEvent` press/move/release events to a static canvas and
  assert that the selected annotation has visible selection-frame/handle items,
  body hover uses an open-hand cursor, and Escape removes the transient frame.
  Add a generated-tree test asserting canvas selection calls
  `scrollToItem()` for the matching row and does not change axis limits.

- [ ] **Step 2: Add a dedicated static selection frame overlay.**

  Track `_selection_frame_item` in `AnnotationCanvas`. Rebuild it alongside
  `_selection_handle_items` using scene geometry for text/rectangle bounds and
  a padded endpoint/control-point bounding rectangle for line/curve objects.
  Set it to `ItemIsSelectable=False`, `Qt.NoButton`, a dashed blue pen, and a
  z-order below handles. Remove it in `_clear_selection_handles()` and
  `_discard_scene_overlays()` so export never includes it.

- [ ] **Step 3: Make tree selection visibly follow canvas selection.**

  Update `_set_tree_current_item()` to call `scrollToItem(item)` after setting
  the current row. When no editable object is selected, clear the tree current
  selection instead of presenting “Background” as if it were an active target;
  retain the background row for navigation and existing background inspector
  behavior when explicitly clicked.

- [ ] **Step 4: Keep selection and status feedback synchronized.**

  Ensure `_on_annotation_canvas_changed()` and
  `_on_generated_selection_changed()` call the selection-hint helper only after
  the selected object is known. On Escape, restore the idle tool hint and clear
  both the canvas overlay and the tree selection. Do not add a command or mark
  the document dirty for feedback-only changes.

- [ ] **Step 5: Run static/tree regression tests.**

  ```text
  python -m pytest tests/test_annotation_canvas.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py -q
  ```

- [ ] **Step 6: Commit the static/tree slice.**

  ```text
  python scripts/auto_commit.py --message "feat(editor): synchronize selection feedback" --files polynexus/gui/widgets/annotation_canvas.py polynexus/gui/widgets/chart_editor_object_list_mixin.py polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py tests/test_annotation_canvas.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py
  ```

### Task 4: End-to-end verification and handoff

**Files:**

- Modify: `docs/agent/tasks/2026-07-21-editor-strong-feedback.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the complete editor regression matrix.**

  ```text
  python -m pytest tests/test_chart_editor*.py tests/test_annotation_canvas.py tests/test_figure_render_adapter.py -q
  ```

  Expected: all relevant editor/render tests pass; report any pre-existing
  Windows Qt access violation separately instead of hiding it.

- [ ] **Step 2: Run repository verification.**

  ```text
  python scripts/verify.py --task docs/agent/tasks/2026-07-21-editor-strong-feedback.md --changed --types
  python scripts/verify.py --changed --types
  ```

- [ ] **Step 3: Record evidence and known limitations.**

  Mark the task acceptance items only after the commands pass. Record focused
  test counts, the visible-feedback behavior, and any limitations in
  `active-work.md`. Preserve unrelated untracked drafts and runtime files.

- [ ] **Step 4: Create the explicit checkpoint.**

  ```text
  python scripts/auto_commit.py --message "feat(editor): deliver strong feedback mode" --files docs/agent/tasks/2026-07-21-editor-strong-feedback.md docs/agent/memory/active-work.md
  ```
