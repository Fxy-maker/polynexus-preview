# Origin Editor Practicality Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make existing static and generated figures reliable to edit, undo, save, and export through one canonical document and one command-based edit session.

**Architecture:** Keep `figure_document.py` as the JSON boundary. Add a Qt-free edit session, command protocol, and capability registry; make Matplotlib and annotation rendering projections of that session. Integrate the current ChartEditor mixins through one adapter and leave `data_sources`/`recipe` as the seam for a later data-aware Origin phase.

**Tech Stack:** Python 3.12+, PySide6, Matplotlib, JSON sidecars, pytest, Qt offscreen tests, Ruff, `compileall`.

---

## Scope

This plan implements Phase 1 of [the approved design](D:/PolyNexus/docs/superpowers/specs/2026-07-17-origin-editor-practicality-design.md): reliable publication-grade editing of `line`, `arrow`, `text`, `rectangle`, `highlight`, `plot_series`, `legend`, and `image_background`. It does not implement data-table editing, fitting, new plot recipes, or new chart types. Those belong to a separate Phase 2 plan after these contracts are stable.

## File map

Create:

- `polynexus/core/figure_edit_capabilities.py`: object capability descriptors.
- `polynexus/core/figure_edit_commands.py`: Qt-free commands and `EditResult`.
- `polynexus/core/figure_edit_session.py`: canonical document, selection, history, dirty state.
- `polynexus/core/figure_edit_persistence.py`: atomic save bundle.
- `polynexus/gui/widgets/chart_editor_edit_session_mixin.py`: Qt-to-session adapter.
- `polynexus/gui/widgets/annotation_render_adapter.py`: QGraphics projection.
- `tests/test_figure_edit_capabilities.py`, `tests/test_figure_edit_commands.py`, `tests/test_figure_edit_session.py`, `tests/test_figure_edit_persistence.py`.
- `tests/test_annotation_render_adapter.py`, `tests/test_chart_editor_workflow.py`.

Modify:

- `polynexus/core/figure_objects.py`, `polynexus/core/figure_document.py`: canonical object normalization and sidecar migration.
- `polynexus/core/figure_object_store.py`: snapshot/replace compatibility operations.
- `polynexus/gui/figure_selection_model.py`: shared generated/annotation selection.
- `polynexus/gui/widgets/annotation_canvas.py`: view/projection instead of authoritative history.
- `polynexus/gui/widgets/chart_editor.py` and the existing chart-editor mixins: route mutations through the adapter.
- `polynexus/gui/i18n.py`: toolbar, validation, and save-result strings.

## Task 1: Freeze the failing workflows with red tests

**Files:** Create `tests/test_chart_editor_workflow.py`; update `tests/test_annotation_canvas.py` and `tests/test_chart_editor_layout.py`.

- [ ] **Step 1: Add deterministic Qt and figure fixtures.**

```python
@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])

def make_static_editor(tmp_path, source=None):
    path = Path(source or (tmp_path / "source.png"))
    if source is None:
        image = QImage(160, 100, QImage.Format_RGBA8888)
        image.fill(QColor("white"))
        assert image.save(str(path))
    editor = ChartEditor()
    editor.set_source_figure(str(path))
    return editor

def make_generated_editor(tmp_path, object_type="line"):
    path = tmp_path / "generated.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(path))
    payloads = {
        "line": {"x1": .1, "y1": .2, "x2": .8, "y2": .9},
        "arrow": {"x1": .1, "y1": .2, "x2": .8, "y2": .9},
        "rectangle": {"bounds": {"x": .1, "y": .2, "width": .4, "height": .3}},
        "highlight": {"bounds": {"x": .1, "y": .2, "width": .4, "height": .3}},
        "plot_series": {"data": {"x": [.1, .5, .8], "y": [.2, .7, .4]}, "chart_kind": "line"},
    }
    object_payload = {"id": f"{object_type}-1", "type": object_type, "name": object_type.title(), "style": {"color": "#000000", "line_width": 1.0, "line_style": "-"}}
    object_payload.update(payloads[object_type])
    save_generated_figure_document(str(path), figure_id="generated", objects=[object_payload])
    editor = ChartEditor()
    editor.generated_line_path = str(path)
    editor.set_source_figure(str(path))
    return editor

@pytest.fixture
def editor(tmp_path):
    return make_generated_editor(tmp_path)
```

