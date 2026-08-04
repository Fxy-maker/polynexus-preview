# Origin 式图像编辑器交互 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved Origin Lite editing flow: an icon toolbox, direct canvas creation for text/lines/arrows/curves/rectangles, a compact contextual style strip, and an on-demand Inspector.

**Architecture:** The existing `FigureDocument` and `EditSession` remain the sole persistence and undo source. A small context-style mixin owns only transient tool defaults and selected-object style controls; static Qt graphics and generated Matplotlib canvases translate gestures into the existing command set. Static-canvas creation is changed from local mutation to explicit create proposals whenever a document session is active, so both canvases commit one command per completed gesture.

**Tech Stack:** Python 3.12, PySide6 Qt Widgets/Graphics View, Matplotlib QtAgg, existing `FigureDocument`/`EditSession`/edit-command contracts, pytest with offscreen Qt.

---

## Scope and file structure

This is one editor interaction slice, rather than two separate features, because static and generated modes must persist the same object geometry and use the same command history. The implementation worktree must be created from `origin/main` at or after `93c265f`; do not implement in the dirty `D:\PolyNexus` worktree.

| File | Responsibility |
| --- | --- |
| Create `polynexus/gui/widgets/chart_editor_tool_icons.py` | Draw deterministic, theme-neutral vector `QIcon`s for the compact toolbox. |
| Create `polynexus/gui/widgets/chart_editor_context_style_mixin.py` | Own the compact style strip, tool defaults, selected-object synchronization, and style command dispatch. |
| Create `polynexus/gui/widgets/chart_editor_inline_text_mixin.py` | Own one transient `QLineEdit` used to commit or discard direct text creation in either canvas mode. |
| Modify `polynexus/gui/widgets/chart_editor.py` | Compose the new mixins, wire signals, mount the style strip, and remove duplicate Inspector creation UI. |
| Modify `polynexus/gui/widgets/chart_editor_layout_mixin.py` | Switch the vertical toolbox from text actions to icon actions and maintain tool hints/selected state. |
| Modify `polynexus/gui/widgets/chart_editor_edit_session_mixin.py` | Route tool selection through the context strip without opening the Inspector. |
| Modify `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py` | Convert static canvas create proposals and inline-text results into `AddObjectCommand`/`Update*Command` operations. |
| Modify `polynexus/gui/widgets/annotation_canvas.py` | Add transient draw previews, create/text requests, text-box dimensions, and static selection handles for segment/curve/rectangle geometry. |
| Modify `polynexus/gui/widgets/annotation_render_adapter.py` | Respect persisted text-box width and line style while retaining legacy text objects without a width. |
| Modify `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py` | Defer generated text creation to the inline editor; preserve press-drag creation for the other tools. |
| Modify generated geometry/press-target helpers | Add rectangle handle drag parity and ensure the existing curve control handle remains the third handle. |
| Modify `polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py` | Start collapsed and never reveal the drawer solely because selection changed. |
| Modify `polynexus/gui/i18n.py` | Add Chinese and English labels for direct-draw status, compact controls, inline text and accessible tooltips. |
| Modify focused tests under `tests/` | Lock down tool appearance, gesture-to-command behavior, text bounds, handles, context controls, drawer behavior, and regression paths. |
| Modify `docs/agent/memory/active-work.md` | Record the completed branch/verification evidence only after implementation is verified. |

All commit commands below require explicit commit authorization at execution time. Without that authorization, leave the changes uncommitted and report the exact working-tree state.

### Task 1: Establish the icon toolbox and default-collapsed Inspector

**Files:**

- Create: `tests/test_chart_editor_tool_icons.py`
- Modify: `tests/test_chart_editor_layout.py`
- Create: `polynexus/gui/widgets/chart_editor_tool_icons.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_inspector_drawer_mixin.py`

- [ ] **Step 1: Write the failing toolbox and drawer tests.**

  Add the following assertions. They intentionally replace the old expectation that selection opens the Inspector.

  ```python
  def test_editor_toolbox_uses_icons_and_keeps_translated_tooltips():
      _app()
      editor = ChartEditor()

      assert editor._editor_toolbar.orientation() == Qt.Vertical
      assert editor._editor_toolbar.toolButtonStyle() == Qt.ToolButtonIconOnly
      assert editor._editor_toolbar.action("select").icon().isNull() is False
      assert editor._editor_toolbar.action("curve").icon().isNull() is False
      assert editor._editor_toolbar.action("text").toolTip() == tr("EDITOR_TOOL_TEXT")

  def test_inspector_is_closed_by_default_and_selection_does_not_reopen_it():
      app = _app()
      editor = ChartEditor()
      editor.resize(1100, 720)
      editor.show()
      app.processEvents()

      assert editor._inspector_panel.isHidden()
      editor._on_generated_selection_changed("missing", "canvas")
      app.processEvents()
      assert editor._inspector_panel.isHidden()
  ```

