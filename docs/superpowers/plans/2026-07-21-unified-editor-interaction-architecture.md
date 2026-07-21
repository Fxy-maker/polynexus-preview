# Unified editor interaction architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give static and generated charts one predictable, canvas-first interaction contract while preserving the existing document and scientific rendering boundaries.

**Architecture:** Add a small Qt-independent controller for tool and gesture state. Route both the Qt annotation scene and generated Matplotlib canvas through the same lifecycle, while adapters continue to produce existing edit-session commands. Generated charts keep Matplotlib for rendering/export and disable its navigation mode during object editing.

**Tech Stack:** Python 3.12+, PySide6 Qt Widgets/Graphics View, Matplotlib QtAgg, existing `FigureDocument`, `EditSession`, and edit-command contracts, pytest with offscreen Qt.

---

### Task 1: Establish the shared interaction controller

**Files:**

- Create: `polynexus/gui/widgets/chart_editor_interaction_controller.py`
- Create: `tests/test_editor_interaction_controller.py`
- Modify: `docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md`

- [ ] **Step 1: Write failing transition tests.**

  Define the desired public contract before implementation:

  ```python
  def test_controller_returns_to_select_after_create_commit():
      controller = EditorInteractionController()
      assert controller.set_tool(EditorTool.RECTANGLE) is True
      assert controller.begin_create((10.0, 20.0)).state is GestureState.CREATING
      assert controller.finish_create((40.0, 60.0)).state is GestureState.SELECT_IDLE
      assert controller.tool is EditorTool.SELECT

  def test_controller_escape_cancels_text_edit_without_commit():
      controller = EditorInteractionController()
      controller.begin_create((10.0, 20.0))
      controller.begin_text_edit()
      transition = controller.cancel()
      assert transition.state is GestureState.SELECT_IDLE
      assert transition.committed is False
  ```

- [ ] **Step 2: Run the controller tests and confirm the import/API failure.**

  Run:

  ```text
  python -m pytest tests/test_editor_interaction_controller.py -q
  ```

  Expected: collection fails because the controller module is not present.

- [ ] **Step 3: Implement the minimal controller.**

  Use `Enum` values `SELECT`, `TEXT`, `LINE`, `ARROW`, `CURVE`, `RECTANGLE`
  and states `SELECT_IDLE`, `CREATING`, `TEXT_EDITING`, `BODY_DRAGGING`,
  `HANDLE_DRAGGING`. Store only `tool`, `state`, `object_id`, `handle_index`,
  `press_point`, and `current_point`; return immutable `InteractionTransition`
  records from transitions. Reject invalid points and invalid state changes
  without mutating state.

- [ ] **Step 4: Run controller tests and refactor only after green.**

  Run:

  ```text
  python -m pytest tests/test_editor_interaction_controller.py -q
  ```

  Expected: all controller transition tests pass.

### Task 2: Normalize toolbar and canvas tool lifecycle

**Files:**

- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py`
- Modify: `tests/test_chart_editor_layout.py`
- Modify: `tests/test_chart_editor_workflow.py`

- [ ] **Step 1: Add failing lifecycle tests.**

  Cover both modes:

  ```python
  def test_generated_creation_tool_returns_to_select_after_release(...):
      editor.set_tool("rectangle")
      editor._on_generated_button_press(press)
      editor._on_generated_button_release(release)
      assert editor._generated_draw_tool == "select"

  def test_static_creation_tool_returns_to_select_after_release(...):
      canvas.set_tool("rectangle")
      send_qt_drag(canvas, ...)
      assert canvas.current_tool() == "select"
  ```

- [ ] **Step 2: Run the new lifecycle tests and confirm the current mismatch.**

  Run:

  ```text
  python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py -q -k 'returns_to_select or creation_tool'
  ```

- [ ] **Step 3: Route tool changes through the controller.**

  `ChartEditor.set_tool()` must map the string to `EditorTool`, clear an
  unfinished gesture, deactivate Matplotlib navigation, update the checked
  toolbar action, and leave Select active after a completed or cancelled
  creation. `AnnotationCanvas` emits the same transition outcome after its
  existing scene command is committed.

- [ ] **Step 4: Run the focused layout/workflow tests.**

  Expected: the new lifecycle tests and existing toolbar/creation tests pass.

### Task 3: Unify generated annotation interaction feedback

**Files:**

- Create: `polynexus/gui/widgets/chart_editor_generated_interaction_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_pointer_feedback_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_selection_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Create: `tests/test_chart_editor_generated_interaction_adapter.py`

- [ ] **Step 1: Write failing adapter tests.**

  Verify a visible text/line/curve/rectangle returns the same target shape:

  ```python
  def test_annotation_target_exposes_body_and_handles(...):
      target = adapter.hit_test(pointer)
      assert target.kind == "body"
      assert target.object_id == "note"
      assert target.cursor == "move"
  ```

- [ ] **Step 2: Implement the adapter around existing hit/geometry helpers.**

  The adapter must return a renderer-neutral `HitTarget` with `object_id`,
  `object_type`, `kind`, `handle_index`, and `cursor_role`. It may call the
  existing generated hit-testing mixin, but it must not mutate the document or
  branch on Matplotlib-specific algorithm state.

- [ ] **Step 3: Replace duplicated feedback branches.**

  Pointer feedback and selection handles consume `HitTarget`; body targets use
  move cursors, endpoint/control targets use resize/curve cursors, and invalid
  or locked targets use the existing not-allowed feedback. Geometry mutation
  remains in `UpdateGeometryCommand`/preview transactions.

- [ ] **Step 4: Run generated interaction tests and the existing drag matrix.**

  Expected: adapter tests, generated drag tests, and undo/redo tests pass.

### Task 4: Finish verification and durable handoff

**Files:**

- Modify: `docs/agent/memory/active-work.md`
- Modify: `docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md`

- [ ] **Step 1: Run the focused interaction matrix.**

  ```text
  python -m pytest tests/test_editor_interaction_controller.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py -q
  ```

- [ ] **Step 2: Run the structured and default verifiers.**

  ```text
  python scripts/verify.py --task docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md --changed --types
  python scripts/verify.py --changed --types
  ```

- [ ] **Step 3: Record evidence and create the checkpoint.**

  Mark the task-card acceptance items only after the commands pass, update
  `active-work.md` with the commit and known limitations, then run:

  ```text
  python scripts/auto_commit.py --message "refactor(editor): unify canvas interaction contract" --files docs/agent/memory/active-work.md docs/agent/tasks/2026-07-21-unified-editor-interaction-architecture.md docs/superpowers/specs/2026-07-21-unified-editor-interaction-architecture-design.md docs/superpowers/plans/2026-07-21-unified-editor-interaction-architecture.md polynexus/gui/widgets/chart_editor_interaction_controller.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/widgets/annotation_canvas.py polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py polynexus/gui/widgets/chart_editor_generated_interaction_adapter.py polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py polynexus/gui/widgets/chart_editor_generated_pointer_feedback_mixin.py polynexus/gui/widgets/chart_editor_generated_selection_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py tests/test_editor_interaction_controller.py tests/test_chart_editor_generated_interaction_adapter.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py
  ```
