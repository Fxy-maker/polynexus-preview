import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.annotation_canvas import AnnotationCanvas


def _send_canvas_drag(canvas, start_x, start_y, end_x, end_y):
    viewport = canvas._view.viewport()
    start = QPointF(canvas._view.mapFromScene(QPointF(start_x, start_y)))
    end = QPointF(canvas._view.mapFromScene(QPointF(end_x, end_y)))
    start_global = QPointF(viewport.mapToGlobal(start.toPoint()))
    end_global = QPointF(viewport.mapToGlobal(end.toPoint()))
    press = QMouseEvent(
        QEvent.MouseButtonPress,
        start,
        start,
        start_global,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    release = QMouseEvent(
        QEvent.MouseButtonRelease,
        end,
        end,
        end_global,
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier,
    )
    app = QApplication.instance() or QApplication([])
    app.sendEvent(viewport, press)
    app.sendEvent(viewport, release)
    return press, release


def test_annotation_canvas_renders_text_overlay(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()

    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Edited", 20, 10)
    annotations = canvas.annotation_state()
    rendered = canvas.render_to_image()

    assert annotation_id
    assert len(annotations) == 1
    assert annotations[0]["type"] == "text"
    assert annotations[0]["text"] == "Edited"
    assert annotations[0]["x"] == 0.25
    assert annotations[0]["y"] == 0.25
    assert not rendered.isNull()
    assert rendered.width() >= 80
    assert rendered.height() >= 40

    canvas.deleteLater()
    app.processEvents()


def test_document_mode_text_drag_requests_box_without_local_mutation(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects([])
    requests = []
    canvas.text_entry_requested.connect(requests.append)

    assert canvas.set_tool("text") is True
    assert canvas._finish_mouse_draw(QPointF(10, 8), QPointF(70, 28)) == ""

    assert requests == [
        {
            "type": "text",
            "geometry": {"x": 0.1, "y": 0.16, "width": 0.6, "height": 0.4},
        }
    ]
    assert canvas.annotation_state() == []

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_text_box_applies_persisted_width(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Peak region", 10, 8, width=60, height=20)
    item = next(item for item in canvas._scene.items() if item.data(0) == annotation_id)

    assert item.textWidth() == 60
    assert canvas.selected_annotation()["width"] == 0.6
    assert canvas.selected_annotation()["height"] == 0.4

    canvas.deleteLater()
    app.processEvents()


def test_text_annotation_exposes_resize_handles_and_updates_box_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Peak", 10, 8, width=60, height=20)
    assert canvas.select_annotation(annotation_id) is True

    assert len(canvas._selection_handle_items) == 4
    assert canvas._begin_selection_handle_drag(QPointF(10, 8)) is True
    assert canvas._finish_selection_handle_drag(QPointF(5, 5)) is True

    geometry = canvas.selected_annotation()
    assert geometry["x"] == 0.05
    assert geometry["y"] == 0.1
    assert geometry["width"] == 0.65
    assert geometry["height"] == 0.46

    canvas.deleteLater()
    app.processEvents()


def test_select_mode_leaves_object_mouse_move_for_graphics_view(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.add_rectangle_annotation(10, 8, 40, 20)
    viewport = canvas._view.viewport()
    point = QPointF(canvas._view.mapFromScene(QPointF(25, 18)))
    global_point = QPointF(viewport.mapToGlobal(point.toPoint()))
    event = QMouseEvent(
        QEvent.MouseMove,
        point,
        point,
        global_point,
        Qt.NoButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )

    assert canvas.eventFilter(viewport, event) is False

    canvas.deleteLater()
    app.processEvents()


def test_static_rectangle_body_drag_updates_position_and_is_undoable(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    canvas.resize(400, 300)
    canvas.show()
    app.processEvents()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_rectangle_annotation(10, 8, 40, 20)
    canvas.set_zoom_100()
    canvas.select_annotation(annotation_id)
    viewport = canvas._view.viewport()

    def event(event_type, scene_point, buttons):
        local = QPointF(canvas._view.mapFromScene(scene_point))
        global_pos = QPointF(viewport.mapToGlobal(local.toPoint()))
        return QMouseEvent(
            event_type,
            local,
            local,
            global_pos,
            Qt.LeftButton if event_type != QEvent.MouseMove else Qt.NoButton,
            buttons,
            Qt.NoModifier,
        )

    app.sendEvent(viewport, event(QEvent.MouseButtonPress, QPointF(25, 18), Qt.LeftButton))
    app.sendEvent(viewport, event(QEvent.MouseMove, QPointF(45, 28), Qt.LeftButton))
    app.sendEvent(viewport, event(QEvent.MouseButtonRelease, QPointF(45, 28), Qt.NoButton))

    moved = canvas.selected_annotation()
    assert moved["x"] == 0.3
    assert moved["y"] == 0.36
    assert len(canvas._undo_stack) == 2
    assert canvas.undo() is True
    assert canvas.selected_annotation()["x"] == 0.1
    assert canvas.redo() is True
    assert canvas.selected_annotation()["x"] == 0.3

    canvas.deleteLater()
    app.processEvents()


def test_static_creation_qt_gesture_returns_to_select_after_commit(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    canvas.resize(400, 300)
    canvas.show()
    app.processEvents()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_zoom_100()
    assert canvas.set_tool("rectangle") is True

    _send_canvas_drag(canvas, 10, 8, 70, 28)

    assert canvas.current_tool() == "select"
    assert canvas._interaction_controller.tool.value == "select"
    assert canvas.annotation_state()[0]["type"] == "rectangle"

    canvas.deleteLater()
    app.processEvents()


def test_document_mode_line_drag_requests_canonical_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects([])
    requests = []
    canvas.object_create_requested.connect(requests.append)

    assert canvas.set_tool("line") is True
    assert canvas._finish_mouse_draw(QPointF(10, 5), QPointF(70, 25)) == ""

    assert requests == [
        {
            "type": "line",
            "geometry": {"x1": 0.1, "y1": 0.1, "x2": 0.7, "y2": 0.5},
        }
    ]
    assert canvas.annotation_state() == []

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_shows_and_clears_drag_preview(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects([])
    viewport = canvas._view.viewport()
    start = QPointF(canvas._view.mapFromScene(QPointF(10, 5)))
    end = QPointF(canvas._view.mapFromScene(QPointF(70, 25)))
    start_global = QPointF(viewport.mapToGlobal(start.toPoint()))
    end_global = QPointF(viewport.mapToGlobal(end.toPoint()))

    assert canvas.set_tool("line") is True
    app.sendEvent(
        viewport,
        QMouseEvent(
            QEvent.MouseButtonPress,
            start,
            start,
            start_global,
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        ),
    )
    app.sendEvent(
        viewport,
        QMouseEvent(
            QEvent.MouseMove,
            end,
            end,
            end_global,
            Qt.NoButton,
            Qt.LeftButton,
            Qt.NoModifier,
        ),
    )

    assert canvas._draw_preview_item is not None

    app.sendEvent(
        viewport,
        QMouseEvent(
            QEvent.MouseButtonRelease,
            end,
            end,
            end_global,
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        ),
    )
    assert canvas._draw_preview_item is None

    canvas.deleteLater()
    app.processEvents()


def test_selected_static_curve_control_handle_commits_one_geometry_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.1,
                "y1": 0.8,
                "x2": 0.9,
                "y2": 0.8,
                "control_x": 0.5,
                "control_y": 0.1,
            }
        ]
    )
    assert canvas.select_annotation("curve-1") is True
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas._begin_selection_handle_drag(QPointF(50, 5)) is True
    assert canvas._update_selection_handle_drag(QPointF(45, 20)) is True
    assert canvas._finish_selection_handle_drag(QPointF(45, 20)) is True

    assert requests == [
        {
            "object_id": "curve-1",
            "source": "annotation_canvas",
            "geometry": {
                "x1": 0.1,
                "y1": 0.8,
                "x2": 0.9,
                "y2": 0.8,
                "control_x": 0.45,
                "control_y": 0.4,
            },
            "object_type": "curve",
        }
    ]

    canvas.deleteLater()
    app.processEvents()


def test_selected_static_line_endpoint_commits_one_geometry_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [{"id": "line-1", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7}]
    )
    assert canvas.select_annotation("line-1") is True
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas._begin_selection_handle_drag(QPointF(10, 10)) is True
    assert canvas._finish_selection_handle_drag(QPointF(25, 20)) is True

    assert requests[-1]["geometry"] == {"x1": 0.25, "y1": 0.4, "x2": 0.8, "y2": 0.7}

    canvas.deleteLater()
    app.processEvents()


def test_legacy_static_handle_drag_routes_through_document_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    original = {"id": "legacy-line", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7}
    canvas.load_annotation_state([original])
    canvas.set_document_interaction_enabled(True)
    assert canvas.select_annotation("legacy-line") is True
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas._begin_selection_handle_drag(QPointF(10, 10)) is True
    assert canvas._finish_selection_handle_drag(QPointF(25, 20)) is True

    assert requests == [
        {
            "object_id": "legacy-line",
            "source": "annotation_canvas",
            "geometry": {"x1": 0.25, "y1": 0.4, "x2": 0.8, "y2": 0.7},
            "object_type": "line",
        }
    ]
    assert canvas.annotation_state() == [original]

    canvas.deleteLater()
    app.processEvents()


def test_legacy_static_delete_routes_through_document_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    original = {"id": "legacy-line", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7}
    canvas.load_annotation_state([original])
    canvas.set_document_interaction_enabled(True)
    assert canvas.select_annotation("legacy-line") is True
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas.delete_selected_annotation() is True

    assert requests == [
        {
            "object_id": "legacy-line",
            "source": "annotation_canvas",
            "operation": "delete",
        }
    ]
    assert canvas.annotation_state() == [original]

    canvas.deleteLater()
    app.processEvents()


def test_legacy_static_nudge_routes_through_document_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    original = {"id": "legacy-line", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7}
    canvas.load_annotation_state([original])
    canvas.set_document_interaction_enabled(True)
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas.move_annotation("legacy-line", 20, 10) is True

    assert requests == [
        {
            "object_id": "legacy-line",
            "source": "annotation_canvas",
            "geometry": {"x1": 0.3, "y1": 0.4, "x2": 1.0, "y2": 0.9},
            "object_type": "line",
        }
    ]
    assert canvas.annotation_state() == [original]

    canvas.deleteLater()
    app.processEvents()


def test_legacy_static_scene_drag_routes_through_document_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    original = {"id": "legacy-line", "type": "line", "x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.7}
    canvas.load_annotation_state([original])
    canvas.set_document_interaction_enabled(True)
    line_item = next(item for item in canvas._scene.items() if item.data(0) == "legacy-line")
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    line_item.moveBy(20, 10)
    assert canvas.sync_scene_items_to_state() is True

    assert requests == [
        {
            "object_id": "legacy-line",
            "source": "annotation_canvas",
            "geometry": {"x1": 0.3, "y1": 0.4, "x2": 1.0, "y2": 0.9},
            "object_type": "line",
        }
    ]
    assert canvas.annotation_state() == [original]

    canvas.deleteLater()
    app.processEvents()


def test_selected_static_rectangle_corner_commits_one_geometry_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [{"id": "region", "type": "rectangle", "x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}]
    )
    assert canvas.select_annotation("region") is True
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas._begin_selection_handle_drag(QPointF(10, 10)) is True
    assert canvas._finish_selection_handle_drag(QPointF(5, 5)) is True

    assert requests[-1]["geometry"] == {"x": 0.05, "y": 0.1, "width": 0.45, "height": 0.4}

    canvas.deleteLater()
    app.processEvents()


def test_escape_cancels_static_handle_drag_without_emitting_geometry_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    original = {"id": "region", "type": "rectangle", "x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}
    canvas.set_document_objects([original])
    assert canvas.select_annotation("region") is True
    requests = []
    canvas.object_edit_requested.connect(requests.append)

    assert canvas._begin_selection_handle_drag(QPointF(10, 10)) is True
    assert canvas._update_selection_handle_drag(QPointF(5, 5)) is True
    canvas.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))

    assert canvas._selection_handle_drag is None
    assert requests == []
    assert canvas.annotation_state() == [original]
    assert canvas._render_adapter.scene_state() == [original]

    canvas.deleteLater()
    app.processEvents()


def test_static_rectangle_handle_hover_uses_diagonal_resize_cursor(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    canvas.resize(400, 300)
    canvas.show()
    app.processEvents()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [{"id": "region", "type": "rectangle", "x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}]
    )
    assert canvas.select_annotation("region") is True
    app.processEvents()
    viewport = canvas._view.viewport()
    local = QPointF(canvas._view.mapFromScene(QPointF(10, 10)))
    global_pos = QPointF(viewport.mapToGlobal(local.toPoint()))

    event = QMouseEvent(
        QEvent.MouseMove,
        local,
        local,
        global_pos,
        Qt.NoButton,
        Qt.NoButton,
        Qt.NoModifier,
    )
    assert canvas.eventFilter(viewport, event) is True

    assert viewport.cursor().shape() == Qt.SizeFDiagCursor

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_renders_legacy_dashed_line_style(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_line_annotation(10, 10, 80, 35)
    assert canvas.update_selected_properties(line_style="--") is True
    item = next(item for item in canvas._scene.items() if item.data(0) == annotation_id)

    assert item.pen().style() == Qt.DashLine

    canvas.deleteLater()
    app.processEvents()


def test_static_canvas_export_omits_transient_preview_and_selection_handles(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [{"id": "region", "type": "rectangle", "x": 0.1, "y": 0.2, "width": 0.4, "height": 0.3}]
    )
    assert canvas.select_annotation("region") is True
    canvas._update_draw_preview(QPointF(20, 5), QPointF(80, 40))

    exported_with_editor_overlays = canvas.render_to_image()
    canvas._clear_draw_preview()
    canvas.clear_selection()
    exported_without_editor_overlays = canvas.render_to_image()

    assert [
        exported_with_editor_overlays.pixelColor(x, y).rgba()
        for y in range(exported_with_editor_overlays.height())
        for x in range(exported_with_editor_overlays.width())
    ] == [
        exported_without_editor_overlays.pixelColor(x, y).rgba()
        for y in range(exported_without_editor_overlays.height())
        for x in range(exported_without_editor_overlays.width())
    ]

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_projects_document_objects_without_local_undo(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    objects = [
        {
            "id": "document-text",
            "type": "text",
            "x": 0.2,
            "y": 0.25,
            "text": "Projected",
        }
    ]

    id_map = canvas.set_document_objects(objects)

    assert set(id_map) == {"document-text"}
    assert canvas.annotation_state() == objects
    assert canvas._undo_stack == []
    assert canvas.undo() is False

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_projects_curve_document_object(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.1,
                "y1": 0.8,
                "x2": 0.9,
                "y2": 0.8,
                "control_x": 0.5,
                "control_y": 0.1,
                "style": {"color": "#0072B2", "line_width": 2.0},
            }
        ]
    )

    assert canvas.annotation_state()[0]["type"] == "curve"
    assert any(item.data(0) == "curve-1" for item in canvas._scene.items())

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_flushes_drag_as_object_edit_request(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [{"id": "document-text", "type": "text", "x": 0.2, "y": 0.25, "text": "Drag"}]
    )
    requests = []
    canvas.object_edit_requested.connect(requests.append)
    item = next(item for item in canvas._scene.items() if item.data(0) == "document-text")

    item.moveBy(20, 10)
    assert canvas.flush_pending_object_edit() is True

    assert len(requests) == 1
    request = requests[0]
    assert request["object_id"] == "document-text"
    assert request["source"] == "annotation_canvas"
    assert request["geometry"] == {"x": 0.4, "y": 0.45}
    assert canvas._undo_stack == []

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_replace_image_preserves_annotations(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Kept", 20, 10)

    replacement = QImage(120, 60, QImage.Format_ARGB32)
    replacement.fill(QColor("#eeeeee"))

    assert canvas.replace_image(replacement) is True
    assert canvas.image_size() == (120, 60)
    assert canvas.selected_annotation_id() == annotation_id
    annotations = canvas.annotation_state()
    assert len(annotations) == 1
    assert annotations[0]["text"] == "Kept"
    assert annotations[0]["x"] == 0.25
    assert annotations[0]["y"] == 0.25

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_undo_redo_annotation_changes(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    annotation_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    assert len(canvas.annotation_state()) == 1
    assert canvas.annotation_state()[0]["type"] == "rectangle"
    assert canvas.annotation_state()[0]["x"] == 0.1
    assert canvas.annotation_state()[0]["width"] == 0.3

    assert canvas.remove_annotation(annotation_id) is True
    assert canvas.annotation_state() == []

    assert canvas.undo() is True
    assert len(canvas.annotation_state()) == 1

    assert canvas.redo() is True
    assert canvas.annotation_state() == []

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_supports_line_arrow_and_highlight(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    line_id = canvas.add_line_annotation(10, 5, 50, 25)
    arrow_id = canvas.add_arrow_annotation(20, 10, 60, 30)
    highlight_id = canvas.add_highlight_annotation(5, 5, 40, 20)
    annotations = canvas.annotation_state()
    rendered = canvas.render_to_image()

    assert {line_id, arrow_id, highlight_id}
    assert [item["type"] for item in annotations] == ["line", "arrow", "highlight"]
    assert annotations[0]["x1"] == 0.1
    assert annotations[0]["y2"] == 0.5
    assert annotations[2]["width"] == 0.4
    assert annotations[2]["height"] == 0.4
    assert not rendered.isNull()

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_supports_bezier_curve(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    curve_id = canvas.add_curve_annotation(10, 40, 90, 40, 50, 5)

    curve = canvas.selected_annotation()
    assert curve["id"] == curve_id
    assert curve["type"] == "curve"
    assert curve["x1"] == 0.1
    assert curve["y2"] == 0.8
    assert curve["control_x"] == 0.5
    assert curve["control_y"] == 0.1
    assert any(item.data(0) == curve_id for item in canvas._scene.items())

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_curve_tool_creates_and_updates_control_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    assert canvas.set_tool("curve") is True
    assert canvas._finish_mouse_draw(QPointF(10, 40), QPointF(90, 40))
    curve = canvas.selected_annotation()
    assert curve["type"] == "curve"

    assert canvas.update_selected_geometry(control_x=0.4, control_y=0.2) is True
    updated = canvas.selected_annotation()
    assert updated["control_x"] == 0.4
    assert updated["control_y"] == 0.2

    canvas.deleteLater()
    app.processEvents()


def test_curve_tool_uses_a_distance_aware_bend_by_default(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(200, 100)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    assert canvas.set_tool("curve") is True
    assert canvas._finish_mouse_draw(QPointF(20, 80), QPointF(180, 80))

    curve = canvas.selected_annotation()
    midpoint_y = (curve["y1"] + curve["y2"]) / 2.0
    assert abs(curve["control_y"] - midpoint_y) >= 0.25

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_moves_curve_with_its_control_point(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill()
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    curve_id = canvas.add_curve_annotation(10, 40, 80, 35, 45, 5)

    assert canvas.move_annotation(curve_id, 10, -5) is True
    curve = canvas.selected_annotation()

    assert curve["x1"] == 0.2
    assert curve["y1"] == 0.7
    assert curve["x2"] == 0.9
    assert curve["y2"] == 0.6
    assert curve["control_x"] == 0.55
    assert curve["control_y"] == 0.0

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_syncs_a_dragged_curve_with_its_control_point(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill()
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    curve_id = canvas.add_curve_annotation(10, 40, 80, 35, 45, 5)
    item = next(item for item in canvas._scene.items() if item.data(0) == curve_id)
    item.setPos(QPointF(10, -5))

    assert canvas.sync_scene_items_to_state() is True
    curve = canvas.selected_annotation()

    assert curve["x1"] == 0.2
    assert curve["y1"] == 0.7
    assert curve["x2"] == 0.9
    assert curve["y2"] == 0.6
    assert curve["control_x"] == 0.55
    assert curve["control_y"] == 0.0

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_copies_curve_with_an_offset_control_point(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill()
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    curve_id = canvas.add_curve_annotation(10, 40, 80, 35, 45, 5)
    assert canvas.copy_selected_annotation() is True

    copied_id = canvas.paste_annotation()
    copied = canvas.selected_annotation()

    assert copied_id != curve_id
    assert copied["x1"] == 0.15
    assert copied["y1"] == 0.9
    assert copied["x2"] == 0.85
    assert copied["y2"] == 0.8
    assert copied["control_x"] == 0.5
    assert copied["control_y"] == 0.2

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_crops_curve_with_control_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill()
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    curve_id = canvas.add_curve_annotation(20, 40, 80, 35, 50, 5)

    assert canvas.crop_to_rect(10, 0, 80, 50) is True
    curve = next(item for item in canvas.annotation_state() if item["id"] == curve_id)

    assert curve["x1"] == 0.125
    assert curve["y1"] == 0.8
    assert curve["x2"] == 0.875
    assert curve["y2"] == 0.7
    assert curve["control_x"] == 0.5
    assert curve["control_y"] == 0.1

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_styles_curve_line_width(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill()
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.add_curve_annotation(10, 40, 80, 35, 45, 5)

    assert canvas.update_selected_properties(color="#0072B2", line_width=3.5) is True
    curve = canvas.selected_annotation()

    assert curve["color"] == "#0072B2"
    assert curve["line_width"] == 3.5

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_segment_tools_select_new_annotation(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    line_id = canvas.add_line_annotation(10, 5, 50, 25)
    assert canvas.selected_annotation_id() == line_id

    arrow_id = canvas.add_arrow_annotation(20, 10, 60, 30)
    assert canvas.selected_annotation_id() == arrow_id

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_zoom_controls_change_view_scale(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    canvas.set_zoom_100()
    assert canvas.zoom_level() == 1.0

    assert canvas.zoom_in() is True
    assert canvas.zoom_level() > 1.0

    assert canvas.zoom_out() is True
    assert canvas.zoom_level() == 1.0

    assert canvas.fit_to_window() is True
    assert canvas.zoom_mode() == "fit"

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_draw_rectangle_with_mouse_drag(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_zoom_100()
    canvas.set_tool("rectangle")

    press, release = _send_canvas_drag(canvas, 10, 5, 40, 20)

    annotations = canvas.annotation_state()
    assert press.isAccepted()
    assert release.isAccepted()
    assert canvas.current_tool() == "select"
    assert len(annotations) == 1
    assert annotations[0]["type"] == "rectangle"
    assert annotations[0]["x"] == 0.1
    assert annotations[0]["y"] == 0.1
    assert annotations[0]["width"] == 0.3
    assert annotations[0]["height"] == 0.3

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_draw_arrow_with_mouse_drag(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_zoom_100()
    canvas.set_tool("arrow")

    _press, release = _send_canvas_drag(canvas, 10, 5, 50, 25)

    annotations = canvas.annotation_state()
    assert release.isAccepted()
    assert canvas.current_tool() == "select"
    assert len(annotations) == 1
    assert annotations[0]["type"] == "arrow"
    assert annotations[0]["x1"] == 0.1
    assert annotations[0]["y1"] == 0.1
    assert annotations[0]["x2"] == 0.5
    assert annotations[0]["y2"] == 0.5

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_keyboard_zoom_shortcuts(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_zoom_100()

    zoom_in_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Plus, Qt.ControlModifier)
    canvas.keyPressEvent(zoom_in_event)
    assert canvas.zoom_level() > 1.0
    assert zoom_in_event.isAccepted()

    zoom_out_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Minus, Qt.ControlModifier)
    canvas.keyPressEvent(zoom_out_event)
    assert canvas.zoom_level() == 1.0
    assert zoom_out_event.isAccepted()

    canvas.zoom_in()
    reset_event = QKeyEvent(QEvent.KeyPress, Qt.Key_0, Qt.ControlModifier)
    canvas.keyPressEvent(reset_event)
    assert canvas.zoom_level() == 1.0
    assert reset_event.isAccepted()

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_select_move_and_delete_selected(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    annotation_id = canvas.add_text_annotation("Move me", 10, 5)
    assert canvas.select_annotation(annotation_id) is True
    assert canvas.selected_annotation_id() == annotation_id

    assert canvas.move_annotation(annotation_id, 20, 10) is True
    moved = canvas.annotation_state()[0]
    assert moved["x"] == 0.3
    assert moved["y"] == 0.3

    assert canvas.delete_selected_annotation() is True
    assert canvas.annotation_state() == []
    assert canvas.selected_annotation_id() == ""

    assert canvas.undo() is True
    assert canvas.annotation_state()[0]["id"] == annotation_id

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_scene_drag_syncs_annotation_state(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    text_id = canvas.add_text_annotation("Drag me", 10, 5)
    line_id = canvas.add_line_annotation(10, 5, 50, 25)

    text_item = next(item for item in canvas._scene.items() if item.data(0) == text_id)
    line_item = next(item for item in canvas._scene.items() if item.data(0) == line_id)

    assert text_item.flags() & text_item.GraphicsItemFlag.ItemIsMovable
    assert line_item.flags() & line_item.GraphicsItemFlag.ItemIsMovable

    text_item.moveBy(20, 10)
    line_item.moveBy(10, 5)
    assert canvas.sync_scene_items_to_state() is True

    state_by_id = {item["id"]: item for item in canvas.annotation_state()}
    assert state_by_id[text_id]["x"] == 0.3
    assert state_by_id[text_id]["y"] == 0.3
    assert state_by_id[line_id]["x1"] == 0.2
    assert state_by_id[line_id]["y1"] == 0.2
    assert state_by_id[line_id]["x2"] == 0.6
    assert state_by_id[line_id]["y2"] == 0.6

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_arrow_scene_item_moves_as_one_object(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    arrow_id = canvas.add_arrow_annotation(10, 5, 50, 25)

    arrow_item = next(item for item in canvas._scene.items() if item.data(0) == arrow_id)
    assert len(arrow_item.childItems()) >= 2
    assert arrow_item.flags() & arrow_item.GraphicsItemFlag.ItemIsMovable

    arrow_item.moveBy(10, 5)
    assert canvas.sync_scene_items_to_state() is True

    annotation = canvas.annotation_state()[0]
    assert annotation["x1"] == 0.2
    assert annotation["y1"] == 0.2
    assert annotation["x2"] == 0.6
    assert annotation["y2"] == 0.6

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_scene_selection_updates_selected_annotation(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Select me", 10, 5)
    canvas._selected_annotation_id = ""

    scene_item = next(item for item in canvas._scene.items() if item.data(0) == annotation_id)
    scene_item.setSelected(False)
    app.processEvents()
    scene_item.setSelected(True)
    app.processEvents()

    assert canvas.selected_annotation_id() == annotation_id

    canvas.deleteLater()
    app.processEvents()


def test_scene_selected_curve_keeps_handles_after_drag_preview(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [
            {
                "id": "curve-1",
                "type": "curve",
                "x1": 0.1,
                "y1": 0.8,
                "x2": 0.9,
                "y2": 0.8,
                "control_x": 0.5,
                "control_y": 0.1,
            }
        ]
    )
    canvas._selected_annotation_id = ""
    scene_item = next(item for item in canvas._scene.items() if item.data(0) == "curve-1")
    scene_item.setSelected(True)
    app.processEvents()

    assert canvas.selected_annotation_id() == "curve-1"
    assert len(canvas._selection_handle_items) == 3
    assert canvas._begin_selection_handle_drag(QPointF(50, 5)) is True
    assert canvas._update_selection_handle_drag(QPointF(45, 20)) is True

    assert canvas.selected_annotation_id() == "curve-1"
    assert len(canvas._selection_handle_items) == 3

    canvas.deleteLater()
    app.processEvents()


def test_legacy_curve_without_control_points_remains_selectable(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects(
        [
            {
                "id": "legacy-curve",
                "type": "curve",
                "geometry": {"x1": 0.1, "y1": 0.8, "x2": 0.9, "y2": 0.8},
            }
        ]
    )

    assert canvas.select_annotation("legacy-curve") is True
    assert len(canvas._selection_handle_items) == 2

    canvas.deleteLater()
    app.processEvents()


def test_document_handle_preview_updates_nested_geometry_without_selection_churn(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    curve = {
        "id": "curve-1",
        "type": "curve",
        "geometry": {
            "x1": 0.1,
            "y1": 0.8,
            "x2": 0.9,
            "y2": 0.8,
            "control_x": 0.5,
            "control_y": 0.1,
        },
    }
    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.set_document_objects([curve])
    assert canvas.select_annotation("curve-1") is True
    selection_changes = []
    canvas.selection_changed.connect(selection_changes.append)

    assert canvas._begin_selection_handle_drag(QPointF(50, 5)) is True
    assert canvas._update_selection_handle_drag(QPointF(45, 20)) is True

    preview = canvas._render_adapter.scene_state()[0]
    assert preview["geometry"]["control_x"] == 0.45
    assert preview["geometry"]["control_y"] == 0.4
    assert selection_changes == []

    canvas.deleteLater()
    app.processEvents()


def test_local_handle_drag_renders_geometry_preview(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_line_annotation(10, 10, 80, 35)

    assert canvas._begin_selection_handle_drag(QPointF(10, 10)) is True
    assert canvas._update_selection_handle_drag(QPointF(25, 20)) is True

    preview = canvas._draw_preview_item
    assert preview is not None
    assert preview.line().p1() == QPointF(25, 20)
    assert canvas._selection_handle_items[0].rect().center() == QPointF(25, 20)
    assert canvas.selected_annotation_id() == annotation_id

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_returns_selected_annotation_payload(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Select me", 10, 5)
    assert canvas.update_selected_properties(color="#0072B2", font_size=16) is True

    selected = canvas.selected_annotation()

    assert selected["id"] == annotation_id
    assert selected["color"] == "#0072B2"
    assert selected["font_size"] == 16
    selected["color"] = "#000000"
    assert canvas.selected_annotation()["color"] == "#0072B2"

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_delete_key_removes_selected_annotation(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    assert canvas.select_annotation(annotation_id) is True

    event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    canvas.keyPressEvent(event)

    assert canvas.annotation_state() == []
    assert event.isAccepted()

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_inner_view_key_events_use_canvas_shortcuts(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    assert canvas.select_annotation(annotation_id) is True

    delete_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    app.sendEvent(canvas._view, delete_event)
    assert canvas.annotation_state() == []
    assert delete_event.isAccepted()

    canvas.add_rectangle_annotation(10, 5, 30, 15)
    undo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    app.sendEvent(canvas._view, undo_event)
    assert canvas.annotation_state() == []
    assert undo_event.isAccepted()

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_ctrl_z_and_ctrl_y_shortcuts(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    canvas.add_rectangle_annotation(10, 5, 30, 15)

    undo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    canvas.keyPressEvent(undo_event)
    assert canvas.annotation_state() == []
    assert undo_event.isAccepted()

    redo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Y, Qt.ControlModifier)
    canvas.keyPressEvent(redo_event)
    assert len(canvas.annotation_state()) == 1
    assert redo_event.isAccepted()

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_ctrl_z_after_scene_drag_restores_previous_position(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Drag me", 10, 5)
    scene_item = next(item for item in canvas._scene.items() if item.data(0) == annotation_id)

    scene_item.moveBy(20, 10)
    undo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    canvas.keyPressEvent(undo_event)

    annotations = canvas.annotation_state()
    assert len(annotations) == 1
    assert annotations[0]["x"] == 0.1
    assert annotations[0]["y"] == 0.1
    assert undo_event.isAccepted()

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_arrow_keys_nudge_selected_annotation(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Nudge", 10, 5)
    assert canvas.select_annotation(annotation_id) is True

    right_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier)
    canvas.keyPressEvent(right_event)
    assert canvas.annotation_state()[0]["x"] == 0.11
    assert right_event.isAccepted()

    down_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.ShiftModifier)
    canvas.keyPressEvent(down_event)
    moved = canvas.annotation_state()[0]
    assert moved["x"] == 0.11
    assert moved["y"] == 0.3
    assert down_event.isAccepted()

    assert canvas.undo() is True
    assert canvas.annotation_state()[0]["y"] == 0.1

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_updates_selected_text(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Old", 10, 5)
    assert canvas.select_annotation(annotation_id) is True

    assert canvas.update_selected_text("New label") is True
    assert canvas.annotation_state()[0]["text"] == "New label"

    assert canvas.undo() is True
    assert canvas.annotation_state()[0]["text"] == "Old"

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_updates_selected_annotation_properties(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    text_id = canvas.add_text_annotation("Label", 10, 5)
    assert canvas.select_annotation(text_id) is True
    assert canvas.update_selected_properties(color="#0072B2", font_size=18) is True
    text = canvas.annotation_state()[0]
    assert text["color"] == "#0072B2"
    assert text["font_size"] == 18

    rect_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    assert canvas.select_annotation(rect_id) is True
    assert canvas.update_selected_properties(color="#D55E00", line_width=4.5) is True
    rect = [item for item in canvas.annotation_state() if item["id"] == rect_id][0]
    assert rect["color"] == "#D55E00"
    assert rect["line_width"] == 4.5

    highlight_id = canvas.add_highlight_annotation(5, 5, 30, 10)
    assert canvas.select_annotation(highlight_id) is True
    assert canvas.update_selected_properties(color="#F0E442", alpha=0.6) is True
    highlight = [item for item in canvas.annotation_state() if item["id"] == highlight_id][0]
    assert highlight["color"] == "#F0E442"
    assert highlight["alpha"] == 0.6

    assert canvas.undo() is True
    highlight = [item for item in canvas.annotation_state() if item["id"] == highlight_id][0]
    assert highlight["alpha"] == 0.35

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_updates_selected_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Move", 20, 10)
    assert canvas.select_annotation(annotation_id) is True

    assert canvas.update_selected_geometry(x=0.5, y=0.75) is True

    annotation = canvas.annotation_state()[0]
    assert annotation["x"] == 0.5
    assert annotation["y"] == 0.75

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_updates_selected_size_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    assert canvas.select_annotation(annotation_id) is True

    assert canvas.update_selected_geometry(width=0.6, height=0.5) is True

    annotation = canvas.annotation_state()[0]
    assert annotation["width"] == 0.6
    assert annotation["height"] == 0.5

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_updates_selected_segment_geometry(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_arrow_annotation(10, 5, 40, 20)
    assert canvas.select_annotation(annotation_id) is True

    assert canvas.update_selected_geometry(x1=0.2, y1=0.3, x2=0.8, y2=0.9) is True

    annotation = canvas.annotation_state()[0]
    assert annotation["x1"] == 0.2
    assert annotation["y1"] == 0.3
    assert annotation["x2"] == 0.8
    assert annotation["y2"] == 0.9

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_copy_paste_selected_annotation(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_text_annotation("Copy me", 10, 5)
    assert canvas.update_selected_properties(color="#0072B2", font_size=16) is True
    assert canvas.copy_selected_annotation() is True

    pasted_id = canvas.paste_annotation()
    annotations = canvas.annotation_state()
    pasted = [item for item in annotations if item["id"] == pasted_id][0]

    assert pasted_id
    assert pasted_id != annotation_id
    assert len(annotations) == 2
    assert pasted["text"] == "Copy me"
    assert pasted["color"] == "#0072B2"
    assert pasted["font_size"] == 16
    assert pasted["x"] == 0.15
    assert pasted["y"] == 0.2
    assert canvas.selected_annotation_id() == pasted_id

    assert canvas.undo() is True
    assert len(canvas.annotation_state()) == 1

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_ctrl_c_and_ctrl_v_copy_paste(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    annotation_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    assert canvas.select_annotation(annotation_id) is True

    copy_event = QKeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier)
    canvas.keyPressEvent(copy_event)
    assert copy_event.isAccepted()

    paste_event = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier)
    canvas.keyPressEvent(paste_event)
    annotations = canvas.annotation_state()

    assert paste_event.isAccepted()
    assert len(annotations) == 2
    assert annotations[1]["type"] == "rectangle"
    assert annotations[1]["x"] == 0.15
    assert annotations[1]["y"] == 0.2

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_reorders_selected_annotation_layers(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    first_id = canvas.add_rectangle_annotation(10, 5, 30, 15)
    second_id = canvas.add_highlight_annotation(15, 10, 30, 15)
    third_id = canvas.add_text_annotation("Top", 20, 15)

    assert [item["id"] for item in canvas.annotation_state()] == [
        first_id,
        second_id,
        third_id,
    ]

    assert canvas.select_annotation(first_id) is True
    assert canvas.bring_selected_to_front() is True
    assert [item["id"] for item in canvas.annotation_state()] == [
        second_id,
        third_id,
        first_id,
    ]

    assert canvas.send_selected_to_back() is True
    assert [item["id"] for item in canvas.annotation_state()] == [
        first_id,
        second_id,
        third_id,
    ]

    assert canvas.undo() is True
    assert [item["id"] for item in canvas.annotation_state()] == [
        second_id,
        third_id,
        first_id,
    ]

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_crop_reframes_image_and_annotations(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True

    text_id = canvas.add_text_annotation("Inside", 30, 15)
    rect_id = canvas.add_rectangle_annotation(20, 10, 20, 10)
    outside_id = canvas.add_text_annotation("Outside", 90, 45)

    assert canvas.crop_to_rect(20, 10, 40, 20) is True

    rendered = canvas.render_to_image()
    annotations = {item["id"]: item for item in canvas.annotation_state()}

    assert rendered.width() == 40
    assert rendered.height() == 20
    assert text_id in annotations
    assert rect_id in annotations
    assert outside_id not in annotations
    assert annotations[text_id]["x"] == 0.25
    assert annotations[text_id]["y"] == 0.25
    assert annotations[rect_id]["x"] == 0.0
    assert annotations[rect_id]["y"] == 0.0
    assert annotations[rect_id]["width"] == 0.5
    assert annotations[rect_id]["height"] == 0.5

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_undo_redo_crop_restores_image_size(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    text_id = canvas.add_text_annotation("Inside", 30, 15)

    assert canvas.crop_to_rect(20, 10, 40, 20) is True
    assert canvas.render_to_image().size().width() == 40

    assert canvas.undo() is True
    undo_image = canvas.render_to_image()
    undo_annotation = canvas.annotation_state()[0]
    assert undo_image.width() == 100
    assert undo_image.height() == 50
    assert undo_annotation["id"] == text_id
    assert undo_annotation["x"] == 0.3
    assert undo_annotation["y"] == 0.3

    assert canvas.redo() is True
    redo_image = canvas.render_to_image()
    redo_annotation = canvas.annotation_state()[0]
    assert redo_image.width() == 40
    assert redo_image.height() == 20
    assert redo_annotation["x"] == 0.25
    assert redo_annotation["y"] == 0.25

    canvas.deleteLater()
    app.processEvents()


def test_annotation_canvas_crop_undo_redo_restores_image_size(tmp_path):
    app = QApplication.instance() or QApplication([])
    image_path = tmp_path / "source.png"
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))

    canvas = AnnotationCanvas()
    assert canvas.load_image(str(image_path)) is True
    text_id = canvas.add_text_annotation("Inside", 30, 15)

    assert canvas.crop_to_rect(20, 10, 40, 20) is True
    assert canvas.image_size() == (40, 20)

    assert canvas.undo() is True
    assert canvas.image_size() == (100, 50)
    assert canvas.render_to_image().size().width() == 100
    restored = {item["id"]: item for item in canvas.annotation_state()}
    assert restored[text_id]["x"] == 0.3
    assert restored[text_id]["y"] == 0.3

    assert canvas.redo() is True
    assert canvas.image_size() == (40, 20)
    assert canvas.render_to_image().size().width() == 40

    canvas.deleteLater()
    app.processEvents()