- [ ] **Step 2: Run the focused tests and confirm the current UI fails the new expectations.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_tool_icons.py -q
  ```

  Expected: the icon test cannot import the new icon module and the Inspector test fails because the current drawer is visible or selection reveals it.

- [ ] **Step 3: Implement the icon factory.**

  Create `chart_editor_tool_icons.py` with a single public `editor_tool_icon(action_id, size=18)` function. Use `QPixmap(size, size)`, `QPainter`, `QPen`, `QPainterPath`, and `QPolygonF`; return a non-null `QIcon` for every action ID below. The shapes must be compact monochrome drawings, not Unicode text rendered into a button:

  ```python
  _SUPPORTED_ACTIONS = {
      "select", "text", "line", "arrow", "curve", "rectangle", "undo", "redo", "export",
  }

  def editor_tool_icon(action_id: str, size: int = 18) -> QIcon:
      action = str(action_id).strip().lower()
      if action not in _SUPPORTED_ACTIONS:
          return QIcon()
      pixmap = QPixmap(size, size)
      pixmap.fill(Qt.GlobalColor.transparent)
      painter = QPainter(pixmap)
      painter.setRenderHint(QPainter.RenderHint.Antialiasing)
      painter.setPen(QPen(QColor("#D7E3F4"), max(1.0, size / 12.0)))
      # Draw the action-specific pointer, T, segment, arrow head, quadratic path,
      # rectangle, curved undo/redo arrow, or export tray before ending the painter.
      painter.end()
      return QIcon(pixmap)
  ```

  Use only fixed geometry derived from `size`; no filesystem assets or generated image files are introduced.

- [ ] **Step 4: Apply icons and compact toolbar policy.**

  In `_EditorContextToolbar.__init__`, set `Qt.ToolButtonIconOnly`, `setIconSize(QSize(18, 18))`, and assign `editor_tool_icon(action_id)` to every `QAction`. Keep translated action text for accessibility and tooltips, but do not show it on the button. In `retranslate`, preserve the assigned icon while updating text and tooltip.

  In `ChartEditor._build_ui`, keep the toolbar on the left but give it a fixed width that accommodates the 18px icon plus margins; do not move the existing navigation toolbar or canvas stack.

- [ ] **Step 5: Make the drawer truly on-demand.**

  Set the splitter’s Inspector panel hidden during editor construction, synchronize the header toggle after hiding it, and change `_reveal_inspector_for_selection` to a no-op. The only code path that opens the drawer must be `_toggle_inspector_drawer` or an explicit advanced-properties action from the context strip introduced in Task 2.

  The required behavior is:

  ```python
  def _reveal_inspector_for_selection(self) -> None:
      """Selection updates controls but never changes drawer visibility."""
      return None
  ```

- [ ] **Step 6: Run the focused layout tests.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_tool_icons.py -q
  ```

  Expected: PASS. The existing narrow-width and manual drawer-toggle tests remain green after their default-state assertions are updated.

### Task 2: Add the compact context style strip and remove Inspector-only drawing defaults

**Files:**

- Create: `tests/test_chart_editor_context_style_mixin.py`
- Create: `polynexus/gui/widgets/chart_editor_context_style_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_layout_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`
- Modify: `polynexus/gui/i18n.py`

- [ ] **Step 1: Write failing context-strip tests.**

  Cover the user-facing contract rather than private Qt layout details:

  ```python
  def test_context_strip_shows_only_text_controls_for_selected_text():
      _app()
      editor = _generated_editor_with_object({"id": "note", "type": "text", "x": 0.2, "y": 0.4, "text": "Peak"})
      editor._select_generated_object("note", "test")

      assert editor._context_style_bar.isVisible()
      assert editor._context_font_size.isVisible()
      assert not editor._context_line_width.isVisible()

  def test_context_strip_updates_selected_line_through_edit_session():
      _app()
      editor = _generated_editor_with_object({"id": "line", "type": "line", "x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0})
      editor._select_generated_object("line", "test")

      assert editor._apply_context_color("#0072B2") is True
      assert editor._generated_figure_object_by_id("line")["style"]["color"] == "#0072B2"
      assert editor._edit_session.can_undo is True
  ```