- [ ] **Step 2: Add the generated line style regression.**

```python
def test_selected_generated_line_color_update_reaches_document(editor):
    editor.set_source_figure(editor.generated_line_path)
    editor._select_generated_object("line-1", "list")
    editor._annotation_color_edit.setText("#0072B2")
    editor._btn_annotation_apply_style.click()
    assert editor._generated_store().get("line-1")["style"]["color"] == "#0072B2"
    assert editor._last_edit_result.changed is True
```

- [ ] **Step 3: Add static text add/edit/undo/redo/save/reload coverage.**

```python
def test_static_text_annotation_round_trips_through_one_history(tmp_path):
    editor = make_static_editor(tmp_path)
    editor._annotation_text_edit.setText("Peak")
    editor._btn_annotation_add_text.click()
    annotation_id = editor._annotation_canvas.selected_annotation_id()
    editor._annotation_text_edit.setText("Peak value")
    editor._btn_annotation_update_text.click()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak value"
    editor._on_annotation_undo()
    assert editor._annotation_canvas.selected_annotation()["text"] == "Peak"
    editor._on_annotation_redo()
    target = tmp_path / "edited.png"
    editor._save_to_path(str(target))
    reloaded = make_static_editor(tmp_path, source=target)
    assert reloaded._annotation_canvas.annotation_state()[0]["id"] == annotation_id
    assert reloaded._annotation_canvas.annotation_state()[0]["text"] == "Peak value"
```

- [ ] **Step 4: Add invalid-input preservation.**

```python
def test_invalid_color_keeps_object_and_history_unchanged(editor):
    editor.set_source_figure(editor.generated_line_path)
    editor._select_generated_object("line-1", "list")
    before = deepcopy(editor._generated_store().get("line-1"))
    editor._annotation_color_edit.setText("not-a-color")
    editor._btn_annotation_apply_style.click()
    assert editor._generated_store().get("line-1") == before
    assert "invalid" in editor._status_label.text().lower()
```

- [ ] **Step 5: Run the red tests, then commit only the tests.**

```powershell
pytest -q tests/test_chart_editor_workflow.py -v
git add tests/test_chart_editor_workflow.py tests/test_annotation_canvas.py tests/test_chart_editor_layout.py
git commit -m "test: specify reliable Origin editing workflows"
```

Expected before implementation: the new tests fail because generated and annotation history are separate, no shared edit result exists, and validation is not centralized.

## Task 2: Normalize the canonical figure object shape

**Files:** Modify `polynexus/core/figure_objects.py` and `polynexus/core/figure_document.py`; test with `tests/test_figure_document.py` and `tests/test_figure_document_builder.py`.

- [ ] **Step 1: Add tests for layer identity, canonical bounds, unknown-field retention, and idempotence.**

```python
def test_static_annotation_is_a_layered_canonical_object():
    document = create_static_figure_document("figure.png", annotations=[
        {"id": "ann-1", "type": "line", "x1": .1, "y1": .2,
         "x2": .8, "y2": .9, "color": "#0072B2", "line_width": 2.0},
    ])
    line = next(item for item in document["objects"] if item["id"] == "ann-1")
    assert line["layer_id"] == "layer-1"
    assert line["bounds"] == {"x1": .1, "y1": .2, "x2": .8, "y2": .9}
    assert line["style"]["color"] == "#0072B2"

def test_normalization_is_idempotent_and_preserves_future_fields():
    payload = {"version": 1, "objects": [{"id": "future-1", "type": "future_artist", "future_payload": {"x": 1}}]}
    once = normalize_figure_document(payload)
    assert normalize_figure_document(once) == once
    assert once["objects"][0]["future_payload"] == {"x": 1}
```

- [ ] **Step 2: Run the tests and verify only the new assertions fail.**

```powershell
pytest -q tests/test_figure_document.py tests/test_figure_document_builder.py -k "canonical or normalize or future"
```

- [ ] **Step 3: Implement normalization.**

`normalize_figure_object()` must set `layer_id="layer-1"`, retain `bounds` and `style` dictionaries, and never discard unrecognized keys. `annotation_to_figure_object()` must put normalized `x/y/width/height/x1/y1/x2/y2` values into `bounds` while retaining legacy top-level values. `create_static_figure_document()` must place the background and converted annotations in one layer.

