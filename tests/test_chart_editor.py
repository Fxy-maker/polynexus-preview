import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.core.plot_edits import load_figure_annotations, load_figure_asset_spec


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


def _image_bytes(image):
    image = image.convertToFormat(QImage.Format_RGBA8888)
    return bytes(image.constBits())


def test_chart_editor_style_preset_round_trip(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    editor = ChartEditor()
    editor._colour_cb.setCurrentText("Warm")
    editor._font_cb.setCurrentText("Large")
    editor._lw_cb.setCurrentText("Thick")
    editor._figsize_cb.setCurrentText("Square")
    editor._grid_cb.setChecked(False)
    editor._grid_sl.setValue(1)
    editor._bg_color = "#F0F0F0"

    editor._style_preset_combo.setEditText("Paper Warm")
    editor._on_save_style_preset()

    editor._colour_cb.setCurrentText("Cool")
    editor._font_cb.setCurrentText("Small")
    editor._lw_cb.setCurrentText("Thin")
    editor._figsize_cb.setCurrentText("Medium (6in)")
    editor._grid_cb.setChecked(True)
    editor._grid_sl.setValue(8)
    editor._bg_color = "#FFFFFF"

    editor._style_preset_combo.setEditText("Paper Warm")
    editor._on_apply_style_preset()

    assert editor._colour_cb.currentText() == "Warm"
    assert editor._font_cb.currentText() == "Large"
    assert editor._lw_cb.currentText() == "Thick"
    assert editor._figsize_cb.currentText() == "Square"
    assert editor._grid_cb.isChecked() is False
    assert editor._grid_sl.value() == 1
    assert editor._bg_color == "#F0F0F0"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_retranslate_updates_style_preset_text(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("zh")
        editor.retranslate()

        assert editor._btn_style_preset_save.text() == tr("EDITOR_STYLE_PRESET_SAVE")
        assert editor._grid_cb.text() == tr("EDITOR_GRID")
        assert editor._style_preset_combo.lineEdit().placeholderText() == tr(
            "EDITOR_STYLE_PRESET_PLACEHOLDER"
        )
    finally:
        set_language(previous)

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_hint_describes_direct_save(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("en")
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        assert "re-plot" not in editor._status_label.text().lower()

        set_language("zh")
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        assert "\u91cd\u65b0\u7ed8\u56fe" not in editor._status_label.text()
    finally:
        set_language(previous)

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_mode_primary_action_describes_saving_current_figure(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("en")
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        assert editor._btn_save_current.text() == tr("EDITOR_SAVE_CURRENT")

        editor._annotation_canvas.add_text_annotation("Saved", 4, 4)
        editor.save_to_target()
        assert "current figure" in editor._status_label.text().lower()
        assert "settings" not in editor._status_label.text().lower()
    finally:
        set_language(previous)

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_file_save_updates_current_image(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    before = figure_path.read_bytes()

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._title_edit.setText("Edited")
    editor.save_to_target()

    assert figure_path.read_bytes() != before
    assert figure_path.stat().st_size > 0

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_title_edit_updates_visible_annotation_canvas(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._annotation_canvas.isHidden() is False
    assert editor._canvas.isHidden() is True
    before = _image_bytes(editor._annotation_canvas.render_to_image())

    editor._title_edit.setText("11111")
    app.processEvents()

    after = _image_bytes(editor._annotation_canvas.render_to_image())
    assert after != before

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_save_current_creates_backup_before_overwrite(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    backup_path = figure_path.with_name(f"{figure_path.name}.bak")
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    before = figure_path.read_bytes()

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Backup note", 20, 10)
    editor.save_to_target()

    assert backup_path.exists()
    assert backup_path.read_bytes() == before
    assert figure_path.read_bytes() != before

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_save_current_keeps_existing_backup(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    backup_path = figure_path.with_name(f"{figure_path.name}.bak")
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    backup_path.write_bytes(b"original backup")

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Do not clobber", 20, 10)
    editor.save_to_target()

    assert backup_path.read_bytes() == b"original backup"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_annotation_save_updates_file_and_sidecar(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    before = figure_path.read_bytes()

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._annotation_canvas is not None
    editor._annotation_canvas.add_text_annotation("Edited", 20, 10)
    editor.save_to_target()

    annotations = load_figure_annotations(str(figure_path))
    asset_spec = load_figure_asset_spec(str(figure_path))

    assert figure_path.read_bytes() != before
    assert annotations[0]["text"] == "Edited"
    assert annotations[0]["x"] == 0.25
    assert asset_spec["figure_id"] == "source"
    assert asset_spec["preview_path"] == str(figure_path.resolve())
    assert asset_spec["width_px"] == 80
    assert asset_spec["height_px"] == 40

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_annotation_drag_save_persists_new_coordinates(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    annotation_id = editor._annotation_canvas.add_text_annotation("Dragged", 20, 10)
    scene_item = next(
        item for item in editor._annotation_canvas._scene.items() if item.data(0) == annotation_id
    )
    scene_item.moveBy(16, 8)
    editor.save_to_target()

    annotations = load_figure_annotations(str(figure_path))

    assert annotations[0]["text"] == "Dragged"
    assert annotations[0]["x"] == 0.45
    assert annotations[0]["y"] == 0.45

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_annotation_buttons_add_text_and_undo(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    editor._annotation_text_edit.setText("Button note")
    editor._btn_annotation_add_text.click()
    assert editor._annotation_canvas.annotation_state()[0]["text"] == "Button note"

    editor._btn_annotation_undo.click()
    assert editor._annotation_canvas.annotation_state() == []

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_annotation_buttons_choose_shape_tools_for_mouse_drawing(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.set_zoom_100()

    editor._btn_annotation_add_line.click()
    assert editor._annotation_canvas.current_tool() == "line"
    assert editor._btn_annotation_add_line.isChecked()
    assert editor._annotation_canvas.annotation_state() == []
    _send_canvas_drag(editor._annotation_canvas, 10, 5, 40, 20)
    assert not editor._btn_annotation_add_line.isChecked()

    editor._btn_annotation_add_arrow.click()
    assert editor._annotation_canvas.current_tool() == "arrow"
    assert editor._btn_annotation_add_arrow.isChecked()
    _send_canvas_drag(editor._annotation_canvas, 20, 10, 50, 25)
    assert not editor._btn_annotation_add_arrow.isChecked()

    editor._btn_annotation_add_highlight.click()
    assert editor._annotation_canvas.current_tool() == "highlight"
    assert editor._btn_annotation_add_highlight.isChecked()
    _send_canvas_drag(editor._annotation_canvas, 5, 5, 35, 15)
    assert not editor._btn_annotation_add_highlight.isChecked()

    assert [item["type"] for item in editor._annotation_canvas.annotation_state()] == [
        "line",
        "arrow",
        "highlight",
    ]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_crop_button_crops_static_canvas(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.set_zoom_100()
    text_id = editor._annotation_canvas.add_text_annotation("Inside", 30, 15)

    editor._btn_annotation_crop.click()
    assert editor._annotation_canvas.current_tool() == "crop"
    assert editor._btn_annotation_crop.isChecked()

    _send_canvas_drag(editor._annotation_canvas, 20, 10, 60, 30)
    rendered = editor._annotation_canvas.render_to_image()
    annotations = {item["id"]: item for item in editor._annotation_canvas.annotation_state()}

    assert not editor._btn_annotation_crop.isChecked()
    assert rendered.width() == 40
    assert rendered.height() == 20
    assert annotations[text_id]["x"] == 0.25
    assert annotations[text_id]["y"] == 0.25

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_crop_save_updates_file_and_asset_spec(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    assert editor._annotation_canvas.crop_to_rect(20, 10, 40, 20) is True
    editor.save_to_target()

    saved = QPixmap(str(figure_path))
    asset_spec = load_figure_asset_spec(str(figure_path))

    assert saved.width() == 40
    assert saved.height() == 20
    assert asset_spec["width_px"] == 40
    assert asset_spec["height_px"] == 20

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_edit_manual_acceptance_flow(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    copy_path = tmp_path / "figures" / "source_review.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    original_bytes = figure_path.read_bytes()

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.set_zoom_100()
    editor._annotation_canvas.add_text_annotation("Manual flow", 30, 15)
    editor._annotation_canvas.add_arrow_annotation(20, 10, 60, 25)
    editor._annotation_canvas.add_rectangle_annotation(20, 10, 30, 15)
    assert editor._annotation_canvas.crop_to_rect(10, 5, 80, 40) is True
    editor.save_to_target()

    assert figure_path.read_bytes() != original_bytes
    assert figure_path.with_name(f"{figure_path.name}.bak").read_bytes() == original_bytes

    reopened = ChartEditor()
    reopened.set_source_figure(str(figure_path))
    annotations = reopened._annotation_canvas.annotation_state()

    assert [item["type"] for item in annotations] == ["text", "arrow", "rectangle"]
    assert annotations[0]["text"] == "Manual flow"
    assert reopened._annotation_canvas.image_size() == (80, 40)

    before_save_as = figure_path.read_bytes()
    reopened._save_to_path(str(copy_path))

    copy_spec = load_figure_asset_spec(str(copy_path))
    assert figure_path.read_bytes() == before_save_as
    assert copy_path.exists()
    assert copy_path.read_bytes() != original_bytes
    assert copy_spec["figure_id"] == "source_review"
    assert copy_spec["width_px"] == 80
    assert copy_spec["height_px"] == 40

    editor.deleteLater()
    reopened.deleteLater()
    app.processEvents()


def test_chart_editor_annotation_zoom_buttons_control_canvas_view(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    editor._btn_annotation_zoom_100.click()
    assert editor._annotation_canvas.zoom_level() == 1.0

    editor._btn_annotation_zoom_in.click()
    assert editor._annotation_canvas.zoom_level() > 1.0

    editor._btn_annotation_zoom_out.click()
    assert editor._annotation_canvas.zoom_level() == 1.0

    editor._btn_annotation_fit.click()
    assert editor._annotation_canvas.zoom_mode() == "fit"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_delete_selected_annotation_button(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.set_zoom_100()

    editor._btn_annotation_add_rect.click()
    _send_canvas_drag(editor._annotation_canvas, 10, 5, 40, 20)
    assert len(editor._annotation_canvas.annotation_state()) == 1
    editor._btn_annotation_delete.click()

    assert editor._annotation_canvas.annotation_state() == []

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_copy_paste_annotation_buttons(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    annotation_id = editor._annotation_canvas.add_text_annotation("Copy button", 20, 10)
    assert editor._annotation_canvas.select_annotation(annotation_id) is True
    editor._btn_annotation_copy.click()
    editor._btn_annotation_paste.click()

    annotations = editor._annotation_canvas.annotation_state()
    assert len(annotations) == 2
    assert annotations[1]["text"] == "Copy button"
    assert annotations[1]["id"] != annotation_id
    assert annotations[1]["x"] == 0.3125
    assert annotations[1]["y"] == 0.375

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_layer_order_buttons(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    first_id = editor._annotation_canvas.add_rectangle_annotation(10, 5, 30, 15)
    second_id = editor._annotation_canvas.add_highlight_annotation(15, 10, 30, 15)
    third_id = editor._annotation_canvas.add_text_annotation("Top", 20, 15)

    assert editor._annotation_canvas.select_annotation(first_id) is True
    editor._btn_annotation_front.click()
    assert [item["id"] for item in editor._annotation_canvas.annotation_state()] == [
        second_id,
        third_id,
        first_id,
    ]

    editor._btn_annotation_back.click()
    assert [item["id"] for item in editor._annotation_canvas.annotation_state()] == [
        first_id,
        second_id,
        third_id,
    ]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_update_selected_text_button(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    annotation_id = editor._annotation_canvas.add_text_annotation("Old", 20, 10)
    assert editor._annotation_canvas.select_annotation(annotation_id) is True
    editor._annotation_text_edit.setText("New")
    editor._btn_annotation_update_text.click()

    assert editor._annotation_canvas.annotation_state()[0]["text"] == "New"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_annotation_property_controls_update_selected_item(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    text_id = editor._annotation_canvas.add_text_annotation("Styled", 20, 10)
    assert editor._annotation_canvas.select_annotation(text_id) is True
    editor._annotation_color_edit.setText("#0072B2")
    editor._annotation_font_size_spin.setValue(18)
    editor._btn_annotation_apply_style.click()

    text = editor._annotation_canvas.annotation_state()[0]
    assert text["color"] == "#0072B2"
    assert text["font_size"] == 18

    line_id = editor._annotation_canvas.add_line_annotation(10, 5, 40, 20)
    assert editor._annotation_canvas.select_annotation(line_id) is True
    editor._annotation_color_edit.setText("#D55E00")
    editor._annotation_line_width_spin.setValue(4.5)
    editor._btn_annotation_apply_style.click()

    line = [item for item in editor._annotation_canvas.annotation_state() if item["id"] == line_id][0]
    assert line["color"] == "#D55E00"
    assert line["line_width"] == 4.5

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_selection_updates_annotation_property_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    text_id = editor._annotation_canvas.add_text_annotation("Styled", 20, 10)
    editor._annotation_canvas.update_selected_properties(color="#0072B2", font_size=18)
    editor._annotation_canvas.select_annotation(text_id)

    assert editor._annotation_color_edit.text() == "#0072B2"
    assert editor._annotation_font_size_spin.value() == 18

    line_id = editor._annotation_canvas.add_line_annotation(10, 5, 40, 20)
    editor._annotation_canvas.update_selected_properties(color="#D55E00", line_width=4.5)
    editor._annotation_canvas.select_annotation(line_id)

    assert editor._annotation_color_edit.text() == "#D55E00"
    assert editor._annotation_line_width_spin.value() == 4.5

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_save_as_keeps_original_file(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    copy_path = tmp_path / "figures" / "source_edited.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    before = figure_path.read_bytes()

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Copy note", 20, 10)
    editor._save_to_path(str(copy_path))

    annotations = load_figure_annotations(str(copy_path))
    asset_spec = load_figure_asset_spec(str(copy_path))

    assert figure_path.read_bytes() == before
    assert not figure_path.with_name(f"{figure_path.name}.bak").exists()
    assert copy_path.exists()
    assert copy_path.read_bytes() != before
    assert annotations[0]["text"] == "Copy note"
    assert asset_spec["figure_id"] == "source_edited"
    assert asset_spec["preview_path"] == str(copy_path.resolve())

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_static_canvas_can_save_pdf_and_svg_with_annotations(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    pdf_path = tmp_path / "figures" / "source_annotated.pdf"
    svg_path = tmp_path / "figures" / "source_annotated.svg"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Vector note", 20, 10)

    assert editor._save_static_canvas_to_path(pdf_path) is True
    assert editor._save_static_canvas_to_path(svg_path) is True
    assert pdf_path.exists()
    assert svg_path.exists()
    assert pdf_path.stat().st_size > 0
    assert svg_path.stat().st_size > 0
    assert "<svg" in svg_path.read_text(encoding="utf-8", errors="ignore").lower()

    editor.deleteLater()
    app.processEvents()