- [ ] **Step 2: Run the new context-strip test file.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_context_style_mixin.py -q
  ```

  Expected: FAIL because the mixin and controls do not yet exist.

- [ ] **Step 3: Implement `ChartEditorContextStyleMixin`.**

  Build one horizontal, initially hidden `QWidget` containing:

  - a small color `QToolButton` whose popup menu exposes `#000000`, `#0072B2`, `#D55E00`, `#009E73`, and `#CC79A7`;
  - a `QComboBox` for `1`, `1.5`, `2`, `3`, and `4` px line widths;
  - a `QComboBox` for `Solid`, `Dashed`, `Dotted`, and `Dash Dot`;
  - a `QSpinBox` for text size from 6 to 72 pt;
  - one `QToolButton` that explicitly calls `_toggle_inspector_drawer` for advanced properties.

  Give the mixin these stable methods and use them from tests and signal handlers:

  ```python
  def _build_context_style_bar(self) -> QWidget: ...
  def _sync_context_style_bar(self) -> None: ...
  def _apply_context_color(self, color: str) -> bool: ...
  def _apply_context_line_width(self, value: float) -> bool: ...
  def _apply_context_line_style(self, label: str) -> bool: ...
  def _apply_context_font_size(self, value: int) -> bool: ...
  def _active_draw_style(self) -> dict[str, object]: ...
  ```

  `_active_draw_style` returns the tool defaults when no object is selected and returns the selected object’s canonical style when one is selected. Apply changes through `UpdateStyleCommand` whenever an `EditSession` exists; in standalone static-canvas mode call `AnnotationCanvas.update_selected_properties` with the same validated value. Do not read `QLineEdit` values from the Inspector to decide the active draw style.

- [ ] **Step 4: Integrate the strip with tool state and selection.**

  Mount the strip below the shared canvas stack, above the existing status bar. Update `ChartEditorEditSessionMixin.set_tool` so it:

  ```python
  self._generated_draw_tool = tool
  self._generated_draw_start_data = None
  self._sync_context_style_bar()
  self._set_draw_status_hint(tool)
  self._sync_editor_toolbar()
  ```

  Remove the current behavior that selects the annotation Inspector tab, focuses `_annotation_text_edit`, or enables Inspector fields when a draw tool is selected. Call `_sync_context_style_bar` after static and generated selection changes so the strip is hidden for no selection/select tool, shows text controls for text, line controls for line/arrow/curve/rectangle, and never shows irrelevant disabled controls.

- [ ] **Step 5: Add translations and keep the Inspector advanced-only.**

  Add matching Chinese and English entries in both dictionaries in `i18n.py` for `EDITOR_CONTEXT_COLOR`, `EDITOR_CONTEXT_LINE_WIDTH`, `EDITOR_CONTEXT_LINE_STYLE`, `EDITOR_CONTEXT_FONT_SIZE`, `EDITOR_CONTEXT_ADVANCED`, `EDITOR_DRAW_TEXT_HINT`, `EDITOR_DRAW_CURVE_HINT`, and `EDITOR_DRAW_CANCELLED`. Remove the add-text/add-line/add-arrow/add-rectangle/highlight/crop button grids from the Annotation Inspector page; retain exact text, geometry, object-list, advanced-style, ordering, zoom, save and export controls for the drawer.

- [ ] **Step 6: Run context, layout, and annotation-control regressions.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_context_style_mixin.py tests/test_chart_editor_layout.py tests/test_chart_editor_annotation_controls_mixin.py -q
  ```

  Expected: PASS. The tests must show that a line can change color without opening the Inspector.

### Task 3: Make static-canvas draw gestures command-backed and support drag-created text boxes

**Files:**

- Modify: `tests/test_annotation_canvas.py`
- Modify: `tests/test_annotation_render_adapter.py`
- Modify: `tests/test_chart_editor_workflow.py`
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/annotation_render_adapter.py`
- Create: `polynexus/gui/widgets/chart_editor_inline_text_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py`