- [ ] **Step 4: Run all document tests and commit.**

```powershell
pytest -q tests/test_figure_document.py tests/test_figure_document_builder.py tests/test_dsc_figure_document.py tests/test_ir_figure_document.py tests/test_nmr_figure_document.py tests/test_saxs_figure_document.py tests/test_waxs_figure_document.py
git add polynexus/core/figure_objects.py polynexus/core/figure_document.py tests/test_figure_document.py tests/test_figure_document_builder.py
git commit -m "feat: normalize Origin figure objects for shared editing"
```

## Task 3: Add the Qt-free capability registry and edit session

**Files:** Create `polynexus/core/figure_edit_capabilities.py`, `polynexus/core/figure_edit_commands.py`, `polynexus/core/figure_edit_session.py`; test with the three corresponding `tests/test_figure_edit_*.py` files.

- [ ] **Step 1: Add capability and command tests first.**

```python
def test_line_capabilities_include_style_and_geometry():
    capabilities = capabilities_for({"type": "line"})
    assert capabilities.style and capabilities.color
    assert capabilities.line_style and capabilities.geometry
    assert capabilities.text is False

def test_update_style_command_is_atomic_and_undoable():
    session = EditSession({"objects": [{"id": "line-1", "type": "line", "style": {"color": "#000000"}}]})
    session.select("line-1", "list")
    assert session.execute(UpdateStyleCommand("line-1", {"color": "#0072B2"})).changed
    assert session.undo().changed
    assert session.document["objects"][0]["style"]["color"] == "#000000"
    assert session.redo().changed

def test_invalid_command_does_not_change_document_or_history():
    session = EditSession({"objects": [{"id": "line-1", "type": "line", "style": {}}]})
    session.select("line-1", "list")
    before = deepcopy(session.document)
    result = session.execute(UpdateStyleCommand("line-1", {"color": "bad"}))
    assert result.error_code == "invalid_color"
    assert session.document == before and session.can_undo is False
```

- [ ] **Step 2: Implement the public core types.**

```python
@dataclass(frozen=True)
class EditCapabilities:
    style: bool = False
    color: bool = False
    line_width: bool = False
    line_style: bool = False
    marker: bool = False
    marker_size: bool = False
    text: bool = False
    font_size: bool = False
    geometry: bool = False
    crop: bool = False
    deletable: bool = False
    reorderable: bool = False
    locked: bool = False

@dataclass(frozen=True)
class EditResult:
    changed: bool
    error_code: str = ""
    message: str = ""
    affected_ids: tuple[str, ...] = ()

@dataclass(frozen=True)
class SelectionState:
    object_id: str = ""
    source: str = ""

class EditCommand(Protocol):
    def apply(self, document: dict) -> tuple[EditResult, object]: ...
    def revert(self, document: dict, snapshot: object) -> EditResult: ...
```

`capabilities_for()` must define `image_background`, `text`, `line`, `arrow`, `rectangle`, `highlight`, `plot_series`, `legend`, and unknown-object behavior. Color validation must accept six-digit hex and renderer-supported named colors. A failed command must not mutate the document, selection, or history.

- [ ] **Step 3: Implement `EditSession`.**

```python
class EditSession:
    def __init__(self, document: dict): ...
    @property
    def document(self) -> dict: ...
    @property
    def selection(self) -> SelectionState: ...
    @property
    def dirty(self) -> bool: ...
    def select(self, object_id: str, source: str) -> None: ...
    def execute(self, command: EditCommand) -> EditResult: ...
    def undo(self) -> EditResult: ...
    def redo(self) -> EditResult: ...
    def mark_saved(self) -> None: ...
```

Implement `AddObjectCommand`, `DeleteObjectCommand`, `UpdateStyleCommand`, `UpdateTextCommand`, `UpdateGeometryCommand`, `MoveLayerCommand`, `SetVisibilityCommand`, `PasteObjectCommand`, and `CropCanvasCommand`. Commands snapshot affected fields, clear redo history after a new successful change, and create no history entry for no-ops.

- [ ] **Step 4: Run core tests and commit.**

