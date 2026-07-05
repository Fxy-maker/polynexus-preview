import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPixmap
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