- [ ] **Step 1: Write failing static gesture tests.**

  Add tests that assert a drag only creates an object on release, text drag preserves the box dimensions, text click remains a label, and cancellation creates no command/object:

  ```python
  def test_document_mode_static_text_drag_requests_a_box_without_local_mutation(tmp_path):
      canvas = _loaded_document_canvas(tmp_path)
      requests = []
      canvas.object_create_requested.connect(requests.append)

      canvas.set_tool("text")
      assert canvas._finish_mouse_draw(QPointF(10, 8), QPointF(70, 28)) == ""

      assert requests == [{"type": "text", "geometry": {"x": 0.1, "y": 0.16, "width": 0.6, "height": 0.4}}]
      assert canvas.annotation_state() == []

  def test_static_text_box_renderer_applies_persisted_width(tmp_path):
      canvas = _loaded_canvas(tmp_path)
      text_id = canvas.add_text_annotation("Peak region", 10, 8, width=60, height=20)
      item = next(item for item in canvas._scene.items() if item.data(0) == text_id)

      assert item.textWidth() == 60
  ```

  In `test_chart_editor_workflow.py`, add a static `ChartEditor` scenario that sends a text request, commits `"Peak region"`, checks the canonical document object has `x`, `y`, `width`, `height`, and uses one undo to remove it.

- [ ] **Step 2: Run the static gesture tests and confirm failure.**

  Run:

  ```powershell
  python -m pytest tests/test_annotation_canvas.py tests/test_annotation_render_adapter.py tests/test_chart_editor_workflow.py -q
  ```

  Expected: FAIL because `object_create_requested`, `width`, and the inline text transaction do not exist.

- [ ] **Step 3: Add Canvas creation proposals and transient previews.**

  In `AnnotationCanvas`, add these signals:

  ```python
  object_create_requested = Signal(object)
  text_entry_requested = Signal(object)
  ```

  During non-select mouse movement, render exactly one temporary preview item for the current line, arrow, curve, rectangle, or text rectangle. Remove it on release, `Esc`, mode change, or invalid geometry. When `_document_objects_mode` is true, `_finish_mouse_draw` must emit a payload rather than append an object locally:

  ```python
  {"type": "line", "geometry": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}}
  {"type": "curve", "geometry": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "control_x": cx, "control_y": cy}}
  {"type": "rectangle", "geometry": {"x": x, "y": y, "width": width, "height": height}}
  ```

  For text, emit `text_entry_requested` with the same normalized box geometry. Treat a drag smaller than 3 device pixels as a label request with only `x` and `y`; treat a larger drag as a text-box request with `width` and `height`. Standalone Canvas users keep the previous local add behavior for non-text tools.

- [ ] **Step 4: Implement the inline text transaction.**

  `ChartEditorInlineTextMixin` owns one hidden `QLineEdit`, a `_pending_inline_text` payload, and these methods:

  ```python
  def _begin_inline_text_entry(self, payload: dict, *, host: QWidget, rect: QRect) -> None: ...
  def _commit_inline_text_entry(self, text: str | None = None) -> bool: ...
  def _cancel_inline_text_entry(self) -> None: ...
  ```

  Position the line edit at the drag rectangle, call `selectAll()` and `setFocus()`, commit on Return or focus loss, and cancel on Escape. An empty or whitespace-only commit discards the pending payload without an `AddObjectCommand`. A nonempty commit delegates to `_commit_canvas_text_payload(payload, text)`, which converts static payloads through `annotation_to_figure_object` and executes one `AddObjectCommand` when a session exists; otherwise it calls `AnnotationCanvas.add_text_annotation(text, x_px, y_px, width=..., height=...)`.

  Update `AnnotationRenderAdapter` so a text item calls `setTextWidth(width_px)` only when its geometry has a positive `width`; old text objects without that key remain automatic-size labels. Ensure static text geometry synchronization retains `width` and `height` when they were present.

- [ ] **Step 5: Wire static proposals to the editor and session.**

  In `ChartEditor._build_ui`, connect `object_create_requested` to `_on_annotation_object_create_requested` and `text_entry_requested` to `_on_annotation_text_entry_requested`. Implement the non-text handler in `ChartEditorAnnotationControlsMixin` with the existing `AddObjectCommand`:

  ```python
  payload = annotation_to_figure_object({"id": annotation_id, "type": kind, **geometry, **style})
  result = self._execute_edit(AddObjectCommand(payload))
  if result is not None and result.changed:
      self._edit_session.select(annotation_id, "annotation_canvas")
      self._annotation_canvas.select_annotation(annotation_id)
  ```

  Use `self._active_draw_style()` for all default colors, widths, alpha, line style and text font size. A failed command restores select mode, clears preview, and writes `EDITOR_DRAW_CANCELLED` to the status label.