```powershell
pytest -q tests/test_figure_edit_capabilities.py tests/test_figure_edit_commands.py tests/test_figure_edit_session.py
git add polynexus/core/figure_edit_capabilities.py polynexus/core/figure_edit_commands.py polynexus/core/figure_edit_session.py tests/test_figure_edit_capabilities.py tests/test_figure_edit_commands.py tests/test_figure_edit_session.py
git commit -m "feat: add command-based figure edit session"
```

## Task 4: Make persistence transactional

**Files:** Create `polynexus/core/figure_edit_persistence.py`; modify `polynexus/gui/widgets/chart_editor_save_mixin.py`; test with `tests/test_figure_edit_persistence.py`, `tests/test_chart_editor_save_mixin.py`, and `tests/test_plot_edits.py`.

- [ ] **Step 1: Add save-success and save-failure tests.**

```python
def test_save_bundle_writes_asset_document_and_compatibility_state(tmp_path):
    result = save_edit_bundle(tmp_path / "edited.png", {"version": 1, "objects": []}, b"new-image", {}, [])
    assert result.ok and result.target_path.read_bytes() == b"new-image"
    assert result.document_path.exists() and result.compatibility_path.exists()

def test_save_failure_keeps_previous_target(tmp_path, monkeypatch):
    target = tmp_path / "edited.png"
    target.write_bytes(b"old-image")
    monkeypatch.setattr(Path, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    result = try_save_edit_bundle(target, {"version": 1, "objects": []}, b"new-image")
    assert result.ok is False and result.error_code == "save_failed"
    assert target.read_bytes() == b"old-image"
```

- [ ] **Step 2: Implement `SaveBundleResult` and atomic replacement.**

```python
@dataclass(frozen=True)
class SaveBundleResult:
    ok: bool
    target_path: Path
    document_path: Path
    compatibility_path: Path | None
    error_code: str = ""
    message: str = ""
```

The module also exposes `try_save_edit_bundle(target_path, document, rendered_bytes, legacy_style=None, legacy_annotations=None)`, which catches filesystem and JSON errors and returns `SaveBundleResult` instead of raising through the UI.

Write rendered asset and normalized JSON to sibling temporary files, close and reload the JSON, then replace final files. Write legacy `plot_edits.json` only after canonical files are ready. On failure, keep the previous target and return `save_failed`.

- [ ] **Step 3: Route `_save_to_path()`, `_save_generated_document_figure()`, and the static branch through the bundle.**

On failure keep `_editor_dirty` true and set the translated error status. On success call `EditSession.mark_saved()` and emit `figure_saved` once.

- [ ] **Step 4: Run tests and commit.**

```powershell
pytest -q tests/test_figure_edit_persistence.py tests/test_chart_editor_save_mixin.py tests/test_plot_edits.py
git add polynexus/core/figure_edit_persistence.py polynexus/gui/widgets/chart_editor_save_mixin.py tests/test_figure_edit_persistence.py tests/test_chart_editor_save_mixin.py
git commit -m "feat: save Origin edits through a transactional bundle"
```

## Task 5: Make annotation canvas a projection of the session

**Files:** Create `polynexus/gui/widgets/annotation_render_adapter.py`; modify `polynexus/gui/widgets/annotation_canvas.py` and `chart_editor_edit_session_mixin.py`; test with `tests/test_annotation_render_adapter.py` and `tests/test_annotation_canvas.py`.

- [ ] **Step 1: Add projection and proposed-edit tests.**

```python
def make_loaded_canvas(tmp_path):
    path = tmp_path / "source.png"
    image = QImage(160, 100, QImage.Format_RGBA8888)
    image.fill(QColor("white"))
    assert image.save(str(path))
    canvas = AnnotationCanvas()
    assert canvas.load_image(str(path)) is True
    return canvas

def move_scene_item(canvas, object_id, dx, dy):
    item = next(item for item in canvas._scene.items() if item.data(0) == object_id)
    item.moveBy(dx, dy)

def test_canvas_projects_canonical_objects_and_returns_id_map(tmp_path):
    canvas = make_loaded_canvas(tmp_path)
    mapping = canvas.set_document_objects([{"id": "ann-1", "type": "text", "x": .2, "y": .3, "text": "Peak", "style": {"color": "#0072B2"}}])
    assert set(mapping) == {"ann-1"}
    assert canvas.annotation_state()[0]["text"] == "Peak"

def test_drag_emits_proposed_geometry_change(qtbot, tmp_path):
    canvas = make_loaded_canvas(tmp_path)
    canvas.set_document_objects([{"id": "ann-1", "type": "line", "x1": .1, "y1": .1, "x2": .5, "y2": .5}])
    events = []
    canvas.object_edit_requested.connect(events.append)
    move_scene_item(canvas, "ann-1", 10, 5)
    canvas.flush_pending_object_edit()
    assert events[-1].object_id == "ann-1"
```

- [ ] **Step 2: Implement the adapter boundary.**

```python
class AnnotationRenderAdapter:
    def __init__(self, scene): ...
    def replace_objects(self, objects: list[dict]) -> dict[str, object]: ...
    def sync_object(self, object_payload: dict) -> object | None: ...
    def clear(self) -> None: ...
    def scene_state(self) -> list[dict]: ...
```

Keep normalized coordinates and selection visuals. `AnnotationCanvas` delegates item construction and scene projection but retains compatibility methods such as `load_image()`, `annotation_state()`, `render_to_image()`, and `set_tool()`. It must not create a persistent history entry when the session projects a document.

- [ ] **Step 3: Connect proposed canvas edits to commands.**

`ChartEditorEditSessionMixin` subscribes to `object_edit_requested`, creates `UpdateGeometryCommand` or `UpdateStyleCommand`, executes it, and projects `session.document["objects"]` back to the canvas with signals blocked during projection.

- [ ] **Step 4: Run annotation tests and commit.**

```powershell
pytest -q tests/test_annotation_render_adapter.py tests/test_annotation_canvas.py
git add polynexus/gui/widgets/annotation_render_adapter.py polynexus/gui/widgets/annotation_canvas.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py tests/test_annotation_render_adapter.py tests/test_annotation_canvas.py
git commit -m "refactor: project annotations from the shared edit session"
```

## Task 6: Route generated objects, selection, and controls through the session

**Files:** Modify `polynexus/core/figure_object_store.py`, `polynexus/gui/figure_selection_model.py`, `chart_editor_generated_selection_mixin.py`, `chart_editor_generated_geometry_mixin.py`, `chart_editor_annotation_controls_mixin.py`, and `chart_editor_object_list_mixin.py`; test with `tests/test_figure_object_store.py`, `tests/test_figure_selection_model.py`, and `tests/test_chart_editor_workflow.py`.

- [ ] **Step 1: Add shared selection and one-history tests.**

```python
def test_selection_model_supports_generated_and_annotation_sources(qtbot):
    model = FigureSelectionModel()
    events = []
    model.selection_changed.connect(lambda object_id, source: events.append((object_id, source)))
    model.select("line-1", "generated-canvas")
    model.select("ann-1", "annotation-canvas")
    assert events == [("line-1", "generated-canvas"), ("ann-1", "annotation-canvas")]

def test_generated_style_and_geometry_share_one_undo_stack(editor):
    editor.set_source_figure(editor.generated_line_path)
    editor._select_generated_object("line-1", "list")
    editor._annotation_color_edit.setText("#009E73")
    editor._btn_annotation_apply_style.click()
    editor._annotation_x_spin.setValue(.2)
    assert editor._edit_session.can_undo is True
    editor._on_annotation_undo()
    editor._on_annotation_undo()
    assert editor._generated_store().get("line-1")["style"]["color"] != "#009E73"
```

- [ ] **Step 2: Add `_execute_edit()` and `_project_edit_result()` to the adapter.**

```python
def _execute_edit(self, command):
    result = self._edit_session.execute(command)
    self._project_edit_result(result)
    return result

def _project_edit_result(self, result):
    self._sync_editor_from_session()
    self._status_label.setText(result.message)
    self._sync_header_actions()
```

Create the session on `set_source_figure()`/`set_figure_generator()`, clear it when the source changes, and expose it to existing mixins. Keep `FigureObjectStore` for reads and compatibility; replace UI calls to direct `update_style`, `update_geometry`, `soft_delete`, and `move` with commands.

- [ ] **Step 3: Route all controls and object-list actions.**

`_on_annotation_apply_style()` builds one capability-filtered `UpdateStyleCommand`; text, geometry, delete, paste, reorder, visibility, and rename use their corresponding commands. List selection calls `session.select(id, "list")`; canvas selection calls `session.select(id, "canvas")`. A successful command projects canvas, Inspector, list, dirty state, and `figure_changed` exactly once.