- [ ] **Step 6: Run static regressions.**

  Run:

  ```powershell
  python -m pytest tests/test_annotation_canvas.py tests/test_annotation_render_adapter.py tests/test_chart_editor_workflow.py tests/test_chart_editor_annotation_controls_mixin.py -q
  ```

  Expected: PASS. Verify manually in the offscreen-capable test that a text drag adds exactly one history entry only after nonempty text is committed.

### Task 4: Complete direct selection handles for static annotations

**Files:**

- Modify: `tests/test_annotation_canvas.py`
- Modify: `polynexus/gui/widgets/annotation_canvas.py`
- Modify: `polynexus/gui/widgets/annotation_render_adapter.py`
- Modify: `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`

- [ ] **Step 1: Write failing static-handle tests.**

  Add focused tests for endpoint/control/corner updates and one-command semantics:

  ```python
  def test_selected_static_curve_control_handle_commits_one_geometry_request(tmp_path):
      canvas = _loaded_document_canvas(tmp_path)
      canvas.set_document_objects([_curve_object("curve-1")])
      canvas.select_annotation("curve-1")
      requests = []
      canvas.object_edit_requested.connect(requests.append)

      assert canvas._begin_selection_handle_drag(QPointF(50, 10)) is True
      canvas._update_selection_handle_drag(QPointF(45, 20))
      assert canvas._finish_selection_handle_drag(QPointF(45, 20)) is True

      assert requests[-1]["object_id"] == "curve-1"
      assert requests[-1]["geometry"]["control_x"] == 0.45
      assert requests[-1]["geometry"]["control_y"] == 0.4
  ```

  Add parallel tests for a line endpoint and a rectangle corner. Confirm that pressing Escape during a handle drag restores the original geometry and emits no request.

- [ ] **Step 2: Run the handle tests and confirm failure.**

  Run:

  ```powershell
  python -m pytest tests/test_annotation_canvas.py -q
  ```

  Expected: FAIL because selected static objects only move as a whole today.

- [ ] **Step 3: Implement one static selection-handle overlay.**

  Add a private overlay owned by `AnnotationCanvas`; it must never enter `_annotations` or `FigureDocument`. Display small square/round handles only for the selected item:

  - line and arrow: endpoint indexes `0`, `1`;
  - curve: endpoint indexes `0`, `1` and control index `2`;
  - rectangle: corner indexes `0`, `1`, `2`, `3`.

  Give the canvas these deterministic methods:

  ```python
  def _begin_selection_handle_drag(self, scene_point: QPointF) -> bool: ...
  def _update_selection_handle_drag(self, scene_point: QPointF) -> bool: ...
  def _finish_selection_handle_drag(self, scene_point: QPointF) -> bool: ...
  def _cancel_selection_handle_drag(self) -> bool: ...
  ```

  The update method changes only the rendered preview and handle positions. The finish method clamps normalized geometry to `[0.0, 1.0]`, emits one `object_edit_requested` payload in document mode, or calls one local `update_selected_geometry` in standalone mode. Reuse the existing `UpdateGeometryCommand` route in `ChartEditorEditSessionMixin`; do not call it on every mouse-move event.

- [ ] **Step 4: Integrate selection-handle pointer and cursor behavior.**

  In `eventFilter`, check the overlay before allowing the default `QGraphicsView` move behavior. Use `Qt.SizeAllCursor` for a control or endpoint, `Qt.SizeFDiagCursor`/`Qt.SizeBDiagCursor` for rectangle corners, and reset the cursor when no handle is under the pointer. In `keyPressEvent`, call `_cancel_selection_handle_drag()` before normal Escape selection clearing.

- [ ] **Step 5: Preserve text and curve rendering contracts.**

  Keep `AnnotationRenderAdapter` responsible only for persisted artwork. The overlay creates no renderer object and does not change export output. Continue using the existing quadratic `QPainterPath` for curves and preserve the existing arrow-head grouping behavior.