- [ ] **Step 4: Run integration tests and commit.**

```powershell
pytest -q tests/test_figure_object_store.py tests/test_figure_selection_model.py tests/test_chart_editor_workflow.py tests/test_chart_editor_annotation_controls_mixin.py tests/test_chart_editor_generated_geometry_mixin.py tests/test_chart_editor_object_list_mixin.py
git add polynexus/core/figure_object_store.py polynexus/gui/figure_selection_model.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/widgets/chart_editor_generated_selection_mixin.py polynexus/gui/widgets/chart_editor_generated_geometry_mixin.py polynexus/gui/widgets/chart_editor_annotation_controls_mixin.py polynexus/gui/widgets/chart_editor_object_list_mixin.py tests/test_figure_object_store.py tests/test_figure_selection_model.py tests/test_chart_editor_workflow.py
git commit -m "feat: route generated and annotation edits through one session"
```

## Task 7: Add the A-direction toolbar and capability-driven Inspector

**Files:** Modify `polynexus/gui/widgets/chart_editor.py`, `chart_editor_layout_mixin.py`, `chart_editor_edit_session_mixin.py`, and `polynexus/gui/i18n.py`; test with `tests/test_chart_editor_layout.py` and `tests/test_chart_editor_workflow.py`.

- [ ] **Step 1: Add toolbar contract tests.**

```python
def test_editor_exposes_stable_context_action_ids():
    editor = ChartEditor()
    assert editor._editor_toolbar.action_ids() == [
        "select", "text", "line", "arrow", "rectangle", "undo", "redo", "export",
    ]
```

- [ ] **Step 2: Add translation keys** `EDITOR_TOOL_SELECT`, `EDITOR_TOOL_TEXT`, `EDITOR_TOOL_LINE`, `EDITOR_TOOL_ARROW`, `EDITOR_TOOL_RECTANGLE`, `EDITOR_TOOL_UNDO`, `EDITOR_TOOL_REDO`, `EDITOR_TOOL_EXPORT`, `EDITOR_STATUS_SELECTED`, `EDITOR_STATUS_APPLIED`, `EDITOR_STATUS_INVALID_COLOR`, and `EDITOR_STATUS_SAVE_FAILED` to the English and Chinese maps and cover them in the retranslate test.

```python
EDITOR_TOOL_SELECT = {"en": "Select", "zh": "选择"}
EDITOR_TOOL_TEXT = {"en": "Text", "zh": "文字"}
EDITOR_STATUS_INVALID_COLOR = {"en": "Invalid color", "zh": "颜色格式无效"}
EDITOR_STATUS_SAVE_FAILED = {"en": "Save failed", "zh": "保存失败"}
```

- [ ] **Step 3: Implement stable toolbar actions.**

```python
actions = {
    "select": self._activate_select_tool,
    "text": self._activate_text_tool,
    "line": self._activate_line_tool,
    "arrow": self._activate_arrow_tool,
    "rectangle": self._activate_rectangle_tool,
    "undo": self._undo_edit,
    "redo": self._redo_edit,
    "export": self._open_export_menu,
}
```

Use `QToolButton`s or `QAction`s with these ids. Derive checked/enabled state from the session; do not add separate generated/static button paths. Preserve the 640px canvas minimum established by the existing layout regression.

- [ ] **Step 4: Make Inspector fields capability-driven.**

Implement `_sync_inspector_from_selection()` using `capabilities_for(selected_object)`. Unsupported fields are disabled with a tooltip explaining why. Color uses a swatch/color dialog plus validated hex input. Apply, undo, and redo report the command result without claiming success when rendering or persistence fails.

- [ ] **Step 5: Run layout/workflow tests and commit.**

```powershell
pytest -q tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py
git add polynexus/gui/widgets/chart_editor.py polynexus/gui/widgets/chart_editor_layout_mixin.py polynexus/gui/widgets/chart_editor_edit_session_mixin.py polynexus/gui/i18n.py tests/test_chart_editor_layout.py tests/test_chart_editor_workflow.py
git commit -m "feat: add context toolbar and capability-driven Origin Inspector"
```

## Task 8: Close Phase 1 with full verification and a Phase 2 handoff