- [ ] **Step 6: Run static-handle and undo regressions.**

  Run:

  ```powershell
  python -m pytest tests/test_annotation_canvas.py tests/test_figure_edit_session.py tests/test_figure_edit_commands.py -q
  ```

  Expected: PASS. Each committed handle gesture is undone by exactly one `Ctrl+Z`.

### Task 5: Bring generated figures to the same direct-creation and handle contract

**Files:**

- Modify: `tests/test_chart_editor_generated_interaction_mixin.py`
- Modify: `tests/test_chart_editor_generated_geometry_mixin.py`
- Modify: `tests/test_chart_editor_generated_press_target_mixin.py`
- Modify: `tests/test_chart_editor_curve.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `polynexus/gui/widgets/chart_editor_inline_text_mixin.py`

- [ ] **Step 1: Write failing generated-text and rectangle-handle tests.**

  Add a direct text transaction test and a rectangle-corner geometry test:

  ```python
  def test_generated_text_drag_waits_for_inline_text_before_adding_object():
      editor = _generated_editor()
      editor._begin_generated_text_box((1.0, 2.0), (4.0, 3.0), QRect(20, 20, 100, 28))

      assert editor._figure_document["objects"] == []
      assert editor._commit_inline_text_entry("Peak region") is True
      text = editor._figure_document["objects"][0]
      assert text["type"] == "text"
      assert text["width"] == 3.0
      assert text["height"] == 1.0

  def test_generated_rectangle_corner_drag_updates_width_and_height_once():
      editor = _generated_editor_with_rectangle()
      assert editor._apply_generated_rectangle_handle_drag("rect-1", 2, 4.0, 3.0)
      rectangle = editor._generated_figure_object_by_id("rect-1")
      assert rectangle["width"] == 3.0
      assert rectangle["height"] == 2.0
  ```

- [ ] **Step 2: Run generated interaction tests and confirm failure.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_generated_press_target_mixin.py tests/test_chart_editor_curve.py -q
  ```

  Expected: FAIL because text is immediately added on press and rectangle handles have no geometry route.

- [ ] **Step 3: Defer generated text creation to Task 3’s inline editor.**

  Update `_handle_generated_draw_press` so text stores its start coordinate and does not call `_add_generated_tool_object`. Update `_finish_generated_draw` to dispatch text to:

  ```python
  self._begin_generated_text_box(start, end, self._generated_canvas_rect(start, end))
  ```

  `_begin_generated_text_box` passes a payload with `mode="generated"`, `x`, `y`, and optional positive `width`/`height` to `_begin_inline_text_entry`. Modify `_add_generated_tool_object` so `tool == "text"` includes `width` and `height` only if supplied and positive. A click remains a text label; a drag is stored as a text box. Empty commit and Escape leave `_figure_document` and command history unchanged.

- [ ] **Step 4: Add generated rectangle handle routing without changing curve semantics.**

  Extend generated press-target detection to return rectangle-corner states with handle indexes `0..3`. Add `_apply_generated_rectangle_handle_drag(object_id, handle_index, x_value, y_value)` to normalize the dragged corner into `{x, y, width, height}`, use `UpdateGeometryCommand`, refresh the preview, and synchronize the Inspector/context strip. Keep the existing curve mapping exactly:

  ```python
  {0: ("x1", "y1"), 1: ("x2", "y2"), 2: ("control_x", "control_y")}
  ```

  Do not replace the confirmed two-endpoint-plus-one-control-handle curve model with a multi-node spline.

- [ ] **Step 5: Render generated text boxes compatibly.**

  In `_render_generated_figure_object`, retain `ax.text` for legacy labels. When positive text `width` is present, pass `wrap=True`, `clip_on=True`, and preserve the bounds in the figure object for selection/Inspector use; do not draw a permanent rectangle around finished text. When width is absent, render exactly as current labels do. This keeps saved text-box geometry available to both adapters without altering existing generated figures.

- [ ] **Step 6: Run generated regressions.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_generated_press_target_mixin.py tests/test_chart_editor_curve.py tests/test_chart_editor_generated_document_mixin.py -q
  ```

  Expected: PASS. Curve endpoint/control tests remain unchanged and generated text click/drag paths both produce undoable objects only after text entry commits.

### Task 6: Integrate keyboard/status behavior, verify persistence, and produce handoff evidence

**Files:**

- Modify: `tests/test_chart_editor_layout.py`
- Modify: `tests/test_chart_editor_workflow.py`
- Modify: `tests/test_chart_editor_save_mixin.py`
- Modify: `docs/agent/tasks/2026-07-18-origin-like-editor-interaction.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Write final cross-mode regression tests.**

  Add tests that cover the completed user workflow:

  ```python
  def test_escape_cancels_active_draw_without_creating_or_reopening_inspector():
      editor = _generated_editor()
      assert editor.set_tool("line") is True
      editor._generated_draw_start_data = (1.0, 1.0)

      assert editor._cancel_active_draw() is True
      assert editor._generated_draw_start_data is None
      assert editor._figure_document["objects"] == []
      assert editor._inspector_panel.isHidden()

  def test_text_box_round_trips_through_saved_figure_document(tmp_path):
      document = _document_with_text_box()
      path = save_generated_figure_document(tmp_path / "figure.png", objects=document["objects"])

      loaded = load_figure_document(str(path))
      assert loaded["objects"][0]["bounds"]["width"] == 0.3
      assert loaded["objects"][0]["bounds"]["height"] == 0.1
  ```

- [ ] **Step 2: Implement the common cancel/status route.**

  Add `_cancel_active_draw()` to `ChartEditorEditSessionMixin`. It must clear static preview, generated start coordinates, inline text, and temporary selection handles; set the active tool to select; then set the translated cancellation status. Route canvas and generated `Esc` handling through this method before normal selection clearing. Keep `Delete`, `Ctrl+Z`, and `Ctrl+Y` on their current command/session paths.

- [ ] **Step 3: Update task evidence and durable memory after all tests pass.**

  Check every acceptance criterion in `docs/agent/tasks/2026-07-18-origin-like-editor-interaction.md` only after the commands below pass. Add the implementation branch, exact focused-suite result, verifier availability result, and manual-GUI result to `docs/agent/memory/active-work.md`. Do not add raw logs, screenshots, secrets, or copied source code to memory.

- [ ] **Step 4: Run the focused regression matrix.**

  Run:

  ```powershell
  python -m pytest tests/test_chart_editor_layout.py tests/test_chart_editor_context_style_mixin.py tests/test_chart_editor_tool_icons.py tests/test_annotation_canvas.py tests/test_annotation_render_adapter.py tests/test_chart_editor_annotation_controls_mixin.py tests/test_chart_editor_workflow.py tests/test_chart_editor_generated_interaction_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_generated_press_target_mixin.py tests/test_chart_editor_curve.py tests/test_chart_editor_generated_document_mixin.py tests/test_chart_editor_save_mixin.py -q
  ```

  Expected: PASS with no skipped failure. Record the exact test count in the task card and final handoff.

- [ ] **Step 5: Run the repository checks and record the actual outcome.**

  Run:

  ```powershell
  python scripts/verify.py --task docs/agent/tasks/2026-07-18-origin-like-editor-interaction.md --changed --types
  python scripts/verify.py --changed --types --full --boundary
  python -m ruff check polynexus/gui/i18n.py polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_tool_icons.py polynexus/gui/widgets/chart_editor_context_style_mixin.py polynexus/gui/widgets/chart_editor_inline_text_mixin.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py polynexus/gui/widgets/annotation_canvas.py polynexus/gui/widgets/annotation_render_adapter.py polynexus/gui/widgets/chart_editor_generated_interaction_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/widgets/chart_editor_generated_press_target_mixin.py polynexus/gui/widgets/chart_editor_generated_document_mixin.py
  python -m compileall polynexus/gui/widgets
  git diff --check
  ```

  Expected: the prescribed verifier may report that `scripts/verify.py` is absent; if so, record that exact absence and do not claim it passed. Ruff, `compileall`, and `git diff --check` must pass before handoff.

- [ ] **Step 6: Perform the real-GUI acceptance pass and request review.**

  Launch the application from the new isolated worktree with `polynexus --gui`. In both a static export and a generated figure, verify: Inspector is initially closed; each icon has a tooltip; text click and text-box drag accept inline text; line, arrow, rectangle and curve draw by drag; curve control point and shape handles move; color changes without opening Inspector; Escape leaves no object; one undo reverses one completed object gesture; saved documents reload; and export remains reachable. Capture results in the task card, then request code review. Do not push, create a PR, merge, or commit unless the user authorizes that action.