**Files:** Update `tests/test_chart_editor_workflow.py`, `tests/test_annotation_canvas.py`, and `tests/test_chart_editor_layout.py`; create `docs/superpowers/specs/2026-07-17-origin-editor-phase2-data-aware-design.md`.

- [ ] **Step 1: Add the object edit matrix.**

```python
@pytest.fixture
def editor_factory(tmp_path):
    def factory(object_type):
        if object_type == "text":
            return make_static_editor(tmp_path)
        return make_generated_editor(tmp_path, object_type)
    return factory

def document_object(editor, object_id):
    return next(item for item in editor._edit_session.document["objects"] if item["id"] == object_id)

def add_text_for_test(editor, text):
    editor._annotation_text_edit.setText(text)
    editor._btn_annotation_add_text.click()
    return editor._annotation_canvas.selected_annotation_id()

def apply_default_edit_for_test(editor, object_id):
    editor._edit_session.select(object_id, "test")
    if object_id.startswith("text"):
        return editor._execute_edit(UpdateTextCommand(object_id, "Label edited"))
    return editor._execute_edit(UpdateStyleCommand(object_id, {"color": "#0072B2"}))

@pytest.mark.parametrize("object_type", ["line", "arrow", "text", "rectangle", "highlight", "plot_series"])
def test_object_edit_round_trip(object_type, editor_factory):
    editor = editor_factory(object_type)
    object_id = f"{object_type}-1" if object_type != "text" else add_text_for_test(editor, "Label")
    before = deepcopy(document_object(editor, object_id))
    apply_default_edit_for_test(editor, object_id)
    after = deepcopy(document_object(editor, object_id))
    assert after != before
    assert editor._edit_session.undo().changed is True
    assert document_object(editor, object_id) == before
    assert editor._edit_session.redo().changed is True
    assert document_object(editor, object_id) == after
```

These helpers remain in the test module. `apply_default_edit_for_test()` calls the public session command with `color="#0072B2"` for style-capable objects and `text="Label edited"` for text.

- [ ] **Step 2: Run Qt tests serially and run quality checks.**

```powershell
$files = @(Get-ChildItem tests -File | Where-Object { $_.Name -like 'test_chart_editor*.py' -or $_.Name -like 'test_annotation*.py' } | Select-Object -ExpandProperty FullName)
pytest -q $files
ruff check polynexus tests
python -m compileall -q polynexus
git diff --check
```

- [ ] **Step 3: Run focused integration tests.**

```powershell
pytest -q tests/test_plot_gallery_service.py tests/test_chart_viewer.py tests/test_figure_window_service.py tests/test_main_window_persistence.py
```

- [ ] **Step 4: Write the Phase 2 handoff spec.**

Record the stable Phase 1 contracts: `EditSession`, `EditCommand`, `EditCapabilities`, canonical object ids, `data_sources`, `recipe`, renderer mappings, and the rule that data re-rendering preserves user-created annotations unless the user explicitly confirms removal.

- [ ] **Step 5: Review and commit the final tests and handoff.**

```powershell
git diff --stat
git status --short
git add tests/test_chart_editor_workflow.py tests/test_annotation_canvas.py tests/test_chart_editor_layout.py docs/superpowers/specs/2026-07-17-origin-editor-phase2-data-aware-design.md
git commit -m "test: close Origin editor phase one and document phase two seam"
```

## Plan self-review

- The approved design's canonical document, edit session, command protocol, capability registry, rendering boundary, transactional persistence, Phase 1 acceptance criteria, compatibility behavior, tests, and rollout are all covered by Tasks 2–8.
- Phase 2 data editing is intentionally a separate spec and is not mixed into Phase 1 UI work.
- Every new state-changing UI path is routed through `_execute_edit()`; no new handler may mutate `_figure_document`, `_annotations`, or `FigureObjectStore` directly.
- Core commands are tested without Qt before Qt integration tests run.
- Legacy sidecars remain readable and are written only after the canonical save bundle succeeds.
- The plan contains no unresolved placeholders or undefined task-to-task interfaces.

Plan complete and saved to `docs/superpowers/plans/2026-07-17-origin-editor-practicality-phase1-plan.md`. Implementation must use `superpowers:subagent-driven-development` or `superpowers:executing-plans` and must preserve the untracked `.superpowers/` directory.
