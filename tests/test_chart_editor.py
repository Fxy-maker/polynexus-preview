import csv
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import matplotlib as mpl
from matplotlib.backend_bases import MouseEvent

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.chart_editor import ChartEditor
from polynexus.core.figure_document import load_figure_document, save_generated_figure_document
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


def _send_matplotlib_canvas_click(canvas, xpix, ypix):
    device_pixel_ratio = getattr(canvas, "device_pixel_ratio", None)
    if not device_pixel_ratio:
        device_pixel_ratio = canvas.devicePixelRatioF()
    local = QPointF(
        float(xpix) / float(device_pixel_ratio),
        (float(canvas.figure.bbox.height) - float(ypix)) / float(device_pixel_ratio),
    )
    global_pos = QPointF(canvas.mapToGlobal(local.toPoint()))
    press = QMouseEvent(
        QEvent.MouseButtonPress,
        local,
        local,
        global_pos,
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    release = QMouseEvent(
        QEvent.MouseButtonRelease,
        local,
        local,
        global_pos,
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier,
    )
    app = QApplication.instance() or QApplication([])
    app.sendEvent(canvas, press)
    app.sendEvent(canvas, release)
    return press, release


def _send_matplotlib_canvas_move(canvas, xpix, ypix):
    device_pixel_ratio = getattr(canvas, "device_pixel_ratio", None)
    if not device_pixel_ratio:
        device_pixel_ratio = canvas.devicePixelRatioF()
    local = QPointF(
        float(xpix) / float(device_pixel_ratio),
        (float(canvas.figure.bbox.height) - float(ypix)) / float(device_pixel_ratio),
    )
    global_pos = QPointF(canvas.mapToGlobal(local.toPoint()))
    move = QMouseEvent(
        QEvent.MouseMove,
        local,
        local,
        global_pos,
        Qt.NoButton,
        Qt.NoButton,
        Qt.NoModifier,
    )
    app = QApplication.instance() or QApplication([])
    app.sendEvent(canvas, move)
    return move


def _send_matplotlib_canvas_mouse_event(
    canvas,
    event_type,
    xpix,
    ypix,
    *,
    button=Qt.NoButton,
    buttons=Qt.NoButton,
):
    device_pixel_ratio = getattr(canvas, "device_pixel_ratio", None)
    if not device_pixel_ratio:
        device_pixel_ratio = canvas.devicePixelRatioF()
    local = QPointF(
        float(xpix) / float(device_pixel_ratio),
        (float(canvas.figure.bbox.height) - float(ypix)) / float(device_pixel_ratio),
    )
    global_pos = QPointF(canvas.mapToGlobal(local.toPoint()))
    mouse_event = QMouseEvent(
        event_type,
        local,
        local,
        global_pos,
        button,
        buttons,
        Qt.NoModifier,
    )
    app = QApplication.instance() or QApplication([])
    app.sendEvent(canvas, mouse_event)
    return mouse_event


def _assert_selected_status(editor, label):
    status_text = editor._status_label.text()
    assert status_text.startswith(
        tr("EDITOR_SELECTED_STATUS_OBJECT", label)
    )
    return status_text


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
        assert editor._btn_save_current.text() == tr("EDITOR_SAVE_EDITS")

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


def test_chart_editor_static_save_writes_figure_document(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Peak", 20, 10)
    editor.save_to_target()

    document_path = figure_path.with_suffix(".pnfig.json")
    document = load_figure_document(str(figure_path))

    assert document_path.exists()
    assert document["mode"] == "static_background"
    assert document["figure_id"] == "source"
    assert [item["type"] for item in document["objects"]] == ["image_background", "text"]
    assert document["objects"][1]["text"] == "Peak"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_tracks_static_canvas_annotations(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    text_id = editor._annotation_canvas.add_text_annotation("Peak", 20, 10)

    assert editor._object_list.count() == 2
    assert editor._object_list.item(0).data(Qt.UserRole) == "__background__"
    assert editor._object_list.item(1).data(Qt.UserRole) == text_id
    assert "Peak" in editor._object_list.item(1).text()

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_tracks_generated_figure_objects(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-intensity",
                "type": "plot_series",
                "chart_kind": "line",
                "name": "I(q)",
                "data": {"x": [0.1, 0.2], "y": [10.0, 8.0]},
            },
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 0.16,
                "y1": 0.0,
                "x2": 0.16,
                "y2": 1.0,
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._object_list.count() == 4
    assert editor._object_list.item(0).data(Qt.UserRole) == "__background__"
    assert editor._object_list.item(1).data(Qt.UserRole) == "series-intensity"
    assert editor._object_list.item(1).data(Qt.UserRole + 1) == "figure_object"
    assert editor._object_list.item(1).text() == "Plot Series: I(q)"
    assert editor._object_list.item(2).data(Qt.UserRole) == "line-qstar"
    assert editor._object_list.item(2).data(Qt.UserRole + 1) == "figure_object"
    assert editor._object_list.item(2).text() == "Line: q*"
    assert editor._object_list.item(3).data(Qt.UserRole) == "legend"
    assert editor._object_list.item(3).text() == "Legend"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_opens_generated_figure_as_live_canvas(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        style={"xlabel": "2theta", "ylabel": "Intensity"},
        objects=[
            {
                "id": "series-measured",
                "type": "plot_series",
                "name": "Measured",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                "style": {"color": "#0072B2", "line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._canvas.isHidden() is False
    # Generated object editing hides Matplotlib's navigation toolbar so its
    # pan/zoom gesture cannot intercept annotation clicks and drags.
    assert editor._toolbar.isHidden() is True
    assert editor._annotation_canvas.isHidden() is True
    assert editor._figure.axes
    assert len(editor._figure.axes[0].lines) == 1
    assert editor._figure.axes[0].get_xlabel() == "2theta"
    assert editor._figure.axes[0].get_ylabel() == "Intensity"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_document_uses_object_mode_hint(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        style={"xlabel": "2theta", "ylabel": "Intensity"},
        objects=[
            {
                "id": "series-measured",
                "type": "plot_series",
                "name": "Measured",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor.is_static_file_mode() is False
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
    assert editor._annotation_canvas.isHidden() is True
    assert editor._object_list.item(1).text() == "Plot Series: Measured"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_entry_context_forces_static_mode_for_generated_document(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        style={"xlabel": "2theta", "ylabel": "Intensity"},
        objects=[
            {
                "id": "series-measured",
                "type": "plot_series",
                "name": "Measured",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
            }
        ],
    )

    entry = SimpleNamespace(
        figure_id="generated",
        title="Generated Figure",
        preview_path=str(figure_path),
        primary_path=str(figure_path),
        editable_path=str(figure_path),
        state="object_editing",
        document_mode="object",
    )

    editor = ChartEditor()
    editor.set_source_figure_entry(entry, force_static=True)

    assert editor.is_static_file_mode() is True
    assert editor._generated_document_mode is False
    assert editor._mode_title_label.text() == "Generated Figure"
    assert editor._mode_banner_label.text() == tr("EDITOR_MODE_STATIC")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_shows_persistent_object_mode_banner(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="temperature_overview",
        objects=[],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._mode_title_label.text() == "temperature overview"
    assert editor._mode_banner_label.text() == tr("EDITOR_MODE_OBJECT")
    assert editor._mode_summary_label.text() == tr("EDITOR_MODE_OBJECT_SUMMARY")
    assert any(token in editor._capability_badge.text().lower() for token in ("editable", "可编辑"))
    assert editor._status_label.text() != tr("EDITOR_MODE_OBJECT")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_shows_persistent_static_mode_banner(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._mode_title_label.text() == "source"
    assert editor._mode_banner_label.text() == tr("EDITOR_MODE_STATIC")
    assert editor._mode_summary_label.text() == tr("EDITOR_MODE_STATIC_SUMMARY")
    assert any(token in editor._capability_badge.text().lower() for token in ("editable", "可编辑"))

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_action_labels_distinguish_save_export_and_copy(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    editor = ChartEditor()
    editor.retranslate()

    assert editor._btn_save_current.text() == tr("EDITOR_SAVE_EDITS")
    assert editor._btn_publish.text() == tr("EDITOR_PUBLISH_COMPLETE")
    assert editor._btn_save_as.text() == tr("EDITOR_SAVE_AS_COPY")
    assert editor._btn_svg.text() == tr("EDITOR_EXPORT_SVG")
    assert editor._btn_png.text() == tr("EDITOR_EXPORT_PNG")
    assert editor._btn_publish.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generator_render_restores_matplotlib_rcparams(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))
    editor = ChartEditor()

    with mpl.rc_context({"savefig.bbox": None}):
        editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
        assert mpl.rcParams["savefig.bbox"] is None

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_legacy_document_render_restores_matplotlib_rcparams(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))
    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    QImage(40, 20, QImage.Format_ARGB32).save(str(figure_path))
    save_generated_figure_document(
        str(figure_path),
        figure_id="generated",
        objects=[
            {
                "id": "series",
                "type": "plot_series",
                "name": "Series",
                "data": {"x": [0.0, 1.0], "y": [0.0, 1.0]},
            }
        ],
    )
    editor = ChartEditor()

    with mpl.rc_context({"savefig.bbox": None}):
        editor.set_source_figure(str(figure_path))
        assert mpl.rcParams["savefig.bbox"] is None

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_placeholder_render_restores_matplotlib_rcparams(
    tmp_path,
    monkeypatch,
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))
    editor = ChartEditor()

    with mpl.rc_context({"savefig.bbox": None}):
        editor._show_placeholder_style_preview()
        assert mpl.rcParams["savefig.bbox"] is None

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_keeps_empty_object_document_in_object_mode(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-empty.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-empty",
        style={"xlabel": "q", "ylabel": "I(q)"},
        objects=[],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor.is_static_file_mode() is False
    assert editor._canvas.isHidden() is False
    assert editor._annotation_canvas.isHidden() is True
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
    assert editor._object_list.count() == 1
    assert editor._object_list.item(0).data(Qt.UserRole) == "__background__"
    assert editor._selected_figure_object_id == ""
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_canvas_pick_selects_generated_object_and_highlights_it(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [10.0, 20.0, 30.0], "y": [2.0, 3.0, 5.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"

    picked_artist = editor._figure.axes[0].lines[1]
    editor._on_generated_pick_event(SimpleNamespace(artist=picked_artist))

    assert editor._selected_figure_object_id == "series-b"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-b"
    assert editor._annotation_text_edit.text() == "B"
    selected_artist = editor._figure.axes[0].lines[1]
    assert selected_artist.get_path_effects()
    assert editor._figure.axes[0].lines[0].get_path_effects() == []

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_blank_canvas_click_clears_generated_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-blank-deselect.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-blank-deselect",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [10.0, 20.0, 30.0], "y": [2.0, 3.0, 5.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    picked_artist = editor._figure.axes[0].lines[1]
    editor._on_generated_pick_event(SimpleNamespace(artist=picked_artist))

    assert editor._selected_figure_object_id == "series-b"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-b"

    blank_press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        1.0,
        1.0,
        button=1,
    )
    editor._on_generated_button_press(blank_press_event)

    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_escape_key_clears_generated_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-escape-deselect.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-escape-deselect",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [10.0, 20.0, 30.0], "y": [2.0, 3.0, 5.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    picked_artist = editor._figure.axes[0].lines[1]
    editor._on_generated_pick_event(SimpleNamespace(artist=picked_artist))

    assert editor._selected_figure_object_id == "series-b"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-b"

    escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    app.sendEvent(editor._canvas, escape_event)

    assert escape_event.isAccepted()
    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_escape_key_on_object_list_clears_generated_selection(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-escape-list-deselect.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-escape-list-deselect",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [10.0, 20.0, 30.0], "y": [2.0, 3.0, 5.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(2)

    assert editor._selected_figure_object_id == "series-b"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-b"

    escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    app.sendEvent(editor._object_list, escape_event)

    assert escape_event.isAccepted()
    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_feedback(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-restore.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-restore",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "guide-line"
        status_text = editor._status_label.text()
        assert status_text.startswith(
            tr("EDITOR_SELECTED_STATUS_OBJECT", "Line: Guide")
        )
        assert "endpoint" in status_text.lower()

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "guide-line"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        hover_hint = editor._status_label.text().lower()
        assert "guide" in hover_hint
        assert "endpoint" in hover_hint

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_keeps_hover_on_other_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-other-object.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-other-object",
            objects=[
                {
                    "id": "guide-a",
                    "type": "line",
                    "name": "Guide A",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "guide-b",
                    "type": "line",
                    "name": "Guide B",
                    "x1": 1.0,
                    "y1": 2.0,
                    "x2": 3.0,
                    "y2": 3.0,
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "guide-a"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 2.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "guide b" in hover_hint
        assert "endpoint" in hover_hint
        assert editor._hovered_figure_object_id == "guide-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "guide-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        restored_hint = editor._status_label.text().lower()
        assert "guide b" in restored_hint
        assert "endpoint" in restored_hint

        line_artists = {
            editor._figure_render_adapter.object_id_for_artist(artist): artist
            for artist in editor._figure.axes[0].lines
        }
        assert line_artists["guide-b"].get_path_effects()
        assert line_artists["guide-a"].get_path_effects() == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_selection_to_hovered_other_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-selection.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-selection",
            objects=[
                {
                    "id": "guide-a",
                    "type": "line",
                    "name": "Guide A",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "guide-b",
                    "type": "line",
                    "name": "Guide B",
                    "x1": 1.0,
                    "y1": 2.0,
                    "x2": 3.0,
                    "y2": 3.0,
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "guide-a"
        status_text = editor._status_label.text()
        assert status_text.startswith(
            tr("EDITOR_SELECTED_STATUS_OBJECT", "Line: Guide A")
        )
        assert "endpoint" in status_text.lower()

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 2.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "guide b" in hover_hint
        assert "endpoint" in hover_hint
        assert editor._hovered_figure_object_id == "guide-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "guide-b"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "guide-b"
        assert editor._selected_object_label.text() == "Line: Guide B"
        assert editor._hovered_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        status_text = editor._status_label.text()
        assert status_text.startswith(
            tr("EDITOR_SELECTED_STATUS_OBJECT", "Line: Guide B")
        )
        assert "endpoint" in status_text.lower()

        line_artists = {
            editor._figure_render_adapter.object_id_for_artist(artist): artist
            for artist in editor._figure.axes[0].lines
        }
        assert line_artists["guide-b"].get_path_effects()
        assert line_artists["guide-a"].get_path_effects() == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_from_bar_selection_to_legend(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-bar-to-legend.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-bar-to-legend",
            objects=[
                {
                    "id": "series-bar-a",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar A",
                    "data": {"x": [1.0], "y": [3.0]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                },
                {
                    "id": "series-bar-b",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar B",
                    "data": {"x": [2.0], "y": [1.8]},
                    "style": {"color": "#D55E00", "alpha": 0.9},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        bar_xpix, bar_ypix = axes.transData.transform((1.0, 1.5))
        _send_matplotlib_canvas_click(editor._canvas, bar_xpix, bar_ypix)

        assert editor._selected_figure_object_id == "series-bar-a"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-bar-a"
        _assert_selected_status(editor, "Plot Series: Bar A")

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "legend" in hover_hint
        assert "drag" in hover_hint
        assert editor._hovered_figure_object_id == "legend"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "legend"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
        assert editor._selected_object_label.text() == "Legend"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Legend")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_from_legend_selection_to_bar(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-legend-to-bar.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-legend-to-bar",
            objects=[
                {
                    "id": "series-bar-a",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar A",
                    "data": {"x": [1.0], "y": [3.0]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                },
                {
                    "id": "series-bar-b",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar B",
                    "data": {"x": [2.0], "y": [1.8]},
                    "style": {"color": "#D55E00", "alpha": 0.9},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        legend_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        legend_ypix = float((bbox.y0 + bbox.y1) / 2.0)
        _send_matplotlib_canvas_click(editor._canvas, legend_xpix, legend_ypix)

        assert editor._selected_figure_object_id == "legend"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
        _assert_selected_status(editor, "Legend")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 0.9))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "bar b" in hover_hint
        assert "click" in hover_hint
        assert editor._hovered_figure_object_id == "series-bar-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-bar-b"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-bar-b"
        assert editor._selected_object_label.text() == "Plot Series: Bar B"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Plot Series: Bar B")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_from_heatmap_selection_to_highlight(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-heatmap-to-highlight.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 3.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 4.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 5.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-heatmap-to-highlight",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                },
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                },
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                },
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        heatmap_xpix, heatmap_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_click(editor._canvas, heatmap_xpix, heatmap_ypix)

        assert editor._selected_figure_object_id == "series-heatmap"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-heatmap"
        _assert_selected_status(editor, "Heatmap: Heatmap Pattern")

        hover_xpix, hover_ypix = axes.transData.transform((4.0, 1.8))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "tolerance band" in hover_hint
        assert "click" in hover_hint
        assert editor._hovered_figure_object_id == "tolerance-band"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "tolerance-band"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "tolerance-band"
        assert editor._selected_object_label.text() == "Highlight: Tolerance Band"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Highlight: Tolerance Band")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_from_highlight_selection_to_heatmap(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-highlight-to-heatmap.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 3.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 4.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 5.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-highlight-to-heatmap",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                },
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                },
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                },
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        highlight_xpix, highlight_ypix = axes.transData.transform((4.0, 1.8))
        _send_matplotlib_canvas_click(editor._canvas, highlight_xpix, highlight_ypix)

        assert editor._selected_figure_object_id == "tolerance-band"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "tolerance-band"
        _assert_selected_status(editor, "Highlight: Tolerance Band")

        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "heatmap pattern" in hover_hint
        assert "click" in hover_hint
        assert editor._hovered_figure_object_id == "series-heatmap"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-heatmap"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-heatmap"
        assert editor._selected_object_label.text() == "Heatmap: Heatmap Pattern"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Heatmap: Heatmap Pattern")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_line_series_selection_and_point_context(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-line-series.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-line-series",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "Series A",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "Series B",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [2.0, 4.0, 3.0]},
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        series_a_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        select_a_xpix = float(
            series_a_points[0][0] + 0.75 * (series_a_points[1][0] - series_a_points[0][0])
        )
        select_a_ypix = float(
            series_a_points[0][1] + 0.75 * (series_a_points[1][1] - series_a_points[0][1])
        )
        _send_matplotlib_canvas_click(editor._canvas, select_a_xpix, select_a_ypix)

        assert editor._selected_figure_object_id == "series-a"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-a"
        assert editor._selected_generated_plot_series_object_id == "series-a"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        series_b_points = axes.transData.transform([(1.0, 2.0), (2.0, 4.0)])
        hover_b_xpix = float(
            series_b_points[0][0] + 0.75 * (series_b_points[1][0] - series_b_points[0][0])
        )
        hover_b_ypix = float(
            series_b_points[0][1] + 0.75 * (series_b_points[1][1] - series_b_points[0][1])
        )
        _send_matplotlib_canvas_move(editor._canvas, hover_b_xpix, hover_b_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "series b" in hover_hint
        assert "nearest point" in hover_hint
        assert editor._hovered_figure_object_id == "series-b"

        _send_matplotlib_canvas_click(editor._canvas, hover_b_xpix, hover_b_ypix)

        assert editor._selected_figure_object_id == "series-b"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-b"
        assert editor._selected_generated_plot_series_object_id == "series-b"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 4.0
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Plot Series: Series B")

        line_artists = {
            editor._figure_render_adapter.object_id_for_artist(artist): artist
            for artist in editor._figure.axes[0].lines
        }
        assert line_artists["series-b"].get_path_effects()
        assert line_artists["series-a"].get_path_effects() == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_switches_from_line_series_point_to_line_geometry(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-click-switch-series-to-line.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-click-switch-series-to-line",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Series",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 4.0,
                    "x2": 3.0,
                    "y2": 4.5,
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        series_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        select_series_xpix = float(
            series_points[0][0] + 0.75 * (series_points[1][0] - series_points[0][0])
        )
        select_series_ypix = float(
            series_points[0][1] + 0.75 * (series_points[1][1] - series_points[0][1])
        )
        _send_matplotlib_canvas_click(
            editor._canvas,
            select_series_xpix,
            select_series_ypix,
        )

        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._selected_generated_plot_series_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert editor._annotation_x_label.text() == "X"
        assert editor._annotation_y_label.text() == "Y"
        assert editor._annotation_w_label.text() == ""
        assert editor._annotation_h_label.text() == ""
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        line_xpix, line_ypix = axes.transData.transform((1.0, 4.0))
        _send_matplotlib_canvas_move(editor._canvas, line_xpix, line_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "guide" in hover_hint
        assert "endpoint" in hover_hint
        assert editor._hovered_figure_object_id == "guide-line"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        _send_matplotlib_canvas_click(editor._canvas, line_xpix, line_ypix)

        assert editor._selected_figure_object_id == "guide-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "guide-line"
        assert editor._selected_generated_plot_series_object_id == ""
        assert editor._selected_generated_plot_series_handle_index is None
        assert editor._annotation_x_label.text() == "X1"
        assert editor._annotation_y_label.text() == "Y1"
        assert editor._annotation_w_label.text() == "X2"
        assert editor._annotation_h_label.text() == "Y2"
        assert round(editor._annotation_x_spin.value(), 4) == 1.0
        assert round(editor._annotation_y_spin.value(), 4) == 4.0
        assert round(editor._annotation_w_spin.value(), 4) == 3.0
        assert round(editor._annotation_h_spin.value(), 4) == 4.5
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Line: Guide")

        line_artists = {
            editor._figure_render_adapter.object_id_for_artist(artist): artist
            for artist in editor._figure.axes[0].lines
        }
        assert line_artists["guide-line"].get_path_effects()
        assert line_artists["series-line"].get_path_effects() == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_on_legend(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-legend.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-legend",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(3)

        assert editor._selected_figure_object_id == "legend"
        _assert_selected_status(editor, "Legend")

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "legend"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
        assert "legend" in editor._status_label.text().lower()
        assert "drag" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_on_heatmap(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-heatmap.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-heatmap",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-heatmap"
        _assert_selected_status(editor, "Heatmap: Heatmap Pattern")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-heatmap"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "heatmap" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_on_image_grid(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-image-grid.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        image_a = data_dir / "pattern_a.npy"
        image_b = data_dir / "pattern_b.npy"
        np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
        np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
        metadata_path = data_dir / "grid_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 0,
                    "strain_pct": 0.0,
                    "image_path": str(image_a),
                }
            )
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 1,
                    "strain_pct": 25.0,
                    "image_path": str(image_b),
                }
            )

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-image-grid",
            data_sources=[
                {
                    "id": "grid-metadata",
                    "kind": "csv",
                    "path": str(metadata_path),
                    "role": "plot_data",
                }
            ],
            style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
            objects=[
                {
                    "id": "series-pattern-grid",
                    "type": "plot_series",
                    "chart_kind": "image_grid",
                    "name": "2D WAXS Pattern Grid",
                    "data_ref": "grid-metadata",
                    "row_column": "grid_row",
                    "column_column": "grid_col",
                    "image_path_column": "image_path",
                    "label_column": "strain_pct",
                    "style": {"colormap": "inferno"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-pattern-grid"
        _assert_selected_status(editor, "Image Grid: 2D WAXS Pattern Grid")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-pattern-grid"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "image grid" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_keeps_hover_on_other_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-other-object.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-list-escape-hover-other-object",
            objects=[
                {
                    "id": "guide-a",
                    "type": "line",
                    "name": "Guide A",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "guide-b",
                    "type": "line",
                    "name": "Guide B",
                    "x1": 1.0,
                    "y1": 2.0,
                    "x2": 3.0,
                    "y2": 3.0,
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "guide-a"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 2.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "guide b" in hover_hint
        assert "endpoint" in hover_hint
        assert editor._hovered_figure_object_id == "guide-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "guide-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        restored_hint = editor._status_label.text().lower()
        assert "guide b" in restored_hint
        assert "endpoint" in restored_hint

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_on_highlight(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-highlight.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated-real-escape-hover-highlight",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "tolerance-band"
        _assert_selected_status(editor, "Highlight: Tolerance Band")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 1.8))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "tolerance-band"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "tolerance band" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_restores_hover_on_heatmap(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-heatmap.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-list-escape-hover-heatmap",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-heatmap"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-heatmap"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "heatmap" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_restores_hover_on_legend(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-legend.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-list-escape-hover-legend",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(3)

        assert editor._selected_figure_object_id == "legend"

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "legend"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
        assert "legend" in editor._status_label.text().lower()
        assert "drag" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_restores_hover_on_image_grid(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-image-grid.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        image_a = data_dir / "pattern_a.npy"
        image_b = data_dir / "pattern_b.npy"
        np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
        np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
        metadata_path = data_dir / "grid_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 0,
                    "strain_pct": 0.0,
                    "image_path": str(image_a),
                }
            )
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 1,
                    "strain_pct": 25.0,
                    "image_path": str(image_b),
                }
            )

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-list-escape-hover-image-grid",
            data_sources=[
                {
                    "id": "grid-metadata",
                    "kind": "csv",
                    "path": str(metadata_path),
                    "role": "plot_data",
                }
            ],
            style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
            objects=[
                {
                    "id": "series-pattern-grid",
                    "type": "plot_series",
                    "chart_kind": "image_grid",
                    "name": "2D WAXS Pattern Grid",
                    "data_ref": "grid-metadata",
                    "row_column": "grid_row",
                    "column_column": "grid_col",
                    "image_path_column": "image_path",
                    "label_column": "strain_pct",
                    "style": {"colormap": "inferno"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-pattern-grid"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-pattern-grid"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "image grid" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_restores_hover_on_highlight(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-highlight.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated-list-escape-hover-highlight",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "tolerance-band"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 1.8))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "tolerance-band"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "tolerance band" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_on_bar(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-bar.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-bar",
            objects=[
                {
                    "id": "series-bar",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar Series",
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-bar"
        _assert_selected_status(editor, "Plot Series: Bar Series")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-bar"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "bar series" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_key_clears_selection_and_restores_hover_on_scatter(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-escape-hover-scatter.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-escape-hover-scatter",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-scatter"
        _assert_selected_status(editor, "Plot Series: Scatter")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-scatter"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert "scatter" in editor._status_label.text().lower()
        assert "drag" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_restores_hover_on_bar(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-bar.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-list-escape-hover-bar",
            objects=[
                {
                    "id": "series-bar",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar Series",
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-bar"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-bar"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor
        assert "bar series" in editor._status_label.text().lower()
        assert "click" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_object_list_escape_key_clears_selection_and_restores_hover_on_scatter(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-list-escape-hover-scatter.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-list-escape-hover-scatter",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-scatter"

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)
        assert editor._hovered_figure_object_id == ""

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._object_list, escape_event)

        assert escape_event.isAccepted()
        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == "series-scatter"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert "scatter" in editor._status_label.text().lower()
        assert "drag" in editor._status_label.text().lower()

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_generated_selection_status_restores_after_hovering_other_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-selection-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-selection-status",
            objects=[
                {
                    "id": "guide-a",
                    "type": "line",
                    "name": "Guide A",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "guide-b",
                    "type": "line",
                    "name": "Guide B",
                    "x1": 1.0,
                    "y1": 2.0,
                    "x2": 3.0,
                    "y2": 3.0,
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        picked_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "guide-a"
        )
        editor._on_generated_pick_event(SimpleNamespace(artist=picked_artist))

        selected_hint = editor._status_label.text().lower()
        assert "selected" in selected_hint
        assert "guide a" in selected_hint

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 2.0))
        hover_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            hover_xpix,
            hover_ypix,
        )
        hover_event.inaxes = axes
        editor._on_generated_mouse_move(hover_event)

        hover_hint = editor._status_label.text().lower()
        assert "endpoint" in hover_hint
        assert "guide b" in hover_hint

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        away_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            away_xpix,
            away_ypix,
        )
        away_event.inaxes = axes
        editor._on_generated_mouse_move(away_event)

        restored_hint = editor._status_label.text().lower()
        assert "selected" in restored_hint
        assert "guide a" in restored_hint

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_canvas_pick_prefers_frontmost_generated_object_when_series_overlap(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_overlap.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-overlap",
        objects=[
            {
                "id": "series-back",
                "type": "plot_series",
                "name": "Back",
                "z_index": 0,
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                "style": {"line_width": 6.0},
            },
            {
                "id": "series-front",
                "type": "plot_series",
                "name": "Front",
                "z_index": 1,
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                "style": {"line_width": 6.0},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    back_artist = editor._figure.axes[0].lines[0]
    xpix, ypix = editor._figure.axes[0].transData.transform((20.0, 4.0))
    mouseevent = MouseEvent("button_press_event", editor._canvas, xpix, ypix)
    mouseevent.inaxes = editor._figure.axes[0]

    editor._on_generated_pick_event(
        SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
    )

    assert editor._selected_figure_object_id == "series-front"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-front"
    assert editor._annotation_text_edit.text() == "Front"

    editor._on_generated_pick_event(
        SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
    )

    assert editor._selected_figure_object_id == "series-back"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-back"
    assert editor._annotation_text_edit.text() == "Back"

    editor._on_generated_pick_event(
        SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
    )

    assert editor._selected_figure_object_id == "series-front"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-front"
    assert editor._annotation_text_edit.text() == "Front"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_overlap_pick_status_invites_click_again_to_cycle(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-overlap-status.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-overlap-status",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "name": "Back",
                    "z_index": 0,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "name": "Front",
                    "z_index": 1,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        back_artist = editor._figure.axes[0].lines[0]
        xpix, ypix = editor._figure.axes[0].transData.transform((20.0, 4.0))
        mouseevent = MouseEvent("button_press_event", editor._canvas, xpix, ypix)
        mouseevent.inaxes = editor._figure.axes[0]

        editor._on_generated_pick_event(
            SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
        )

        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "front" in status_text
        assert "click again" in status_text

        editor._on_generated_pick_event(
            SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
        )

        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "back" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_overlap_cycle_hint_does_not_leak_into_next_figure_selection(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        overlap_path = tmp_path / "figures" / "generated-overlap-hint-reset.png"
        overlap_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(overlap_path))

        save_generated_figure_document(
            str(overlap_path),
            technique="waxs",
            figure_id="generated-overlap-hint-reset",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "name": "Back",
                    "z_index": 0,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "name": "Front",
                    "z_index": 1,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
            ],
        )

        single_path = tmp_path / "figures" / "generated-single-hint-reset.png"
        pixmap_single = QPixmap(80, 40)
        pixmap_single.fill(QColor("white"))
        assert pixmap_single.save(str(single_path))

        save_generated_figure_document(
            str(single_path),
            technique="waxs",
            figure_id="generated-single-hint-reset",
            objects=[
                {
                    "id": "series-single",
                    "type": "plot_series",
                    "name": "Single",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(overlap_path))

        back_artist = editor._figure.axes[0].lines[0]
        xpix, ypix = editor._figure.axes[0].transData.transform((20.0, 4.0))
        mouseevent = MouseEvent("button_press_event", editor._canvas, xpix, ypix)
        mouseevent.inaxes = editor._figure.axes[0]
        editor._on_generated_pick_event(
            SimpleNamespace(artist=back_artist, mouseevent=mouseevent)
        )
        assert "click again" in editor._status_label.text().lower()

        editor.set_source_figure(str(single_path))
        picked_artist = editor._figure.axes[0].lines[0]
        editor._on_generated_pick_event(SimpleNamespace(artist=picked_artist))

        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "single" in status_text
        assert "click again" not in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_keeps_overlap_cycle_hint_visible(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-overlap-real-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-overlap-real-click",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "name": "Back",
                    "z_index": 0,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "name": "Front",
                    "z_index": 1,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((20.0, 4.0))
        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "series-front"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "front" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_second_click_cycles_overlapping_objects(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-overlap-real-cycle.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-overlap-real-cycle",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "name": "Back",
                    "z_index": 0,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "name": "Front",
                    "z_index": 1,
                    "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                    "style": {"line_width": 6.0},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((20.0, 4.0))

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)
        assert editor._selected_figure_object_id == "series-front"

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "series-back"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "back" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_line_series_body_keeps_overlap_cycle_hint_visible(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-overlap-real-near-line-body.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-overlap-real-near-line-body",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "name": "Back",
                    "z_index": 0,
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "name": "Front",
                    "z_index": 1,
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 6.0)
        ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 6.0)

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "series-front"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "front" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_direct_press_prefers_frontmost_overlapping_series_over_selected_back_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-overlap-direct-press.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-overlap-direct-press",
        objects=[
            {
                "id": "series-back",
                "type": "plot_series",
                "name": "Back",
                "z_index": 0,
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                "style": {"line_width": 6.0},
            },
            {
                "id": "series-front",
                "type": "plot_series",
                "name": "Front",
                "z_index": 1,
                "data": {"x": [10.0, 20.0, 30.0], "y": [1.0, 4.0, 2.0]},
                "style": {"line_width": 6.0},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)
    assert editor._selected_figure_object_id == "series-back"

    axes = editor._figure.axes[0]
    start_points = axes.transData.transform([(10.0, 1.0), (20.0, 4.0)])
    press_xpix = float(start_points[0][0] + 0.75 * (start_points[1][0] - start_points[0][0]))
    press_ypix = float(start_points[0][1] + 0.75 * (start_points[1][1] - start_points[0][1]))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        press_xpix,
        press_ypix,
        button=1,
    )
    press_event.inaxes = axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = axes.transData.transform((20.35, 3.45))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    assert document["objects"][0]["data"]["x"] == [10.0, 20.0, 30.0]
    assert document["objects"][0]["data"]["y"] == [1.0, 4.0, 2.0]
    assert document["objects"][1]["data"]["x"] == [10.0, 20.35, 30.0]
    assert document["objects"][1]["data"]["y"] == [1.0, 3.45, 2.0]
    assert editor._selected_figure_object_id == "series-front"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-front"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_opens_generated_image_grid_as_live_canvas(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_grid.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    image_a = data_dir / "pattern_a.npy"
    image_b = data_dir / "pattern_b.npy"
    np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
    np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
    metadata_path = data_dir / "grid_metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 0,
                "strain_pct": 0.0,
                "image_path": str(image_a),
            }
        )
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 1,
                "strain_pct": 25.0,
                "image_path": str(image_b),
            }
        )

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated_grid",
        data_sources=[
            {
                "id": "grid-metadata",
                "kind": "csv",
                "path": str(metadata_path),
                "role": "plot_data",
            }
        ],
        style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
        objects=[
            {
                "id": "series-pattern-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "2D WAXS Pattern Grid",
                "data_ref": "grid-metadata",
                "row_column": "grid_row",
                "column_column": "grid_col",
                "image_path_column": "image_path",
                "label_column": "strain_pct",
                "style": {"colormap": "inferno"},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._canvas.isHidden() is False
    assert editor._annotation_canvas.isHidden() is True
    assert len(editor._figure.axes) == 2
    assert [len(ax.images) for ax in editor._figure.axes] == [1, 1]
    assert [ax.get_title() for ax in editor._figure.axes] == ["0", "25"]
    assert editor._object_list.item(1).data(Qt.UserRole) == "series-pattern-grid"
    assert editor._object_list.item(1).text() == "Image Grid: 2D WAXS Pattern Grid"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_canvas_pick_selects_generated_image_grid_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_grid.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    image_a = data_dir / "pattern_a.npy"
    image_b = data_dir / "pattern_b.npy"
    np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
    np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
    metadata_path = data_dir / "grid_metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 0,
                "strain_pct": 0.0,
                "image_path": str(image_a),
            }
        )
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 1,
                "strain_pct": 25.0,
                "image_path": str(image_b),
            }
        )

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated_grid",
        data_sources=[
            {
                "id": "grid-metadata",
                "kind": "csv",
                "path": str(metadata_path),
                "role": "plot_data",
            }
        ],
        style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
        objects=[
            {
                "id": "series-pattern-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "2D WAXS Pattern Grid",
                "data_ref": "grid-metadata",
                "row_column": "grid_row",
                "column_column": "grid_col",
                "image_path_column": "image_path",
                "label_column": "strain_pct",
                "style": {"colormap": "inferno"},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    picked_artist = editor._figure.axes[0].images[0]
    editor._on_generated_pick_event(SimpleNamespace(artist=picked_artist))

    assert editor._selected_figure_object_id == "series-pattern-grid"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-pattern-grid"
    assert editor._annotation_text_edit.text() == "2D WAXS Pattern Grid"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_click_selects_generated_image_grid_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_grid_real_click.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    image_a = data_dir / "pattern_a.npy"
    image_b = data_dir / "pattern_b.npy"
    np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
    np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
    metadata_path = data_dir / "grid_metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 0,
                "strain_pct": 0.0,
                "image_path": str(image_a),
            }
        )
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 1,
                "strain_pct": 25.0,
                "image_path": str(image_b),
            }
        )

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated_grid_real_click",
        data_sources=[
            {
                "id": "grid-metadata",
                "kind": "csv",
                "path": str(metadata_path),
                "role": "plot_data",
            }
        ],
        style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
        objects=[
            {
                "id": "series-pattern-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "2D WAXS Pattern Grid",
                "data_ref": "grid-metadata",
                "row_column": "grid_row",
                "column_column": "grid_col",
                "image_path_column": "image_path",
                "label_column": "strain_pct",
                "style": {"colormap": "inferno"},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    xpix, ypix = axes.transData.transform((0.5, 0.5))
    _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

    assert editor._selected_figure_object_id == "series-pattern-grid"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-pattern-grid"
    assert editor._annotation_text_edit.text() == "2D WAXS Pattern Grid"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_click_selects_generated_heatmap_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_heatmap_real_click.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    matrix_path = data_dir / "heatmap.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
        writer.writeheader()
        writer.writerow({"x": 0, "y": 0, "value": 1.0})
        writer.writerow({"x": 1, "y": 0, "value": 2.0})
        writer.writerow({"x": 0, "y": 1, "value": 3.0})
        writer.writerow({"x": 1, "y": 1, "value": 4.0})

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated_heatmap_real_click",
        data_sources=[
            {
                "id": "heatmap-data",
                "kind": "csv",
                "path": str(matrix_path),
                "role": "plot_data",
            }
        ],
        objects=[
            {
                "id": "series-heatmap",
                "type": "plot_series",
                "chart_kind": "heatmap",
                "name": "Heatmap Pattern",
                "data_ref": "heatmap-data",
                "x_column": "x",
                "y_column": "y",
                "value_column": "value",
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    xpix, ypix = axes.transData.transform((0.5, 0.5))
    _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

    assert editor._selected_figure_object_id == "series-heatmap"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-heatmap"
    assert editor._annotation_text_edit.text() == "Heatmap Pattern"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_hover_updates_status_hint_for_generated_heatmap_selection(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_heatmap_real_hover.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_heatmap_real_hover",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "heatmap pattern" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-heatmap"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_heatmap_edge_hover_and_click_selects_heatmap(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_heatmap_real_edge_hover.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_heatmap_real_edge_hover",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((1.5, 0.5))
        hover_xpix = edge_xpix - 2.0
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, edge_ypix)

        hint = editor._status_label.text().lower()
        assert "heatmap pattern" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-heatmap"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, edge_ypix)

        assert editor._selected_figure_object_id == "series-heatmap"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-heatmap"
        _assert_selected_status(editor, "Heatmap: Heatmap Pattern")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_heatmap_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_heatmap_blank_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_heatmap_blank_real_click",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        heatmap_xpix, heatmap_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_click(editor._canvas, heatmap_xpix, heatmap_ypix)

        assert editor._selected_figure_object_id == "series-heatmap"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-heatmap"
        _assert_selected_status(editor, "Heatmap: Heatmap Pattern")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_outside_heatmap_edge_does_not_select_heatmap(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_heatmap_far_edge_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_heatmap_far_edge_real_click",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "series-heatmap",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Heatmap Pattern",
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        rightmost_axes = editor._figure.axes[-1]
        patch_bbox = rightmost_axes.patch.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float(patch_bbox.x1 + 14.0)
        hover_ypix = float((patch_bbox.y0 + patch_bbox.y1) / 2.0)
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
        assert editor._hovered_figure_object_id == ""

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_and_click_select_generated_highlight_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_highlight_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated_highlight_real_click",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 1.8))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "tolerance band" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "tolerance-band"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "tolerance-band"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "tolerance-band"
        _assert_selected_status(editor, "Highlight: Tolerance Band")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_highlight_edge_hover_and_click_selects_highlight(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_highlight_real_edge_hover.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated_highlight_real_edge_hover",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((3.0, 1.6))
        hover_xpix = edge_xpix + 5.0
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, edge_ypix)

        hint = editor._status_label.text().lower()
        assert "tolerance band" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "tolerance-band"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, edge_ypix)

        assert editor._selected_figure_object_id == "tolerance-band"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "tolerance-band"
        _assert_selected_status(editor, "Highlight: Tolerance Band")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_outside_highlight_edge_does_not_select_highlight(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_highlight_far_edge_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated_highlight_far_edge_real_click",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((3.0, 1.6))
        hover_xpix = edge_xpix + 14.0
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, edge_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
        assert editor._hovered_figure_object_id == ""

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, edge_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_highlight_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_highlight_blank_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated_highlight_blank_real_click",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "tolerance-band",
                    "type": "highlight",
                    "name": "Tolerance Band",
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        highlight_xpix, highlight_ypix = axes.transData.transform((2.0, 1.8))
        _send_matplotlib_canvas_click(editor._canvas, highlight_xpix, highlight_ypix)

        assert editor._selected_figure_object_id == "tolerance-band"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "tolerance-band"
        _assert_selected_status(editor, "Highlight: Tolerance Band")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_keeps_overlap_cycle_hint_visible_for_highlights(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-highlight-overlap-real-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated-highlight-overlap-real-click",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "band-back",
                    "type": "highlight",
                    "name": "Back Band",
                    "z_index": 0,
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                },
                {
                    "id": "band-front",
                    "type": "highlight",
                    "name": "Front Band",
                    "z_index": 1,
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.25, "color": "#CC6677"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((2.0, 1.8))
        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "band-front"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "front band" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_second_click_cycles_overlapping_highlights(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-highlight-overlap-real-cycle.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        band_path = data_dir / "highlight_band.csv"
        with band_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "lower", "upper"])
            writer.writeheader()
            writer.writerow({"x": 1.0, "lower": 1.0, "upper": 2.0})
            writer.writerow({"x": 2.0, "lower": 1.2, "upper": 2.3})
            writer.writerow({"x": 3.0, "lower": 1.1, "upper": 2.1})

        save_generated_figure_document(
            str(figure_path),
            technique="nmr",
            figure_id="generated-highlight-overlap-real-cycle",
            data_sources=[
                {
                    "id": "highlight-band",
                    "kind": "csv",
                    "path": str(band_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "band-back",
                    "type": "highlight",
                    "name": "Back Band",
                    "z_index": 0,
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.15, "color": "#88CC88"},
                },
                {
                    "id": "band-front",
                    "type": "highlight",
                    "name": "Front Band",
                    "z_index": 1,
                    "data_ref": "highlight-band",
                    "x_column": "x",
                    "lower_y_column": "lower",
                    "upper_y_column": "upper",
                    "style": {"alpha": 0.25, "color": "#CC6677"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((2.0, 1.8))

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)
        assert editor._selected_figure_object_id == "band-front"

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "band-back"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "back band" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_second_click_cycles_overlapping_bar_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-bar-overlap-real-cycle.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-bar-overlap-real-cycle",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Back Bar",
                    "z_index": 0,
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.6},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Front Bar",
                    "z_index": 1,
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#D55E00", "alpha": 0.6},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((1.0, 1.5))

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)
        assert editor._selected_figure_object_id == "series-front"

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "series-back"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "back bar" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_keeps_overlap_cycle_hint_visible_for_scatter_points(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-overlap-real-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-overlap-real-click",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Back Scatter",
                    "z_index": 0,
                    "data": {"x": [2.0], "y": [3.0]},
                    "style": {"marker_size": 10.0, "color": "#0072B2"},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Front Scatter",
                    "z_index": 1,
                    "data": {"x": [2.0], "y": [3.0]},
                    "style": {"marker_size": 10.0, "color": "#D55E00"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "series-front"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "front scatter" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_second_click_cycles_overlapping_scatter_points(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-overlap-real-cycle.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-overlap-real-cycle",
            objects=[
                {
                    "id": "series-back",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Back Scatter",
                    "z_index": 0,
                    "data": {"x": [2.0], "y": [3.0]},
                    "style": {"marker_size": 10.0, "color": "#0072B2"},
                },
                {
                    "id": "series-front",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Front Scatter",
                    "z_index": 1,
                    "data": {"x": [2.0], "y": [3.0]},
                    "style": {"marker_size": 10.0, "color": "#D55E00"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((2.0, 3.0))

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)
        assert editor._selected_figure_object_id == "series-front"

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "series-back"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "back scatter" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_second_click_cycles_overlapping_heatmaps(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-heatmap-overlap-real-cycle.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        matrix_path = data_dir / "heatmap.csv"
        with matrix_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["x", "y", "value"])
            writer.writeheader()
            writer.writerow({"x": 0, "y": 0, "value": 1.0})
            writer.writerow({"x": 1, "y": 0, "value": 2.0})
            writer.writerow({"x": 0, "y": 1, "value": 3.0})
            writer.writerow({"x": 1, "y": 1, "value": 4.0})

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-heatmap-overlap-real-cycle",
            data_sources=[
                {
                    "id": "heatmap-data",
                    "kind": "csv",
                    "path": str(matrix_path),
                    "role": "plot_data",
                }
            ],
            objects=[
                {
                    "id": "heatmap-back",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Back Heatmap",
                    "z_index": 0,
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                    "style": {"colormap": "viridis"},
                },
                {
                    "id": "heatmap-front",
                    "type": "plot_series",
                    "chart_kind": "heatmap",
                    "name": "Front Heatmap",
                    "z_index": 1,
                    "data_ref": "heatmap-data",
                    "x_column": "x",
                    "y_column": "y",
                    "value_column": "value",
                    "style": {"colormap": "magma"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        xpix, ypix = axes.transData.transform((0.5, 0.5))

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)
        assert editor._selected_figure_object_id == "heatmap-front"

        _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)

        assert editor._selected_figure_object_id == "heatmap-back"
        assert editor._generated_handle_drag_state is None
        status_text = editor._status_label.text().lower()
        assert "selected" in status_text
        assert "back heatmap" in status_text
        assert "click again" in status_text

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_and_click_select_generated_bar_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_bar_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_bar_real_click",
            objects=[
                {
                    "id": "series-bar",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar Series",
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "bar series" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-bar"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-bar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-bar"
        _assert_selected_status(editor, "Plot Series: Bar Series")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_bar_edge_hover_and_click_still_selects_bar_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_bar_edge_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_bar_edge_real_click",
            objects=[
                {
                    "id": "series-bar",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar Series",
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((1.4, 1.5))
        hover_xpix = edge_xpix + 5.0
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, edge_ypix)

        hint = editor._status_label.text().lower()
        assert "bar series" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-bar"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, edge_ypix)

        assert editor._selected_figure_object_id == "series-bar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-bar"
        _assert_selected_status(editor, "Plot Series: Bar Series")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_outside_bar_edge_does_not_select_bar_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_bar_far_edge_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_bar_far_edge_real_click",
            objects=[
                {
                    "id": "series-bar",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar Series",
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((1.4, 1.5))
        hover_xpix = edge_xpix + 14.0
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, edge_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
        assert editor._hovered_figure_object_id == ""

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, edge_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_bar_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_bar_blank_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_bar_blank_real_click",
            objects=[
                {
                    "id": "series-bar",
                    "type": "plot_series",
                    "chart_kind": "bar",
                    "name": "Bar Series",
                    "data": {"x": [1.0, 2.0], "y": [3.0, 1.5]},
                    "style": {"color": "#0072B2", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        bar_xpix, bar_ypix = axes.transData.transform((1.0, 1.5))
        _send_matplotlib_canvas_click(editor._canvas, bar_xpix, bar_ypix)

        assert editor._selected_figure_object_id == "series-bar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-bar"
        _assert_selected_status(editor, "Plot Series: Bar Series")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_and_click_select_generated_barh_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_barh_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_barh_real_click",
            objects=[
                {
                    "id": "series-barh",
                    "type": "plot_series",
                    "chart_kind": "barh",
                    "name": "BarH Series",
                    "data": {"x": [3.0, 1.5], "y": [1.0, 2.0]},
                    "style": {"color": "#009E73", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.5, 1.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "barh series" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-barh"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-barh"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-barh"
        _assert_selected_status(editor, "Plot Series: BarH Series")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_barh_edge_hover_and_click_still_selects_barh_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_barh_edge_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_barh_edge_real_click",
            objects=[
                {
                    "id": "series-barh",
                    "type": "plot_series",
                    "chart_kind": "barh",
                    "name": "BarH Series",
                    "data": {"x": [3.0, 1.5], "y": [1.0, 2.0]},
                    "style": {"color": "#009E73", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((1.5, 1.4))
        hover_ypix = edge_ypix + 5.0
        _send_matplotlib_canvas_move(editor._canvas, edge_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "barh series" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-barh"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, edge_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-barh"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-barh"
        _assert_selected_status(editor, "Plot Series: BarH Series")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_barh_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_barh_blank_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_barh_blank_real_click",
            objects=[
                {
                    "id": "series-barh",
                    "type": "plot_series",
                    "chart_kind": "barh",
                    "name": "BarH Series",
                    "data": {"x": [3.0, 1.5], "y": [1.0, 2.0]},
                    "style": {"color": "#009E73", "alpha": 0.9},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        bar_xpix, bar_ypix = axes.transData.transform((1.5, 1.0))
        _send_matplotlib_canvas_click(editor._canvas, bar_xpix, bar_ypix)

        assert editor._selected_figure_object_id == "series-barh"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-barh"
        _assert_selected_status(editor, "Plot Series: BarH Series")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_image_grid_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_grid_blank_real_click.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    image_a = data_dir / "pattern_a.npy"
    image_b = data_dir / "pattern_b.npy"
    np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
    np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
    metadata_path = data_dir / "grid_metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 0,
                "strain_pct": 0.0,
                "image_path": str(image_a),
            }
        )
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 1,
                "strain_pct": 25.0,
                "image_path": str(image_b),
            }
        )

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated_grid_blank_real_click",
        data_sources=[
            {
                "id": "grid-metadata",
                "kind": "csv",
                "path": str(metadata_path),
                "role": "plot_data",
            }
        ],
        style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
        objects=[
            {
                "id": "series-pattern-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "2D WAXS Pattern Grid",
                "data_ref": "grid-metadata",
                "row_column": "grid_row",
                "column_column": "grid_col",
                "image_path_column": "image_path",
                "label_column": "strain_pct",
                "style": {"colormap": "inferno"},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    xpix, ypix = axes.transData.transform((0.5, 0.5))
    _send_matplotlib_canvas_click(editor._canvas, xpix, ypix)
    assert editor._selected_figure_object_id == "series-pattern-grid"

    _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_far_outside_image_grid_edge_does_not_select_grid(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated_grid_far_edge_real_click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        image_a = data_dir / "pattern_a.npy"
        image_b = data_dir / "pattern_b.npy"
        np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
        np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
        metadata_path = data_dir / "grid_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 0,
                    "strain_pct": 0.0,
                    "image_path": str(image_a),
                }
            )
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 1,
                    "strain_pct": 25.0,
                    "image_path": str(image_b),
                }
            )

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated_grid_far_edge_real_click",
            data_sources=[
                {
                    "id": "grid-metadata",
                    "kind": "csv",
                    "path": str(metadata_path),
                    "role": "plot_data",
                }
            ],
            style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
            objects=[
                {
                    "id": "series-pattern-grid",
                    "type": "plot_series",
                    "chart_kind": "image_grid",
                    "name": "2D WAXS Pattern Grid",
                    "data_ref": "grid-metadata",
                    "row_column": "grid_row",
                    "column_column": "grid_col",
                    "image_path_column": "image_path",
                    "label_column": "strain_pct",
                    "style": {"colormap": "inferno"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        rightmost_axes = editor._figure.axes[-1]
        patch_bbox = rightmost_axes.patch.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float(patch_bbox.x1 + 14.0)
        hover_ypix = float((patch_bbox.y0 + patch_bbox.y1) / 2.0)
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
        assert editor._hovered_figure_object_id == ""

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_populates_controls_from_generated_document_style(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated",
        style={
            "title": "Original SAXS",
            "xlabel": "q",
            "ylabel": "I(q)",
            "grid_on": False,
            "grid_alpha": 0.6,
            "bg_color": "#F0F0F0",
        },
        objects=[
            {
                "id": "series-intensity",
                "type": "plot_series",
                "name": "Intensity",
                "data": {"x": [0.1, 0.2, 0.3], "y": [10.0, 8.0, 6.0]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._title_edit.text() == "Original SAXS"
    assert editor._xlabel_edit.text() == "q"
    assert editor._ylabel_edit.text() == "I(q)"
    assert editor._grid_cb.isChecked() is False
    assert editor._grid_sl.value() == 6
    assert editor._bg_color == "#F0F0F0"
    assert editor._figure.axes[0].get_title() == "Original SAXS"
    assert any(line.get_visible() for line in editor._figure.axes[0].get_xgridlines()) is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_save_preserves_generated_figure_document(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="dsc",
        figure_id="generated",
        style={"xlabel": "Temperature", "ylabel": "Heat Flow"},
        objects=[
            {
                "id": "series-heat-flow",
                "type": "plot_series",
                "name": "Heat Flow",
                "data": {"x": [20.0, 40.0, 60.0], "y": [0.1, 0.4, 0.2]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._title_edit.setText("Edited DSC")
    editor._xlabel_edit.setText("Edited T")
    editor.save_to_target()

    document = load_figure_document(str(figure_path))
    assert document["mode"] == "object"
    assert document["objects"][0]["id"] == "series-heat-flow"
    assert document["style"]["title"] == "Edited DSC"
    assert document["style"]["xlabel"] == "Edited T"
    assert document["style"]["ylabel"] == "Heat Flow"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_save_can_clear_generated_document_labels(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="ir",
        figure_id="generated",
        style={"title": "Old Title", "xlabel": "Old X", "ylabel": "Old Y"},
        objects=[
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "name": "Spectrum",
                "data": {"x": [1000.0, 1100.0], "y": [0.2, 0.5]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._title_edit.setText("")
    editor._xlabel_edit.setText("")
    editor._ylabel_edit.setText("New Y")
    editor.save_to_target()

    document = load_figure_document(str(figure_path))
    assert document["style"]["title"] == ""
    assert document["style"]["xlabel"] == ""
    assert document["style"]["ylabel"] == "New Y"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_applies_style_to_selected_generated_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-measured",
                "type": "plot_series",
                "name": "Measured",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"color": "#0072B2", "line_width": 1.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_color_edit.isEnabled() is True
    assert editor._annotation_line_width_spin.isEnabled() is True
    assert editor._btn_annotation_apply_style.isEnabled() is True

    editor._annotation_color_edit.setText("#D55E00")
    editor._annotation_line_width_spin.setValue(3.5)
    editor._annotation_line_style_combo.setCurrentText("Dashed")
    editor._annotation_marker_combo.setCurrentText("Circle")
    editor._annotation_marker_size_spin.setValue(9.0)
    editor._btn_annotation_apply_style.click()

    document = load_figure_document(str(figure_path))
    assert document["objects"][0]["style"]["color"] == "#D55E00"
    assert document["objects"][0]["style"]["line_width"] == 3.5
    assert document["objects"][0]["style"]["line_style"] == "--"
    assert document["objects"][0]["style"]["marker"] == "o"
    assert document["objects"][0]["style"]["marker_size"] == 9.0
    assert editor._figure.axes[0].lines[0].get_color() == "#D55E00"
    assert editor._figure.axes[0].lines[0].get_linewidth() == 3.5
    assert editor._figure.axes[0].lines[0].get_linestyle() == "--"
    assert editor._figure.axes[0].lines[0].get_marker() == "o"
    assert editor._figure.axes[0].lines[0].get_markersize() == 9.0

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_renames_selected_generated_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="nmr",
        figure_id="generated",
        objects=[
            {
                "id": "series-spectrum",
                "type": "plot_series",
                "name": "Spectrum",
                "data": {"x": [1.0, 2.0, 3.0], "y": [0.2, 0.6, 0.4]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_text_edit.text() == "Spectrum"
    assert editor._btn_annotation_update_text.isEnabled() is True

    editor._annotation_text_edit.setText("Edited Spectrum")
    editor._btn_annotation_update_text.click()

    document = load_figure_document(str(figure_path))
    assert document["objects"][0]["name"] == "Edited Spectrum"
    assert editor._object_list.item(1).text() == "Plot Series: Edited Spectrum"
    assert editor._figure.axes[0].get_legend().get_texts()[0].get_text() == "Edited Spectrum"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_toggles_generated_object_visibility_from_object_list(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0, 3.0], "y": [3.0, 2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert len(editor._figure.axes[0].lines) == 2
    item = editor._object_list.item(2)
    assert item.data(Qt.UserRole) == "series-b"
    assert item.checkState() == Qt.Checked

    item.setCheckState(Qt.Unchecked)
    app.processEvents()

    document = load_figure_document(str(figure_path))
    assert document["objects"][1]["visible"] is False
    assert len(editor._figure.axes[0].lines) == 1
    assert editor._figure.axes[0].lines[0].get_label() == "A"
    assert editor._object_list.item(2).checkState() == Qt.Unchecked

    item = editor._object_list.item(2)
    item.setCheckState(Qt.Checked)
    app.processEvents()

    document = load_figure_document(str(figure_path))
    assert document["objects"][1]["visible"] is True
    assert len(editor._figure.axes[0].lines) == 2

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_can_hide_all_generated_objects(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="dsc",
        figure_id="generated",
        style={"xlabel": "T", "ylabel": "HF"},
        objects=[
            {
                "id": "series-only",
                "type": "plot_series",
                "name": "Only",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    assert len(editor._figure.axes[0].lines) == 1

    editor._object_list.item(1).setCheckState(Qt.Unchecked)
    app.processEvents()

    assert editor._figure.axes
    assert len(editor._figure.axes[0].lines) == 0
    assert editor._figure.axes[0].get_xlabel() == "T"
    assert editor._figure.axes[0].get_ylabel() == "HF"
    assert load_figure_document(str(figure_path))["objects"][0]["visible"] is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_hides_legend_when_no_generated_series_are_visible(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-only",
                "type": "plot_series",
                "name": "Only",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    assert editor._figure.axes[0].get_legend() is not None

    editor._object_list.item(1).setCheckState(Qt.Unchecked)
    app.processEvents()

    assert len(editor._figure.axes[0].lines) == 0
    assert editor._figure.axes[0].get_legend() is None

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_reorder_buttons_ignore_legend_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-only",
                "type": "plot_series",
                "name": "Only",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._object_list.item(2).data(Qt.UserRole) == "legend"
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_reorders_generated_objects_with_layer_buttons(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._btn_annotation_front.isEnabled() is True
    assert editor._btn_annotation_back.isEnabled() is True

    editor._btn_annotation_front.click()
    document = load_figure_document(str(figure_path))
    assert [obj["id"] for obj in document["objects"]] == ["series-b", "series-a", "legend"]
    assert [line.get_label() for line in editor._figure.axes[0].lines] == ["B", "A"]
    assert editor._object_list.item(2).data(Qt.UserRole) == "series-a"

    editor._btn_annotation_back.click()
    document = load_figure_document(str(figure_path))
    assert [obj["id"] for obj in document["objects"]] == ["series-a", "series-b", "legend"]
    assert [line.get_label() for line in editor._figure.axes[0].lines] == ["A", "B"]
    assert editor._object_list.item(1).data(Qt.UserRole) == "series-a"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_soft_deletes_selected_generated_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="ir",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0, 3.0], "y": [3.0, 2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._btn_annotation_delete.isEnabled() is True
    editor._btn_annotation_delete.click()

    document = load_figure_document(str(figure_path))
    assert document["objects"][0]["id"] == "series-a"
    assert document["objects"][0]["deleted"] is True
    assert "deleted" not in document["objects"][1]
    assert editor._object_list.count() == 3
    assert editor._object_list.item(1).data(Qt.UserRole) == "series-b"
    assert [line.get_label() for line in editor._figure.axes[0].lines] == ["B"]

    reopened = ChartEditor()
    reopened.set_source_figure(str(figure_path))
    assert reopened._object_list.count() == 3
    assert reopened._object_list.item(1).data(Qt.UserRole) == "series-b"
    assert [line.get_label() for line in reopened._figure.axes[0].lines] == ["B"]

    editor.deleteLater()
    reopened.deleteLater()
    app.processEvents()


def test_chart_editor_undo_restores_soft_deleted_generated_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="nmr",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 2.0, 3.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0, 3.0], "y": [3.0, 2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)
    editor._btn_annotation_delete.click()

    assert [line.get_label() for line in editor._figure.axes[0].lines] == ["B"]

    editor._btn_annotation_undo.click()

    document = load_figure_document(str(figure_path))
    assert document["objects"][0]["id"] == "series-a"
    assert document["objects"][0]["deleted"] is False
    assert document["objects"][0]["visible"] is True
    assert editor._object_list.count() == 4
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-a"
    assert [line.get_label() for line in editor._figure.axes[0].lines] == ["A", "B"]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_delete_key_soft_deletes_generated_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(2)

    delete_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    app.sendEvent(editor._object_list, delete_event)

    assert delete_event.isAccepted()
    document = load_figure_document(str(figure_path))
    assert document["objects"][1]["deleted"] is True
    assert [line.get_label() for line in editor._figure.axes[0].lines] == ["A"]


def test_chart_editor_static_mode_hint_clarifies_annotation_only_boundary(tmp_path, monkeypatch):
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
        hint = editor._status_label.text().lower()
        assert "annotation" in hint
        assert "crop" in hint
        assert "not directly selectable" in hint
    finally:
        set_language(previous)

    editor.deleteLater()
    app.processEvents()

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_toggles_generated_legend_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    legend_item = editor._object_list.item(3)
    assert legend_item.data(Qt.UserRole) == "legend"
    assert legend_item.text() == "Legend"
    assert legend_item.checkState() == Qt.Checked
    assert editor._figure.axes[0].get_legend() is not None

    legend_item.setCheckState(Qt.Unchecked)
    app.processEvents()

    document = load_figure_document(str(figure_path))
    legend = [obj for obj in document["objects"] if obj["type"] == "legend"][0]
    assert legend["visible"] is False
    assert editor._figure.axes[0].get_legend() is None

    legend_item = editor._object_list.item(3)
    legend_item.setCheckState(Qt.Checked)
    app.processEvents()

    document = load_figure_document(str(figure_path))
    legend = [obj for obj in document["objects"] if obj["type"] == "legend"][0]
    assert legend["visible"] is True
    assert editor._figure.axes[0].get_legend() is not None

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_selection_selects_canvas_annotation(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    first_id = editor._annotation_canvas.add_text_annotation("First", 10, 10)
    second_id = editor._annotation_canvas.add_text_annotation("Second", 30, 20)

    editor._annotation_canvas.select_annotation(first_id)
    editor._object_list.setCurrentRow(2)

    assert editor._annotation_canvas.selected_annotation_id() == second_id
    assert editor._annotation_text_edit.text() == "Second"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_background_clears_annotation_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Peak", 20, 10)

    editor._object_list.setCurrentRow(0)

    assert editor._annotation_canvas.selected_annotation_id() == ""

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_escape_key_clears_static_annotation_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_text_annotation("Escape me", 20, 10)
    assert editor._annotation_canvas.select_annotation(annotation_id) is True
    assert editor._object_list.currentItem().data(Qt.UserRole) == annotation_id

    escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    editor._annotation_canvas.keyPressEvent(escape_event)

    assert escape_event.isAccepted()
    assert editor._annotation_canvas.selected_annotation_id() == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_delete_key_deletes_selected_annotation(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._annotation_canvas.add_text_annotation("Remove from list", 20, 10)
    editor._object_list.setCurrentRow(1)

    delete_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    app.sendEvent(editor._object_list, delete_event)

    assert delete_event.isAccepted()
    assert editor._annotation_canvas.annotation_state() == []
    assert editor._object_list.count() == 1
    assert editor._annotation_canvas.selected_annotation_id() == ""
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_copy_paste_shortcuts_duplicate_selected_annotation(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_text_annotation("Copy from list", 20, 10)
    editor._object_list.setCurrentRow(1)

    copy_event = QKeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier)
    app.sendEvent(editor._object_list, copy_event)
    paste_event = QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier)
    app.sendEvent(editor._object_list, paste_event)

    annotations = editor._annotation_canvas.annotation_state()
    pasted_id = editor._annotation_canvas.selected_annotation_id()

    assert copy_event.isAccepted()
    assert paste_event.isAccepted()
    assert len(annotations) == 2
    assert annotations[1]["text"] == "Copy from list"
    assert annotations[1]["id"] != annotation_id
    assert pasted_id == annotations[1]["id"]
    assert editor._object_list.count() == 3
    assert editor._object_list.currentItem().data(Qt.UserRole) == pasted_id

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_background_selection_clears_property_panel(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    text_id = editor._annotation_canvas.add_text_annotation("Peak", 20, 10)
    editor._annotation_canvas.select_annotation(text_id)

    assert editor._annotation_text_edit.text() == "Peak"
    assert editor._annotation_x_spin.isEnabled() is True

    editor._object_list.setCurrentRow(0)

    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
    assert editor._annotation_text_edit.text() == ""
    assert editor._annotation_x_spin.isEnabled() is False
    assert editor._annotation_y_spin.isEnabled() is False
    assert editor._annotation_w_spin.isEnabled() is False
    assert editor._annotation_h_spin.isEnabled() is False
    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"
    assert editor._annotation_w_label.text() == "W"
    assert editor._annotation_h_label.text() == "H"

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


def test_chart_editor_annotation_button_emits_single_change_event(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    changes = []
    editor.figure_changed.connect(lambda: changes.append("changed"))

    editor._annotation_text_edit.setText("One event")
    editor._btn_annotation_add_text.click()

    assert changes == ["changed"]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_control_emits_single_change_event(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_text_annotation("Point", 20, 10)
    editor._annotation_canvas.select_annotation(annotation_id)
    changes = []
    editor.figure_changed.connect(lambda: changes.append("changed"))

    editor._annotation_x_spin.setValue(0.5)

    assert changes == ["changed"]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_keyboard_delete_refreshes_object_list(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    annotation_id = editor._annotation_canvas.add_text_annotation("Delete me", 20, 10)
    editor._annotation_canvas.select_annotation(annotation_id)
    assert editor._object_list.count() == 2

    delete_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
    editor._annotation_canvas.keyPressEvent(delete_event)

    assert delete_event.isAccepted()
    assert editor._annotation_canvas.annotation_state() == []
    assert editor._object_list.count() == 1
    assert editor._object_list.item(0).data(Qt.UserRole) == "__background__"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_keyboard_undo_redo_refreshes_object_list(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    editor._annotation_canvas.add_text_annotation("Undo me", 20, 10)
    assert editor._object_list.count() == 2

    undo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    editor._annotation_canvas.keyPressEvent(undo_event)
    assert undo_event.isAccepted()
    assert editor._annotation_canvas.annotation_state() == []
    assert editor._object_list.count() == 1

    redo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Y, Qt.ControlModifier)
    editor._annotation_canvas.keyPressEvent(redo_event)
    assert redo_event.isAccepted()
    assert editor._annotation_canvas.annotation_state()[0]["text"] == "Undo me"
    assert editor._object_list.count() == 2
    assert "Undo me" in editor._object_list.item(1).text()

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_keyboard_undo_keeps_existing_object_selected(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    annotation_id = editor._annotation_canvas.add_text_annotation("Point", 20, 10)
    editor._annotation_canvas.select_annotation(annotation_id)
    editor._annotation_x_spin.setValue(0.5)
    assert editor._annotation_canvas.annotation_state()[0]["x"] == 0.5

    undo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    editor._annotation_canvas.keyPressEvent(undo_event)

    assert undo_event.isAccepted()
    assert editor._annotation_canvas.selected_annotation_id() == annotation_id
    assert editor._object_list.currentItem().data(Qt.UserRole) == annotation_id
    assert round(editor._annotation_x_spin.value(), 4) == 0.25

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_ctrl_z_after_unsynced_drag_emits_single_change_event(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_text_annotation("Point", 20, 10)
    editor._annotation_canvas.select_annotation(annotation_id)

    item = next(
        item for item in editor._annotation_canvas._scene.items()
        if item.data(0) == annotation_id
    )
    item.moveBy(20, 10)
    changes = []
    editor.figure_changed.connect(lambda: changes.append("changed"))

    undo_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Z, Qt.ControlModifier)
    editor._annotation_canvas.keyPressEvent(undo_event)

    annotation = editor._annotation_canvas.annotation_state()[0]
    assert undo_event.isAccepted()
    assert annotation["x"] == 0.25
    assert annotation["y"] == 0.25
    assert changes == ["changed"]

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


def test_chart_editor_selection_clears_text_field_for_non_text_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    text_id = editor._annotation_canvas.add_text_annotation("Text value", 20, 10)
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._annotation_text_edit.text() == "Text value"

    line_id = editor._annotation_canvas.add_line_annotation(10, 5, 40, 20)
    editor._annotation_canvas.select_annotation(line_id)

    assert editor._annotation_text_edit.text() == ""
    assert editor._selected_object_label.text() == "Line"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_update_text_button_only_enabled_for_text_object(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    text_id = editor._annotation_canvas.add_text_annotation("Editable", 20, 10)
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._btn_annotation_update_text.isEnabled() is True

    line_id = editor._annotation_canvas.add_line_annotation(10, 5, 40, 20)
    editor._annotation_canvas.select_annotation(line_id)
    assert editor._btn_annotation_update_text.isEnabled() is False

    editor._object_list.setCurrentRow(0)
    assert editor._btn_annotation_update_text.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_action_buttons_follow_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    editor._object_list.setCurrentRow(0)
    assert editor._btn_annotation_delete.isEnabled() is False
    assert editor._btn_annotation_copy.isEnabled() is False
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is False

    text_id = editor._annotation_canvas.add_text_annotation("Actionable", 20, 10)
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._btn_annotation_delete.isEnabled() is True
    assert editor._btn_annotation_copy.isEnabled() is True
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is False

    editor._object_list.setCurrentRow(0)
    assert editor._btn_annotation_delete.isEnabled() is False
    assert editor._btn_annotation_copy.isEnabled() is False
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_layer_buttons_follow_selected_object_order(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    bottom_id = editor._annotation_canvas.add_text_annotation("Bottom", 20, 10)
    top_id = editor._annotation_canvas.add_text_annotation("Top", 30, 20)

    editor._annotation_canvas.select_annotation(bottom_id)
    assert editor._btn_annotation_front.isEnabled() is True
    assert editor._btn_annotation_back.isEnabled() is False

    editor._annotation_canvas.select_annotation(top_id)
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is True

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_style_apply_controls_follow_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    editor._object_list.setCurrentRow(0)
    assert editor._annotation_color_edit.isEnabled() is False
    assert editor._btn_annotation_apply_style.isEnabled() is False

    text_id = editor._annotation_canvas.add_text_annotation("Styled", 20, 10)
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._annotation_color_edit.isEnabled() is True
    assert editor._btn_annotation_apply_style.isEnabled() is True

    editor._object_list.setCurrentRow(0)
    assert editor._annotation_color_edit.isEnabled() is False
    assert editor._btn_annotation_apply_style.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_style_controls_follow_selected_object_type(tmp_path, monkeypatch):
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
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._annotation_font_size_spin.isEnabled() is True
    assert editor._annotation_line_width_spin.isEnabled() is False
    assert editor._annotation_alpha_spin.isEnabled() is False

    line_id = editor._annotation_canvas.add_line_annotation(10, 5, 40, 20)
    editor._annotation_canvas.select_annotation(line_id)
    assert editor._annotation_font_size_spin.isEnabled() is False
    assert editor._annotation_line_width_spin.isEnabled() is True
    assert editor._annotation_alpha_spin.isEnabled() is False

    highlight_id = editor._annotation_canvas.add_highlight_annotation(10, 5, 30, 15)
    editor._annotation_canvas.select_annotation(highlight_id)
    assert editor._annotation_font_size_spin.isEnabled() is False
    assert editor._annotation_line_width_spin.isEnabled() is False
    assert editor._annotation_alpha_spin.isEnabled() is True

    editor._object_list.setCurrentRow(0)
    assert editor._annotation_font_size_spin.isEnabled() is False
    assert editor._annotation_line_width_spin.isEnabled() is False
    assert editor._annotation_alpha_spin.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_legend_selection_disables_rename_and_style_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(3)

    assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
    assert editor._btn_annotation_update_text.isEnabled() is False
    assert editor._annotation_color_edit.isEnabled() is False
    assert editor._annotation_line_width_spin.isEnabled() is False
    assert editor._annotation_alpha_spin.isEnabled() is False
    assert editor._btn_annotation_apply_style.isEnabled() is False
    assert editor._btn_annotation_delete.isEnabled() is False
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_controls_edit_selected_legend_anchor(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-legend-geometry-controls.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-legend-geometry-controls",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
            {
                "id": "legend",
                "type": "legend",
                "name": "Legend",
                "z_index": 2,
                "style": {"loc": "upper left", "bbox_to_anchor": [0.25, 0.85]},
            },
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(3)

    assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"
    assert editor._annotation_w_label.text() == ""
    assert editor._annotation_h_label.text() == ""
    assert editor._annotation_x_spin.isEnabled() is True
    assert editor._annotation_y_spin.isEnabled() is True
    assert editor._annotation_w_spin.isEnabled() is False
    assert editor._annotation_h_spin.isEnabled() is False
    assert round(editor._annotation_x_spin.value(), 4) == 0.25
    assert round(editor._annotation_y_spin.value(), 4) == 0.85

    editor._annotation_x_spin.setValue(0.45)
    editor._annotation_y_spin.setValue(0.7)

    document = load_figure_document(str(figure_path))
    legend_object = next(obj for obj in document["objects"] if obj["type"] == "legend")
    assert legend_object["style"]["loc"] == "upper left"
    assert legend_object["style"]["bbox_to_anchor"] == [0.45, 0.7]
    assert round(editor._annotation_x_spin.value(), 4) == 0.45
    assert round(editor._annotation_y_spin.value(), 4) == 0.7

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_legend_drag_updates_position_and_redraw(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-legend-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-legend-drag",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(3)

    legend = editor._figure.axes[0].get_legend()
    assert legend is not None
    editor._canvas.draw()
    start_bbox = legend.get_window_extent(editor._canvas.get_renderer())
    start_xpix = float((start_bbox.x0 + start_bbox.x1) / 2.0)
    start_ypix = float((start_bbox.y0 + start_bbox.y1) / 2.0)

    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = editor._figure.axes[0]
    editor._on_generated_button_press(press_event)

    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        start_xpix + 40.0,
        start_ypix - 20.0,
        button=1,
    )
    move_event.inaxes = editor._figure.axes[0]
    editor._on_generated_mouse_move(move_event)
    app.processEvents()
    editor._canvas.draw()

    moved_legend = editor._figure.axes[0].get_legend()
    assert moved_legend is not None
    moved_bbox = moved_legend.get_window_extent(editor._canvas.get_renderer())
    assert moved_bbox.x0 > start_bbox.x0 + 5.0

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        start_xpix + 40.0,
        start_ypix - 20.0,
        button=1,
    )
    release_event.inaxes = editor._figure.axes[0]
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    legend_object = next(
        obj for obj in document["objects"] if obj.get("type") == "legend"
    )
    assert legend_object["style"]["loc"] == "upper left"
    assert len(legend_object["style"]["bbox_to_anchor"]) == 2
    assert editor._selected_figure_object_id == "legend"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"

    final_legend = editor._figure.axes[0].get_legend()
    assert final_legend is not None
    editor._canvas.draw()
    final_bbox = final_legend.get_window_extent(editor._canvas.get_renderer())
    assert final_bbox.x0 > start_bbox.x0 + 5.0

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_legend_drag_shows_status_without_saved_anchor(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-hover.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-hover",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        editor._canvas.draw()
        start_bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((start_bbox.x0 + start_bbox.x1) / 2.0)
        hover_ypix = float((start_bbox.y0 + start_bbox.y1) / 2.0)

        press_event = MouseEvent(
            "button_press_event",
            editor._canvas,
            hover_xpix,
            hover_ypix,
            button=1,
        )
        press_event.inaxes = editor._figure.axes[0]
        editor._on_generated_button_press(press_event)

        drag_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            hover_xpix + 6.0,
            hover_ypix - 4.0,
        )
        drag_event.inaxes = editor._figure.axes[0]
        editor._on_generated_mouse_move(drag_event)

        status_text = editor._status_label.text().lower()
        assert "legend" in status_text
        assert "anchor" in status_text

        release_event = MouseEvent(
            "button_release_event",
            editor._canvas,
            hover_xpix + 6.0,
            hover_ypix - 4.0,
            button=1,
        )
        release_event.inaxes = editor._figure.axes[0]
        editor._on_generated_button_release(release_event)

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_tiny_motion_on_legend_selects_without_dragging(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-real-click-threshold.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-real-click-threshold",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._canvas.draw()
        app.processEvents()

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            hover_xpix,
            hover_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            hover_xpix + 1.0,
            hover_ypix + 1.0,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonRelease,
            hover_xpix + 1.0,
            hover_ypix + 1.0,
            button=Qt.LeftButton,
        )

        document = load_figure_document(str(figure_path))
        assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]
        assert editor._selected_figure_object_id == "legend"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
        _assert_selected_status(editor, "Legend")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_legend_edge_hover_and_click_selects_legend(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-real-edge-hover.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-real-edge-hover",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._canvas.draw()
        app.processEvents()

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float(bbox.x1 + 5.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "legend" in hint
        assert "drag" in hint
        assert editor._hovered_figure_object_id == "legend"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "legend"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
        _assert_selected_status(editor, "Legend")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_selected_legend_shows_drag_hint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-selected-hover-status.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-selected-hover-status",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(3)

        assert editor._selected_figure_object_id == "legend"
        _assert_selected_status(editor, "Legend")

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_LEGEND",
            "Legend",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        _assert_selected_status(editor, "Legend")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_legend_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-blank-real-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-blank-real-click",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._canvas.draw()
        app.processEvents()

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)
        assert editor._selected_figure_object_id == "legend"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
        _assert_selected_status(editor, "Legend")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_outside_legend_edge_does_not_select_legend(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-far-edge-real-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-far-edge-real-click",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._canvas.draw()
        app.processEvents()

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float(bbox.x1 + 14.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
        assert editor._hovered_figure_object_id == ""

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_legend_drag_updates_geometry_controls_live(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-legend-real-geometry-feedback.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-legend-real-geometry-feedback",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
            {
                "id": "legend",
                "type": "legend",
                "name": "Legend",
                "z_index": 2,
                "style": {"loc": "upper left", "bbox_to_anchor": [0.25, 0.85]},
            },
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))
    editor._canvas.draw()
    app.processEvents()

    legend = editor._figure.axes[0].get_legend()
    assert legend is not None
    bbox = legend.get_window_extent(editor._canvas.get_renderer())
    start_xpix = float((bbox.x0 + bbox.x1) / 2.0)
    start_ypix = float((bbox.y0 + bbox.y1) / 2.0)

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonPress,
        start_xpix,
        start_ypix,
        button=Qt.LeftButton,
        buttons=Qt.LeftButton,
    )

    assert editor._selected_figure_object_id == "legend"
    assert round(editor._annotation_x_spin.value(), 4) == 0.25
    assert round(editor._annotation_y_spin.value(), 4) == 0.85

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseMove,
        start_xpix + 36.0,
        start_ypix - 18.0,
        buttons=Qt.LeftButton,
    )

    moved_x = round(editor._annotation_x_spin.value(), 4)
    moved_y = round(editor._annotation_y_spin.value(), 4)
    assert moved_x != 0.25
    assert moved_y != 0.85

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonRelease,
        start_xpix + 36.0,
        start_ypix - 18.0,
        button=Qt.LeftButton,
    )

    document = load_figure_document(str(figure_path))
    legend_object = next(obj for obj in document["objects"] if obj["type"] == "legend")
    anchor = legend_object["style"]["bbox_to_anchor"]
    assert round(anchor[0], 4) == moved_x
    assert round(anchor[1], 4) == moved_y
    assert round(editor._annotation_x_spin.value(), 4) == moved_x
    assert round(editor._annotation_y_spin.value(), 4) == moved_y

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_escape_cancels_legend_drag_without_saved_anchor(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-real-escape-cancel.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-real-escape-cancel",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._canvas.draw()
        app.processEvents()

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        start_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        start_ypix = float((bbox.y0 + bbox.y1) / 2.0)

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            start_xpix,
            start_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )

        start_anchor_x = round(editor._annotation_x_spin.value(), 4)
        start_anchor_y = round(editor._annotation_y_spin.value(), 4)
        assert editor._selected_figure_object_id == "legend"

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            start_xpix + 36.0,
            start_ypix - 18.0,
            buttons=Qt.LeftButton,
        )

        moved_anchor_x = round(editor._annotation_x_spin.value(), 4)
        moved_anchor_y = round(editor._annotation_y_spin.value(), 4)
        assert moved_anchor_x != start_anchor_x
        assert moved_anchor_y != start_anchor_y

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._generated_handle_drag_state is None
        assert editor._selected_figure_object_id == "legend"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
        assert editor._status_label.text().lower().startswith("selected")
        assert round(editor._annotation_x_spin.value(), 4) == start_anchor_x
        assert round(editor._annotation_y_spin.value(), 4) == start_anchor_y

        document = load_figure_document(str(figure_path))
        assert [obj["type"] for obj in document["objects"]] == ["plot_series", "plot_series"]

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_canvas_pick_selects_generated_legend_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-legend-pick.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-legend-pick",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    legend = editor._figure.axes[0].get_legend()
    assert legend is not None

    editor._on_generated_pick_event(SimpleNamespace(artist=legend))

    assert editor._selected_figure_object_id == "legend"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "legend"
    assert editor._annotation_text_edit.text() == "Legend"
    assert editor._btn_annotation_update_text.isEnabled() is False
    assert editor._btn_annotation_delete.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_auto_generated_legend_uses_clean_feedback_label(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-legend-clean-label.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-legend-clean-label",
            objects=[
                {
                    "id": "series-a",
                    "type": "plot_series",
                    "name": "A",
                    "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                },
                {
                    "id": "series-b",
                    "type": "plot_series",
                    "name": "B",
                    "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        legend_item = editor._object_list.item(3)
        assert legend_item.data(Qt.UserRole) == "legend"
        assert legend_item.text() == "Legend"

        legend = editor._figure.axes[0].get_legend()
        assert legend is not None
        editor._canvas.draw()
        bbox = legend.get_window_extent(editor._canvas.get_renderer())
        hover_xpix = float((bbox.x0 + bbox.x1) / 2.0)
        hover_ypix = float((bbox.y0 + bbox.y1) / 2.0)
        hover_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            hover_xpix,
            hover_ypix,
        )
        hover_event.inaxes = editor._figure.axes[0]
        editor._on_generated_mouse_move(hover_event)
        assert editor._status_label.text() == tr("EDITOR_HOVER_HINT_DRAG_LEGEND", "Legend")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)
        assert editor._selected_figure_object_id == "legend"
        _assert_selected_status(editor, "Legend")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_generated_image_grid_selection_disables_style_and_reorder_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated_grid.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    image_a = data_dir / "pattern_a.npy"
    image_b = data_dir / "pattern_b.npy"
    np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
    np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
    metadata_path = data_dir / "grid_metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 0,
                "strain_pct": 0.0,
                "image_path": str(image_a),
            }
        )
        writer.writerow(
            {
                "grid_row": 0,
                "grid_col": 1,
                "strain_pct": 25.0,
                "image_path": str(image_b),
            }
        )

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated_grid",
        data_sources=[
            {
                "id": "grid-metadata",
                "kind": "csv",
                "path": str(metadata_path),
                "role": "plot_data",
            }
        ],
        style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
        objects=[
            {
                "id": "series-pattern-grid",
                "type": "plot_series",
                "chart_kind": "image_grid",
                "name": "2D WAXS Pattern Grid",
                "data_ref": "grid-metadata",
                "row_column": "grid_row",
                "column_column": "grid_col",
                "image_path_column": "image_path",
                "label_column": "strain_pct",
                "style": {"colormap": "inferno"},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-pattern-grid"
    assert editor._btn_annotation_update_text.isEnabled() is True
    assert editor._annotation_color_edit.isEnabled() is False
    assert editor._annotation_line_width_spin.isEnabled() is False
    assert editor._annotation_alpha_spin.isEnabled() is False
    assert editor._annotation_line_style_combo.isEnabled() is False
    assert editor._annotation_marker_combo.isEnabled() is False
    assert editor._btn_annotation_apply_style.isEnabled() is False
    assert editor._btn_annotation_delete.isEnabled() is True
    assert editor._btn_annotation_front.isEnabled() is False
    assert editor._btn_annotation_back.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_line_selection_populates_geometry_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_x_label.text() == "X1"
    assert editor._annotation_y_label.text() == "Y1"
    assert editor._annotation_w_label.text() == "X2"
    assert editor._annotation_h_label.text() == "Y2"
    assert editor._annotation_x_spin.isEnabled() is True
    assert editor._annotation_w_spin.isEnabled() is True
    assert editor._annotation_x_spin.value() == 1.5
    assert editor._annotation_y_spin.value() == 0.25
    assert editor._annotation_w_spin.value() == 2.5
    assert editor._annotation_h_spin.value() == 3.75

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_selected_generated_line_renders_control_handles(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-handles.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-handles",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:line-qstar"
    ]

    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.5, 0.25], [2.5, 3.75]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_line_geometry_change_redraws_and_persists(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    editor._annotation_x_spin.setValue(1.75)
    editor._annotation_y_spin.setValue(0.5)
    editor._annotation_w_spin.setValue(2.75)
    editor._annotation_h_spin.setValue(4.25)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.5
    assert line["x2"] == 2.75
    assert line["y2"] == 4.25
    assert list(editor._figure.axes[0].lines[0].get_xdata()) == [1.75, 2.75]
    assert list(editor._figure.axes[0].lines[0].get_ydata()) == [0.5, 4.25]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_selected_line_shows_default_current_endpoint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-selected-default-endpoint.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-selected-default-endpoint",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._selected_figure_object_id == "line-qstar"
    assert editor._selected_generated_line_object_id == "line-qstar"
    assert editor._selected_generated_line_handle_index == 0
    assert round(editor._annotation_x_spin.value(), 4) == 1.5
    assert round(editor._annotation_y_spin.value(), 4) == 0.25
    assert round(editor._annotation_w_spin.value(), 4) == 2.5
    assert round(editor._annotation_h_spin.value(), 4) == 3.75

    current_handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-current-handle:line-qstar"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[1.5, 0.25]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_line_handle_drag_updates_geometry_and_redraw(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-drag",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((1.5, 0.25))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((1.75, 0.5))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    current_handle_artists = [
        artist
        for artist in start_axes.collections
        if artist.get_gid() == "pn-current-handle:line-qstar"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[1.75, 0.5]],
    )

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.5
    assert line["x2"] == 2.5
    assert line["y2"] == 3.75
    assert editor._annotation_x_spin.value() == 1.75
    assert editor._annotation_y_spin.value() == 0.5
    assert editor._annotation_w_spin.value() == 2.5
    assert editor._annotation_h_spin.value() == 3.75
    assert list(editor._figure.axes[0].lines[0].get_xdata()) == [1.75, 2.5]
    assert list(editor._figure.axes[0].lines[0].get_ydata()) == [0.5, 3.75]

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:line-qstar"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.75, 0.5], [2.5, 3.75]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_line_body_drag_updates_geometry_and_redraw(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-body-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-body-drag",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 2.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.25, 2.5))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.75
    assert line["x2"] == 2.75
    assert line["y2"] == 4.25
    assert list(editor._figure.axes[0].lines[0].get_xdata()) == [1.75, 2.75]
    assert list(editor._figure.axes[0].lines[0].get_ydata()) == [0.75, 4.25]
    assert editor._annotation_x_spin.value() == 1.75
    assert editor._annotation_y_spin.value() == 0.75
    assert editor._annotation_w_spin.value() == 2.75
    assert editor._annotation_h_spin.value() == 4.25

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:line-qstar"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.75, 0.75], [2.75, 4.25]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_line_body_drag_updates_geometry_feedback(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-real-geometry-feedback.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-real-geometry-feedback",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    start_xpix, start_ypix = axes.transData.transform((2.0, 2.0))
    move_xpix, move_ypix = axes.transData.transform((2.25, 2.5))

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonPress,
        start_xpix,
        start_ypix,
        button=Qt.LeftButton,
        buttons=Qt.LeftButton,
    )

    assert editor._selected_figure_object_id == "line-qstar"
    assert editor._annotation_x_label.text() == "X1"
    assert editor._annotation_y_label.text() == "Y1"
    assert editor._annotation_w_label.text() == "X2"
    assert editor._annotation_h_label.text() == "Y2"
    assert round(editor._annotation_x_spin.value(), 4) == 1.5
    assert round(editor._annotation_y_spin.value(), 4) == 0.25
    assert round(editor._annotation_w_spin.value(), 4) == 2.5
    assert round(editor._annotation_h_spin.value(), 4) == 3.75

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseMove,
        move_xpix,
        move_ypix,
        buttons=Qt.LeftButton,
    )

    assert round(editor._annotation_x_spin.value(), 4) == 1.75
    assert round(editor._annotation_y_spin.value(), 4) == 0.75
    assert round(editor._annotation_w_spin.value(), 4) == 2.75
    assert round(editor._annotation_h_spin.value(), 4) == 4.25
    assert editor._status_label.text() == tr(
        "EDITOR_DRAG_STATUS_LINE",
        "Line: q*",
        "1.75",
        "0.75",
        "2.75",
        "4.25",
    )

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonRelease,
        move_xpix,
        move_ypix,
        button=Qt.LeftButton,
    )

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.75
    assert line["x2"] == 2.75
    assert line["y2"] == 4.25

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_tiny_motion_on_line_body_selects_without_dragging(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-real-click-threshold.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-real-click-threshold",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        start_xpix, start_ypix = axes.transData.transform((2.0, 2.0))
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            start_xpix,
            start_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            start_xpix + 1.0,
            start_ypix + 1.0,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonRelease,
            start_xpix + 1.0,
            start_ypix + 1.0,
            button=Qt.LeftButton,
        )

        document = load_figure_document(str(figure_path))
        line = document["objects"][0]
        assert line["x1"] == 1.5
        assert line["y1"] == 0.25
        assert line["x2"] == 2.5
        assert line["y2"] == 3.75
        assert editor._selected_figure_object_id == "line-qstar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
        _assert_selected_status(editor, "Line: q*")
        assert editor._annotation_x_label.text() == "X1"
        assert editor._annotation_y_label.text() == "Y1"
        assert editor._annotation_w_label.text() == "X2"
        assert editor._annotation_h_label.text() == "Y2"
        assert round(editor._annotation_x_spin.value(), 4) == 1.5
        assert round(editor._annotation_y_spin.value(), 4) == 0.25
        assert round(editor._annotation_w_spin.value(), 4) == 2.5
        assert round(editor._annotation_h_spin.value(), 4) == 3.75

        current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:line-qstar"
        ]
        assert len(current_handle_artists) == 1
        np.testing.assert_allclose(
            current_handle_artists[0].get_offsets(),
            [[1.5, 0.25]],
        )

        line_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "line-qstar"
        )
        np.testing.assert_allclose(line_artist.get_xdata(), [1.5, 2.5])
        np.testing.assert_allclose(line_artist.get_ydata(), [0.25, 3.75])

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_line_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-real-blank-deselect.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-real-blank-deselect",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        line_xpix, line_ypix = axes.transData.transform((2.0, 2.0))
        _send_matplotlib_canvas_click(editor._canvas, line_xpix, line_ypix)

        assert editor._selected_figure_object_id == "line-qstar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
        _assert_selected_status(editor, "Line: q*")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        line_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "line-qstar"
        )
        assert line_artist.get_path_effects() == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_updates_status_hint_for_line_body(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-real-hover-status.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-real-hover-status",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        initial_cursor = editor._canvas.cursor().shape()
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 2.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "line-qstar"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_LINE",
            "Line: q*",
        )

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        _send_matplotlib_canvas_move(editor._canvas, away_xpix, away_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._canvas.cursor().shape() == initial_cursor
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_line_body_hover_and_click_selects_line(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-real-near-body-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-real-near-body-click",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.5, 0.25), (2.5, 3.75)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 9.0)
        hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 9.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "line-qstar"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_LINE",
            "Line: q*",
        )

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "line-qstar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
        assert editor._selected_object_label.text() == "Line: q*"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Line: q*")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_selected_line_body_shows_drag_hint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-selected-hover-status.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-selected-hover-status",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "line-qstar"
        _assert_selected_status(editor, "Line: q*")

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.5, 0.25), (2.5, 3.75)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 9.0)
        hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 9.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._canvas.cursor().shape() == Qt.CursorShape.OpenHandCursor
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_LINE",
            "Line: q*",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        _assert_selected_status(editor, "Line: q*")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_from_line_body_does_not_select_line(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-real-far-body-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-real-far-body-click",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.5, 0.25), (2.5, 3.75)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 16.0)
        hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 16.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_cancels_line_body_drag_and_restores_values(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-real-escape-cancel.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-real-escape-cancel",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        start_xpix, start_ypix = axes.transData.transform((2.0, 2.0))
        move_xpix, move_ypix = axes.transData.transform((2.25, 2.5))

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            start_xpix,
            start_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            move_xpix,
            move_ypix,
            buttons=Qt.LeftButton,
        )

        preview_geometry = editor._generated_handle_drag_state["preview_geometry"]
        assert preview_geometry["x1"] == 1.75
        assert preview_geometry["y1"] == 0.75
        assert preview_geometry["x2"] == 2.75
        assert preview_geometry["y2"] == 4.25
        assert editor._figure_document["objects"][0]["x1"] == 1.5
        assert editor._figure_document["objects"][0]["y1"] == 0.25
        assert round(editor._annotation_x_spin.value(), 4) == 1.75
        assert round(editor._annotation_y_spin.value(), 4) == 0.75
        assert round(editor._annotation_w_spin.value(), 4) == 2.75
        assert round(editor._annotation_h_spin.value(), 4) == 4.25

        moved_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "line-qstar"
        )
        np.testing.assert_allclose(moved_artist.get_xdata(), [1.75, 2.75])
        np.testing.assert_allclose(moved_artist.get_ydata(), [0.75, 4.25])

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._generated_handle_drag_state is None
        assert editor._selected_figure_object_id == "line-qstar"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
        assert editor._status_label.text().lower().startswith("selected")
        assert round(editor._annotation_x_spin.value(), 4) == 1.5
        assert round(editor._annotation_y_spin.value(), 4) == 0.25
        assert round(editor._annotation_w_spin.value(), 4) == 2.5
        assert round(editor._annotation_h_spin.value(), 4) == 3.75

        restored_line = editor._figure_document["objects"][0]
        assert restored_line["x1"] == 1.5
        assert restored_line["y1"] == 0.25
        assert restored_line["x2"] == 2.5
        assert restored_line["y2"] == 3.75

        restored_document = load_figure_document(str(figure_path))
        persisted_line = restored_document["objects"][0]
        assert persisted_line["x1"] == 1.5
        assert persisted_line["y1"] == 0.25
        assert persisted_line["x2"] == 2.5
        assert persisted_line["y2"] == 3.75

        restored_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "line-qstar"
        )
        np.testing.assert_allclose(restored_artist.get_xdata(), [1.5, 2.5])
        np.testing.assert_allclose(restored_artist.get_ydata(), [0.25, 3.75])

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_cancels_line_endpoint_drag_and_restores_values(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-endpoint-real-escape-cancel.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="saxs",
            figure_id="generated-line-endpoint-real-escape-cancel",
            objects=[
                {
                    "id": "line-qstar",
                    "type": "line",
                    "name": "q*",
                    "x1": 1.5,
                    "y1": 0.25,
                    "x2": 2.5,
                    "y2": 3.75,
                    "style": {"color": "#D55E00", "line_width": 1.5},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        start_xpix, start_ypix = axes.transData.transform((1.5, 0.25))
        move_xpix, move_ypix = axes.transData.transform((1.75, 0.5))

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            start_xpix,
            start_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            move_xpix,
            move_ypix,
            buttons=Qt.LeftButton,
        )

        preview_geometry = editor._generated_handle_drag_state["preview_geometry"]
        assert preview_geometry["x1"] == 1.75
        assert preview_geometry["y1"] == 0.5
        assert preview_geometry["x2"] == 2.5
        assert preview_geometry["y2"] == 3.75
        assert editor._figure_document["objects"][0]["x1"] == 1.5
        assert editor._figure_document["objects"][0]["y1"] == 0.25
        assert round(editor._annotation_x_spin.value(), 4) == 1.75
        assert round(editor._annotation_y_spin.value(), 4) == 0.5
        assert round(editor._annotation_w_spin.value(), 4) == 2.5
        assert round(editor._annotation_h_spin.value(), 4) == 3.75

        moved_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "line-qstar"
        )
        np.testing.assert_allclose(moved_artist.get_xdata(), [1.75, 2.5])
        np.testing.assert_allclose(moved_artist.get_ydata(), [0.5, 3.75])

        moved_current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:line-qstar"
        ]
        assert len(moved_current_handle_artists) == 1
        np.testing.assert_allclose(
            moved_current_handle_artists[0].get_offsets(),
            [[1.75, 0.5]],
        )

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._generated_handle_drag_state is None
        assert editor._selected_figure_object_id == "line-qstar"
        assert editor._selected_generated_line_object_id == "line-qstar"
        assert editor._selected_generated_line_handle_index == 0
        assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
        assert editor._status_label.text().lower().startswith("selected")
        assert round(editor._annotation_x_spin.value(), 4) == 1.5
        assert round(editor._annotation_y_spin.value(), 4) == 0.25
        assert round(editor._annotation_w_spin.value(), 4) == 2.5
        assert round(editor._annotation_h_spin.value(), 4) == 3.75

        restored_line = editor._figure_document["objects"][0]
        assert restored_line["x1"] == 1.5
        assert restored_line["y1"] == 0.25
        assert restored_line["x2"] == 2.5
        assert restored_line["y2"] == 3.75

        restored_document = load_figure_document(str(figure_path))
        persisted_line = restored_document["objects"][0]
        assert persisted_line["x1"] == 1.5
        assert persisted_line["y1"] == 0.25
        assert persisted_line["x2"] == 2.5
        assert persisted_line["y2"] == 3.75

        restored_artist = next(
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "line-qstar"
        )
        np.testing.assert_allclose(restored_artist.get_xdata(), [1.5, 2.5])
        np.testing.assert_allclose(restored_artist.get_ydata(), [0.25, 3.75])

        restored_current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:line-qstar"
        ]
        assert len(restored_current_handle_artists) == 1
        np.testing.assert_allclose(
            restored_current_handle_artists[0].get_offsets(),
            [[1.5, 0.25]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_direct_press_on_unselected_line_selects_and_drags_it(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-press-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-press-drag",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_figure_object_id == ""

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 2.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.25, 2.5))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.75
    assert line["x2"] == 2.75
    assert line["y2"] == 4.25
    assert editor._selected_figure_object_id == "line-qstar"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
    assert list(editor._figure.axes[0].lines[0].get_xdata()) == [1.75, 2.75]
    assert list(editor._figure.axes[0].lines[0].get_ydata()) == [0.75, 4.25]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_direct_press_on_unselected_line_endpoint_drags_only_that_endpoint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-endpoint-press-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-endpoint-press-drag",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    start_axes = editor._figure.axes[0]
    endpoint_xpix, endpoint_ypix = start_axes.transData.transform((1.5, 0.25))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        endpoint_xpix,
        endpoint_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((1.75, 0.5))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.5
    assert line["x2"] == 2.5
    assert line["y2"] == 3.75
    assert editor._selected_figure_object_id == "line-qstar"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "line-qstar"
    assert list(editor._figure.axes[0].lines[0].get_xdata()) == [1.75, 2.5]
    assert list(editor._figure.axes[0].lines[0].get_ydata()) == [0.5, 3.75]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_direct_press_on_selected_line_endpoint_keeps_unselected_hit_slop(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-endpoint-selected-press-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-line-endpoint-selected-press-drag",
        objects=[
            {
                "id": "line-qstar",
                "type": "line",
                "name": "q*",
                "x1": 1.5,
                "y1": 0.25,
                "x2": 2.5,
                "y2": 3.75,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    start_axes = editor._figure.axes[0]
    pixel_points = start_axes.transData.transform([(1.5, 0.25), (2.5, 3.75)])
    segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
    segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
    segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
    assert segment_length > 0.0
    normal_x = -segment_dy / segment_length
    normal_y = segment_dx / segment_length
    press_xpix = float(pixel_points[0][0] + normal_x * 13.0)
    press_ypix = float(pixel_points[0][1] + normal_y * 13.0)

    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        press_xpix,
        press_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((1.75, 0.5))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["y1"] == 0.5
    assert line["x2"] == 2.5
    assert line["y2"] == 3.75

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_vertical_line_uses_single_x_geometry_control(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-vline.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-vline",
        objects=[
            {
                "id": "line-vref",
                "type": "line",
                "name": "q ref",
                "x1": 1.5,
                "y1": 0.0,
                "x2": None,
                "y2": 1.0,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_x_spin.isEnabled() is True
    assert editor._annotation_y_spin.isEnabled() is False
    assert editor._annotation_w_spin.isEnabled() is False
    assert editor._annotation_h_spin.isEnabled() is False
    assert editor._annotation_x_spin.value() == 1.5

    editor._annotation_x_spin.setValue(1.75)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["x1"] == 1.75
    assert line["x2"] is None
    assert list(editor._figure.axes[0].lines[0].get_xdata()) == [1.75, 1.75]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_horizontal_line_uses_single_y_geometry_control(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-hline.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="saxs",
        figure_id="generated-hline",
        objects=[
            {
                "id": "line-href",
                "type": "line",
                "name": "intensity ref",
                "x1": 0.0,
                "y1": 2.5,
                "x2": 1.0,
                "y2": None,
                "style": {"color": "#D55E00", "line_width": 1.5},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_y_label.text() == "Y"
    assert editor._annotation_x_spin.isEnabled() is False
    assert editor._annotation_y_spin.isEnabled() is True
    assert editor._annotation_w_spin.isEnabled() is False
    assert editor._annotation_h_spin.isEnabled() is False
    assert editor._annotation_y_spin.value() == 2.5

    editor._annotation_y_spin.setValue(2.75)

    document = load_figure_document(str(figure_path))
    line = document["objects"][0]
    assert line["y1"] == 2.75
    assert line["y2"] is None
    assert list(editor._figure.axes[0].lines[0].get_ydata()) == [2.75, 2.75]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_style_controls_reset_values_for_unsupported_properties(tmp_path, monkeypatch):
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
    editor._annotation_canvas.update_selected_properties(font_size=18)
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._annotation_font_size_spin.value() == 18

    line_id = editor._annotation_canvas.add_line_annotation(10, 5, 40, 20)
    editor._annotation_canvas.update_selected_properties(line_width=4.5)
    editor._annotation_canvas.select_annotation(line_id)
    assert editor._annotation_font_size_spin.value() == 12
    assert editor._annotation_line_width_spin.value() == 4.5

    highlight_id = editor._annotation_canvas.add_highlight_annotation(10, 5, 30, 15)
    editor._annotation_canvas.update_selected_properties(alpha=0.6)
    editor._annotation_canvas.select_annotation(highlight_id)
    assert editor._annotation_line_width_spin.value() == 2.0
    assert editor._annotation_alpha_spin.value() == 0.6
    assert editor._annotation_line_style_combo.currentText() == "Solid"
    assert editor._annotation_marker_combo.currentText() == "None"
    assert editor._annotation_marker_size_spin.value() == 6.0

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_plot_series_style_extras_follow_selection(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated",
        objects=[
            {
                "id": "series-a",
                "type": "plot_series",
                "name": "A",
                "data": {"x": [1.0, 2.0], "y": [1.0, 2.0]},
                "style": {"line_style": ":", "marker": "s", "marker_size": 11.0},
            },
            {
                "id": "series-b",
                "type": "plot_series",
                "name": "B",
                "data": {"x": [1.0, 2.0], "y": [2.0, 1.0]},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_line_style_combo.isEnabled() is True
    assert editor._annotation_marker_combo.isEnabled() is True
    assert editor._annotation_marker_size_spin.isEnabled() is True
    assert editor._annotation_line_style_combo.currentText() == "Dotted"
    assert editor._annotation_marker_combo.currentText() == "Square"
    assert editor._annotation_marker_size_spin.value() == 11.0

    editor._object_list.setCurrentRow(3)
    assert editor._annotation_line_style_combo.isEnabled() is False
    assert editor._annotation_marker_combo.isEnabled() is False
    assert editor._annotation_marker_size_spin.isEnabled() is False

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_scatter_style_controls_follow_visible_defaults(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-style.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-style",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0], "y": [1.0, 3.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._annotation_line_style_combo.isEnabled() is False
    assert editor._annotation_marker_combo.isEnabled() is True
    assert editor._annotation_marker_size_spin.isEnabled() is True
    assert editor._annotation_marker_combo.currentText() == "Circle"
    assert editor._annotation_marker_size_spin.value() == 8.0
    assert editor._selected_generated_plot_series_object_id == "series-scatter"
    assert editor._selected_generated_plot_series_handle_index == 0
    assert round(editor._annotation_x_spin.value(), 4) == 1.0
    assert round(editor._annotation_y_spin.value(), 4) == 1.0

    current_handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-current-handle:series-scatter"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[1.0, 1.0]],
    )

    editor._annotation_line_width_spin.setValue(2.5)
    editor._annotation_marker_combo.setCurrentText("Square")
    editor._annotation_marker_size_spin.setValue(9.0)
    editor._btn_annotation_apply_style.click()

    document = load_figure_document(str(figure_path))
    assert document["objects"][0]["style"]["line_width"] == 2.5
    assert document["objects"][0]["style"]["marker"] == "s"
    assert document["objects"][0]["style"]["marker_size"] == 9.0

    editor._object_list.setCurrentRow(0)
    scatter_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
    ]
    assert len(scatter_artists) == 1
    assert float(scatter_artists[0].get_linewidths()[0]) == 2.5
    assert scatter_artists[0].get_sizes()[0] == 81.0

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_reselect_keeps_current_marker_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-marker-line-reselect-keeps-current.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-marker-line-reselect-keeps-current",
        objects=[
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Marked",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker": "o", "marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    axes = editor._figure.axes[0]
    second_xpix, second_ypix = axes.transData.transform((2.0, 3.0))
    _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

    assert editor._selected_generated_plot_series_object_id == "series-marked"
    assert editor._selected_generated_plot_series_handle_index == 1
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    editor._object_list.setCurrentRow(1)

    assert editor._selected_generated_plot_series_object_id == "series-marked"
    assert editor._selected_generated_plot_series_handle_index == 1
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    current_handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-current-handle:series-marked"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[2.0, 3.0]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_object_list_reselect_restores_previous_marker_point_after_deselect(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-marker-line-restore-previous-point.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-marker-line-restore-previous-point",
        objects=[
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Marked",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker": "o", "marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    axes = editor._figure.axes[0]
    second_xpix, second_ypix = axes.transData.transform((2.0, 3.0))
    _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

    assert editor._selected_generated_plot_series_object_id == "series-marked"
    assert editor._selected_generated_plot_series_handle_index == 1

    _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"

    editor._object_list.setCurrentRow(1)

    assert editor._selected_figure_object_id == "series-marked"
    assert editor._selected_generated_plot_series_object_id == "series-marked"
    assert editor._selected_generated_plot_series_handle_index == 1
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    current_handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-current-handle:series-marked"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[2.0, 3.0]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_source_switch_resets_handle_memory_for_reused_object_ids(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    first_path = tmp_path / "figures" / "generated-handle-memory-first.png"
    first_path.parent.mkdir()
    first_pixmap = QPixmap(80, 40)
    first_pixmap.fill(QColor("white"))
    assert first_pixmap.save(str(first_path))

    second_path = tmp_path / "figures" / "generated-handle-memory-second.png"
    second_path.parent.mkdir(exist_ok=True)
    second_pixmap = QPixmap(80, 40)
    second_pixmap.fill(QColor("white"))
    assert second_pixmap.save(str(second_path))

    shared_line_id = "shared-line"
    shared_series_id = "shared-series"

    save_generated_figure_document(
        str(first_path),
        technique="waxs",
        figure_id="generated-handle-memory-first",
        objects=[
            {
                "id": shared_line_id,
                "type": "line",
                "name": "Shared line",
                "x1": 1.0,
                "y1": 1.0,
                "x2": 2.0,
                "y2": 2.0,
                "style": {"color": "#D55E00", "line_width": 1.5},
            },
            {
                "id": shared_series_id,
                "type": "plot_series",
                "name": "Shared series",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2, "marker": "o", "marker_size": 8.0},
            },
        ],
    )

    save_generated_figure_document(
        str(second_path),
        technique="waxs",
        figure_id="generated-handle-memory-second",
        objects=[
            {
                "id": shared_line_id,
                "type": "line",
                "name": "Shared line",
                "x1": 10.0,
                "y1": 10.0,
                "x2": 20.0,
                "y2": 20.0,
                "style": {"color": "#0072B2", "line_width": 1.5},
            },
            {
                "id": shared_series_id,
                "type": "plot_series",
                "name": "Shared series",
                "data": {"x": [10.0, 20.0, 30.0], "y": [10.0, 30.0, 20.0]},
                "style": {"line_width": 1.2, "marker": "o", "marker_size": 8.0},
            },
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(first_path))

    editor._object_list.setCurrentRow(1)
    first_axes = editor._figure.axes[0]
    line_endpoint_xpix, line_endpoint_ypix = first_axes.transData.transform((2.0, 2.0))
    _send_matplotlib_canvas_click(editor._canvas, line_endpoint_xpix, line_endpoint_ypix)
    assert editor._selected_generated_line_handle_index == 1

    editor._object_list.setCurrentRow(2)
    series_second_xpix, series_second_ypix = first_axes.transData.transform((2.0, 3.0))
    _send_matplotlib_canvas_click(editor._canvas, series_second_xpix, series_second_ypix)
    assert editor._selected_generated_plot_series_handle_index == 1

    editor.set_source_figure(str(second_path))

    editor._object_list.setCurrentRow(1)
    second_line_artist = editor._figure.axes[0].lines[0]
    assert editor._selected_figure_object_id == shared_line_id
    assert editor._selected_generated_line_handle_index == 0
    np.testing.assert_allclose(second_line_artist.get_xdata(), [10.0, 20.0])
    np.testing.assert_allclose(second_line_artist.get_ydata(), [10.0, 20.0])
    current_line_handles = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == f"pn-current-handle:{shared_line_id}"
    ]
    assert len(current_line_handles) == 1
    np.testing.assert_allclose(current_line_handles[0].get_offsets(), [[10.0, 10.0]])

    editor._object_list.setCurrentRow(2)
    second_axes = editor._figure.axes[0]
    assert editor._selected_figure_object_id == shared_series_id
    assert editor._selected_generated_plot_series_handle_index == 0
    assert round(editor._annotation_x_spin.value(), 4) == 10.0
    assert round(editor._annotation_y_spin.value(), 4) == 10.0
    current_series_handles = [
        artist
        for artist in second_axes.collections
        if artist.get_gid() == f"pn-current-handle:{shared_series_id}"
    ]
    assert len(current_series_handles) == 1
    np.testing.assert_allclose(current_series_handles[0].get_offsets(), [[10.0, 10.0]])

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_selected_generated_plot_series_with_marker_renders_control_handles(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-marker-handles.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-marker-handles",
        objects=[
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Marked",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker": "o", "marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    assert editor._selected_figure_object_id == "series-marked"
    assert editor._selected_generated_plot_series_object_id == "series-marked"
    assert editor._selected_generated_plot_series_handle_index == 0

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:series-marked"
    ]

    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.0, 3.0], [3.0, 2.0]],
    )
    current_handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-current-handle:series-marked"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[1.0, 1.0]],
    )
    assert round(editor._annotation_x_spin.value(), 4) == 1.0
    assert round(editor._annotation_y_spin.value(), 4) == 1.0

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_plot_series_handle_drag_updates_data_and_redraw(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-series-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-series-drag",
        objects=[
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Marked",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker": "o", "marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 3.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.25, 2.5))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    np.testing.assert_allclose(
        start_axes.lines[0].get_xdata(),
        [1.0, 2.25, 3.0],
    )
    np.testing.assert_allclose(
        start_axes.lines[0].get_ydata(),
        [1.0, 2.5, 2.0],
    )
    preview_handle_artists = [
        artist
        for artist in start_axes.collections
        if artist.get_gid() == "pn-selection-handles:series-marked"
    ]
    assert len(preview_handle_artists) == 1
    np.testing.assert_allclose(
        preview_handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.25, 2.5], [3.0, 2.0]],
    )
    preview_current_handle_artists = [
        artist
        for artist in start_axes.collections
        if artist.get_gid() == "pn-current-handle:series-marked"
    ]
    assert len(preview_current_handle_artists) == 1
    np.testing.assert_allclose(
        preview_current_handle_artists[0].get_offsets(),
        [[2.25, 2.5]],
    )

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.25, 3.0]
    assert series["data"]["y"] == [1.0, 2.5, 2.0]
    assert editor._selected_figure_object_id == "series-marked"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-marked"

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:series-marked"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        editor._figure.axes[0].lines[0].get_xdata(),
        [1.0, 2.25, 3.0],
    )
    np.testing.assert_allclose(
        editor._figure.axes[0].lines[0].get_ydata(),
        [1.0, 2.5, 2.0],
    )
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.25, 2.5], [3.0, 2.0]],
    )
    current_handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-current-handle:series-marked"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[2.25, 2.5]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_data_source_plot_series_handle_drag_materializes_inline_data(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-series-source-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    series_path = data_dir / "series.csv"
    with series_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["q", "intensity"])
        writer.writeheader()
        writer.writerow({"q": 1.0, "intensity": 1.0})
        writer.writerow({"q": 2.0, "intensity": 3.0})
        writer.writerow({"q": 3.0, "intensity": 2.0})

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-series-source-drag",
        data_sources=[
            {
                "id": "series-data",
                "kind": "csv",
                "path": str(series_path),
                "role": "plot_data",
            }
        ],
        objects=[
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Marked",
                "data_ref": "series-data",
                "x_column": "q",
                "y_column": "intensity",
                "style": {"marker": "o", "marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 3.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.4, 2.6))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    np.testing.assert_allclose(
        start_axes.lines[0].get_xdata(),
        [1.0, 2.4, 3.0],
    )
    np.testing.assert_allclose(
        start_axes.lines[0].get_ydata(),
        [1.0, 2.6, 2.0],
    )

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data_ref"] == "series-data"
    assert series["x_column"] == "q"
    assert series["y_column"] == "intensity"
    assert series["data"]["x"] == [1.0, 2.4, 3.0]
    assert series["data"]["y"] == [1.0, 2.6, 2.0]
    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:series-marked"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.4, 2.6], [3.0, 2.0]],
    )

    with series_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[1]["q"] == "2.0"
    assert rows[1]["intensity"] == "3.0"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_scatter_series_handle_drag_uses_default_point_handles(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-drag",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:series-scatter"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.0, 3.0], [3.0, 2.0]],
    )

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 3.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.3, 2.4))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    scatter_artists = [
        artist
        for artist in start_axes.collections
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
    ]
    assert len(scatter_artists) == 1
    np.testing.assert_allclose(
        scatter_artists[0].get_offsets(),
        [[1.0, 1.0], [2.3, 2.4], [3.0, 2.0]],
    )
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.3, 2.4], [3.0, 2.0]],
    )
    current_handle_artists = [
        artist
        for artist in start_axes.collections
        if artist.get_gid() == "pn-current-handle:series-scatter"
    ]
    assert len(current_handle_artists) == 1
    np.testing.assert_allclose(
        current_handle_artists[0].get_offsets(),
        [[2.3, 2.4]],
    )

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.3, 3.0]
    assert series["data"]["y"] == [1.0, 2.4, 2.0]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_direct_press_on_selected_large_scatter_handle_keeps_marker_hit_slop(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-selected-large-marker-press-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-selected-large-marker-press-drag",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 18.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)

    start_axes = editor._figure.axes[0]
    point_xpix, point_ypix = start_axes.transData.transform((2.0, 3.0))
    press_xpix = float(point_xpix + 15.0)
    press_ypix = float(point_ypix)

    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        press_xpix,
        press_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.3, 2.4))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.3, 3.0]
    assert series["data"]["y"] == [1.0, 2.4, 2.0]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_direct_press_on_unselected_scatter_point_selects_and_drags_it(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-press-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-press-drag",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_figure_object_id == ""

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 3.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.35, 2.45))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.35, 3.0]
    assert series["data"]["y"] == [1.0, 2.45, 2.0]
    assert editor._selected_figure_object_id == "series-scatter"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"

    scatter_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
    ]
    assert len(scatter_artists) == 1
    np.testing.assert_allclose(
        scatter_artists[0].get_offsets(),
        [[1.0, 1.0], [2.35, 2.45], [3.0, 2.0]],
    )

    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:series-scatter"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[1.0, 1.0], [2.35, 2.45], [3.0, 2.0]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_selected_scatter_point_click_with_tiny_motion_does_not_drag(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-click-threshold.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-click-threshold",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._object_list.setCurrentRow(1)
    assert editor._selected_figure_object_id == "series-scatter"

    axes = editor._figure.axes[0]
    start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = axes
    editor._on_generated_button_press(press_event)

    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        start_xpix + 1.0,
        start_ypix + 1.0,
        button=1,
    )
    move_event.inaxes = axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        start_xpix + 1.0,
        start_ypix + 1.0,
        button=1,
    )
    release_event.inaxes = axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.0, 3.0]
    assert series["data"]["y"] == [1.0, 3.0, 2.0]
    assert editor._selected_figure_object_id == "series-scatter"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"

    scatter_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
    ]
    assert len(scatter_artists) == 1
    np.testing.assert_allclose(
        scatter_artists[0].get_offsets(),
        [[1.0, 1.0], [2.0, 3.0], [3.0, 2.0]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_tiny_motion_on_scatter_point_selects_without_dragging(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-real-click-threshold.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-real-click-threshold",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonPress,
        start_xpix,
        start_ypix,
        button=Qt.LeftButton,
        buttons=Qt.LeftButton,
    )
    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseMove,
        start_xpix + 1.0,
        start_ypix + 1.0,
        buttons=Qt.LeftButton,
    )
    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonRelease,
        start_xpix + 1.0,
        start_ypix + 1.0,
        button=Qt.LeftButton,
    )

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.0, 3.0]
    assert series["data"]["y"] == [1.0, 3.0, 2.0]
    assert editor._selected_figure_object_id == "series-scatter"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"
    _assert_selected_status(editor, "Plot Series: Scatter")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_click_on_other_endpoint_of_selected_line_moves_current_endpoint_emphasis(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-retarget-current-endpoint.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-retarget-current-endpoint",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        first_xpix, first_ypix = axes.transData.transform((1.0, 1.0))
        _send_matplotlib_canvas_click(editor._canvas, first_xpix, first_ypix)

        assert editor._selected_figure_object_id == "guide-line"
        first_current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:guide-line"
        ]
        assert len(first_current_handle_artists) == 1
        np.testing.assert_allclose(
            first_current_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )

        second_xpix, second_ypix = axes.transData.transform((3.0, 2.0))
        _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

        assert editor._selected_figure_object_id == "guide-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "guide-line"
        second_current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:guide-line"
        ]
        assert len(second_current_handle_artists) == 1
        np.testing.assert_allclose(
            second_current_handle_artists[0].get_offsets(),
            [[3.0, 2.0]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_updates_status_hint_for_scatter_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-real-hover-status.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-real-hover-status",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "scatter" in hint
        assert "drag" in hint
        assert editor._hovered_figure_object_id == "series-scatter"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_selected_scatter_point_shows_drag_hint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-selected-hover-status.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-selected-hover-status",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-scatter"
        _assert_selected_status(editor, "Plot Series: Scatter")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert editor._hovered_figure_object_id == ""
        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-scatter"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Scatter",
        )

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        _send_matplotlib_canvas_move(editor._canvas, away_xpix, away_ypix)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-scatter"
        ]
        assert cleared_preview_handle_artists == []
        _assert_selected_status(editor, "Plot Series: Scatter")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_scatter_point_hover_and_click_selects_scatter(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-real-near-point-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-real-near-point-click",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        hover_xpix = float(point_xpix + 13.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "series-scatter"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        hint = editor._status_label.text().lower()
        assert "scatter" in hint
        assert "drag" in hint

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-scatter"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"
        assert editor._selected_object_label.text() == "Plot Series: Scatter"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Plot Series: Scatter")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_from_scatter_point_does_not_select_scatter(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-real-far-point-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-real-far-point-click",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        hover_xpix = float(point_xpix + 20.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_large_scatter_marker_hover_and_click_selects_scatter(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-real-large-marker-near-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-real-large-marker-near-click",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 18.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        hover_xpix = float(point_xpix + 15.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "series-scatter"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        hint = editor._status_label.text().lower()
        assert "scatter" in hint
        assert "drag" in hint

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-scatter"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"
        _assert_selected_status(editor, "Plot Series: Scatter")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_large_scatter_marker_click_selects_hovered_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-real-large-marker-hover-click-consistency.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-real-large-marker-hover-click-consistency",
            objects=[
                {
                    "id": "series-scatter-a",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter A",
                    "data": {"x": [1.0], "y": [2.0]},
                    "style": {"marker_size": 18.0, "color": "#0072B2"},
                },
                {
                    "id": "series-scatter-b",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter B",
                    "data": {"x": [3.0], "y": [2.0]},
                    "style": {"marker_size": 18.0, "color": "#D55E00"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((3.0, 2.0))
        hover_xpix = float(point_xpix + 15.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "series-scatter-b"
        hint = editor._status_label.text().lower()
        assert "scatter b" in hint

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-scatter-b"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter-b"
        assert editor._selected_object_label.text() == "Plot Series: Scatter B"

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_from_large_scatter_marker_does_not_select_scatter(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-real-large-marker-far-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-real-large-marker-far-click",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 18.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        hover_xpix = float(point_xpix + 24.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_blank_canvas_click_clears_selected_scatter_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-blank-real-click.png"
        figure_path.parent.mkdir()
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-blank-real-click",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, point_xpix, point_ypix)

        assert editor._selected_figure_object_id == "series-scatter"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"
        _assert_selected_status(editor, "Plot Series: Scatter")

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_scatter_drag_updates_point_geometry_feedback(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-real-geometry-feedback.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-real-geometry-feedback",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
    move_xpix, move_ypix = axes.transData.transform((2.35, 2.45))

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonPress,
        start_xpix,
        start_ypix,
        button=Qt.LeftButton,
        buttons=Qt.LeftButton,
    )

    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"
    assert editor._annotation_w_label.text() == ""
    assert editor._annotation_h_label.text() == ""
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseMove,
        move_xpix,
        move_ypix,
        buttons=Qt.LeftButton,
    )

    assert round(editor._annotation_x_spin.value(), 4) == 2.35
    assert round(editor._annotation_y_spin.value(), 4) == 2.45
    assert editor._status_label.text() == tr(
        "EDITOR_DRAG_STATUS_POINT",
        "Plot Series: Scatter",
        "2.35",
        "2.45",
    )

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonRelease,
        move_xpix,
        move_ypix,
        button=Qt.LeftButton,
    )

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.35, 3.0]
    assert series["data"]["y"] == [1.0, 2.45, 2.0]

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_controls_edit_selected_scatter_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-geometry-controls.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-geometry-controls",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
    _send_matplotlib_canvas_click(editor._canvas, start_xpix, start_ypix)

    assert editor._selected_figure_object_id == "series-scatter"
    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"
    assert editor._annotation_w_label.text() == ""
    assert editor._annotation_h_label.text() == ""
    assert editor._annotation_x_spin.isEnabled() is True
    assert editor._annotation_y_spin.isEnabled() is True
    assert editor._annotation_w_spin.isEnabled() is False
    assert editor._annotation_h_spin.isEnabled() is False
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    editor._annotation_x_spin.setValue(2.25)
    editor._annotation_y_spin.setValue(2.75)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.25, 3.0]
    assert series["data"]["y"] == [1.0, 2.75, 2.0]

    scatter_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
    ]
    assert len(scatter_artists) == 1
    np.testing.assert_allclose(
        scatter_artists[0].get_offsets(),
        [[1.0, 1.0], [2.25, 2.75], [3.0, 2.0]],
    )

    assert round(editor._annotation_x_spin.value(), 4) == 2.25
    assert round(editor._annotation_y_spin.value(), 4) == 2.75

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_controls_edit_selected_line_series_point_from_real_canvas_click(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-geometry-controls.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-geometry-controls",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
    click_xpix = float(
        segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
    )
    click_ypix = float(
        segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
    )
    _send_matplotlib_canvas_click(editor._canvas, click_xpix, click_ypix)

    assert editor._selected_figure_object_id == "series-line"
    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"
    assert editor._annotation_w_label.text() == ""
    assert editor._annotation_h_label.text() == ""
    assert editor._annotation_x_spin.isEnabled() is True
    assert editor._annotation_y_spin.isEnabled() is True
    assert editor._annotation_w_spin.isEnabled() is False
    assert editor._annotation_h_spin.isEnabled() is False
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    editor._annotation_x_spin.setValue(2.25)
    editor._annotation_y_spin.setValue(2.75)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.25, 3.0]
    assert series["data"]["y"] == [1.0, 2.75, 2.0]

    line_artists = [
        artist
        for artist in editor._figure.axes[0].lines
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
    ]
    assert len(line_artists) == 1
    np.testing.assert_allclose(
        line_artists[0].get_xdata(),
        [1.0, 2.25, 3.0],
    )
    np.testing.assert_allclose(
        line_artists[0].get_ydata(),
        [1.0, 2.75, 2.0],
    )

    assert round(editor._annotation_x_spin.value(), 4) == 2.25
    assert round(editor._annotation_y_spin.value(), 4) == 2.75

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_tiny_motion_on_line_series_body_selects_without_dragging(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-real-click-threshold.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-real-click-threshold",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
    click_xpix = float(
        segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
    )
    click_ypix = float(
        segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
    )

    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonPress,
        click_xpix,
        click_ypix,
        button=Qt.LeftButton,
        buttons=Qt.LeftButton,
    )
    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseMove,
        click_xpix + 1.0,
        click_ypix + 1.0,
        buttons=Qt.LeftButton,
    )
    _send_matplotlib_canvas_mouse_event(
        editor._canvas,
        QEvent.MouseButtonRelease,
        click_xpix + 1.0,
        click_ypix + 1.0,
        button=Qt.LeftButton,
    )

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.0, 3.0]
    assert series["data"]["y"] == [1.0, 3.0, 2.0]
    assert editor._selected_figure_object_id == "series-line"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"
    assert round(editor._annotation_x_spin.value(), 4) == 2.0
    assert round(editor._annotation_y_spin.value(), 4) == 3.0

    line_artists = [
        artist
        for artist in editor._figure.axes[0].lines
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
    ]
    assert len(line_artists) == 1
    np.testing.assert_allclose(
        line_artists[0].get_xdata(),
        [1.0, 2.0, 3.0],
    )
    np.testing.assert_allclose(
        line_artists[0].get_ydata(),
        [1.0, 3.0, 2.0],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_blank_canvas_click_clears_selected_line_series_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-real-blank-deselect.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-real-blank-deselect",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
    click_xpix = float(
        segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
    )
    click_ypix = float(
        segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
    )
    _send_matplotlib_canvas_click(editor._canvas, click_xpix, click_ypix)

    assert editor._selected_figure_object_id == "series-line"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
    assert editor._selected_generated_plot_series_object_id == "series-line"
    assert editor._selected_generated_plot_series_handle_index == 1

    _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
    assert editor._selected_generated_plot_series_object_id == ""
    assert editor._selected_generated_plot_series_handle_index is None

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_blank_canvas_click_clears_hover_feedback_after_hovering_other_object(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-real-blank-clears-hover-feedback.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-real-blank-clears-hover-feedback",
            objects=[
                {
                    "id": "guide-a",
                    "type": "line",
                    "name": "Guide A",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                },
                {
                    "id": "guide-b",
                    "type": "line",
                    "name": "Guide B",
                    "x1": 1.0,
                    "y1": 2.0,
                    "x2": 3.0,
                    "y2": 3.0,
                    "style": {"line_width": 1.2},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "guide-a"
        initial_cursor = editor._canvas.cursor().shape()

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 2.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hover_hint = editor._status_label.text().lower()
        assert "guide b" in hover_hint
        assert "endpoint" in hover_hint
        assert editor._hovered_figure_object_id == "guide-b"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        _send_matplotlib_canvas_click(editor._canvas, 5.0, 5.0)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_NONE")
        assert editor._hovered_figure_object_id == ""
        assert editor._canvas.cursor().shape() == initial_cursor
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        line_artists = {
            editor._figure_render_adapter.object_id_for_artist(artist): artist
            for artist in editor._figure.axes[0].lines
        }
        assert line_artists["guide-a"].get_path_effects() == []
        assert line_artists["guide-b"].get_path_effects() == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_direct_press_on_unselected_line_series_selects_and_drags_it(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-press-drag.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-press-drag",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_figure_object_id == ""

    start_axes = editor._figure.axes[0]
    start_xpix, start_ypix = start_axes.transData.transform((2.0, 3.0))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        start_xpix,
        start_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.35, 2.45))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.35, 3.0]
    assert series["data"]["y"] == [1.0, 2.45, 2.0]
    assert editor._selected_figure_object_id == "series-line"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"

    line_artists = [
        artist
        for artist in editor._figure.axes[0].lines
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
    ]
    assert len(line_artists) == 1
    np.testing.assert_allclose(
        line_artists[0].get_xdata(),
        [1.0, 2.35, 3.0],
    )
    np.testing.assert_allclose(
        line_artists[0].get_ydata(),
        [1.0, 2.45, 2.0],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_hover_updates_cursor_for_draggable_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-hover.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-hover",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    start_axes = editor._figure.axes[0]
    start_points = start_axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
    start_xpix = float(start_points[0][0] + 0.75 * (start_points[1][0] - start_points[0][0]))
    start_ypix = float(start_points[0][1] + 0.75 * (start_points[1][1] - start_points[0][1]))
    hover_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        start_xpix,
        start_ypix,
    )
    hover_event.inaxes = start_axes
    initial_cursor = editor._canvas.cursor().shape()
    editor._on_generated_mouse_move(hover_event)

    assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
    assert editor._selected_figure_object_id == ""

    away_xpix, away_ypix = start_axes.transData.transform((10.0, 10.0))
    away_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        away_xpix,
        away_ypix,
    )
    away_event.inaxes = start_axes
    editor._on_generated_mouse_move(away_event)

    assert editor._canvas.cursor().shape() == initial_cursor

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_hover_updates_cursor_for_line_endpoint_drag(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-endpoint-hover.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-endpoint-hover",
        objects=[
            {
                "id": "guide-line",
                "type": "line",
                "name": "Guide",
                "x1": 1.0,
                "y1": 1.0,
                "x2": 3.0,
                "y2": 2.0,
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.0))
    hover_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        hover_xpix,
        hover_ypix,
    )
    hover_event.inaxes = axes
    editor._on_generated_mouse_move(hover_event)

    assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
    assert editor._hovered_figure_object_id == "guide-line"
    assert editor._selected_figure_object_id == ""

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_hover_updates_cursor_for_scatter_point_drag(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-scatter-hover.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-scatter-hover",
        objects=[
            {
                "id": "series-scatter",
                "type": "plot_series",
                "chart_kind": "scatter",
                "name": "Scatter",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"marker_size": 8.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))
    hover_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        hover_xpix,
        hover_ypix,
    )
    hover_event.inaxes = axes
    editor._on_generated_mouse_move(hover_event)

    assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
    assert editor._hovered_figure_object_id == "series-scatter"
    assert editor._selected_figure_object_id == ""

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_generated_hover_updates_status_hint_for_image_grid_selection(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-image-grid-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        image_a = data_dir / "pattern_a.npy"
        image_b = data_dir / "pattern_b.npy"
        np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
        np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
        metadata_path = data_dir / "grid_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 0,
                    "strain_pct": 0.0,
                    "image_path": str(image_a),
                }
            )
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 1,
                    "strain_pct": 25.0,
                    "image_path": str(image_b),
                }
            )

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-image-grid-hover-status",
            data_sources=[
                {
                    "id": "grid-metadata",
                    "kind": "csv",
                    "path": str(metadata_path),
                    "role": "plot_data",
                }
            ],
            style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
            objects=[
                {
                    "id": "series-pattern-grid",
                    "type": "plot_series",
                    "chart_kind": "image_grid",
                    "name": "2D WAXS Pattern Grid",
                    "data_ref": "grid-metadata",
                    "row_column": "grid_row",
                    "column_column": "grid_col",
                    "image_path_column": "image_path",
                    "label_column": "strain_pct",
                    "style": {"colormap": "inferno"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        hover_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            hover_xpix,
            hover_ypix,
        )
        hover_event.inaxes = axes
        editor._on_generated_mouse_move(hover_event)

        hint = editor._status_label.text().lower()
        assert "2d waxs pattern grid" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-pattern-grid"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        away_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            away_xpix,
            away_ypix,
        )
        away_event.inaxes = axes
        editor._on_generated_mouse_move(away_event)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_updates_status_hint_for_image_grid_selection(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-image-grid-real-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        image_a = data_dir / "pattern_a.npy"
        image_b = data_dir / "pattern_b.npy"
        np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
        np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
        metadata_path = data_dir / "grid_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 0,
                    "strain_pct": 0.0,
                    "image_path": str(image_a),
                }
            )
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 1,
                    "strain_pct": 25.0,
                    "image_path": str(image_b),
                }
            )

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-image-grid-real-hover-status",
            data_sources=[
                {
                    "id": "grid-metadata",
                    "kind": "csv",
                    "path": str(metadata_path),
                    "role": "plot_data",
                }
            ],
            style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
            objects=[
                {
                    "id": "series-pattern-grid",
                    "type": "plot_series",
                    "chart_kind": "image_grid",
                    "name": "2D WAXS Pattern Grid",
                    "data_ref": "grid-metadata",
                    "row_column": "grid_row",
                    "column_column": "grid_col",
                    "image_path_column": "image_path",
                    "label_column": "strain_pct",
                    "style": {"colormap": "inferno"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((0.5, 0.5))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "2d waxs pattern grid" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-pattern-grid"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        _send_matplotlib_canvas_move(editor._canvas, away_xpix, away_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_image_grid_edge_hover_and_click_still_selects_grid(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-image-grid-edge-real-hover.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        image_a = data_dir / "pattern_a.npy"
        image_b = data_dir / "pattern_b.npy"
        np.save(image_a, np.array([[1.0, 2.0], [3.0, 4.0]]))
        np.save(image_b, np.array([[4.0, 3.0], [2.0, 1.0]]))
        metadata_path = data_dir / "grid_metadata.csv"
        with metadata_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["grid_row", "grid_col", "strain_pct", "image_path"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 0,
                    "strain_pct": 0.0,
                    "image_path": str(image_a),
                }
            )
            writer.writerow(
                {
                    "grid_row": 0,
                    "grid_col": 1,
                    "strain_pct": 25.0,
                    "image_path": str(image_b),
                }
            )

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-image-grid-edge-real-hover",
            data_sources=[
                {
                    "id": "grid-metadata",
                    "kind": "csv",
                    "path": str(metadata_path),
                    "role": "plot_data",
                }
            ],
            style={"layout": "image_grid", "colormap": "inferno", "origin": "lower"},
            objects=[
                {
                    "id": "series-pattern-grid",
                    "type": "plot_series",
                    "chart_kind": "image_grid",
                    "name": "2D WAXS Pattern Grid",
                    "data_ref": "grid-metadata",
                    "row_column": "grid_row",
                    "column_column": "grid_col",
                    "image_path_column": "image_path",
                    "label_column": "strain_pct",
                    "style": {"colormap": "inferno"},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        edge_xpix, edge_ypix = axes.transData.transform((1.5, 0.5))
        hover_xpix = edge_xpix + 5.0
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, edge_ypix)

        hint = editor._status_label.text().lower()
        assert "2d waxs pattern grid" in hint
        assert "click" in hint
        assert editor._hovered_figure_object_id == "series-pattern-grid"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.PointingHandCursor

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, edge_ypix)

        assert editor._selected_figure_object_id == "series-pattern-grid"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-pattern-grid"

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_generated_hover_updates_status_hint_for_line_endpoint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-endpoint-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-endpoint-hover-status",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.0))
        hover_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            hover_xpix,
            hover_ypix,
        )
        hover_event.inaxes = axes
        editor._on_generated_mouse_move(hover_event)

        hint = editor._status_label.text().lower()
        assert "guide" in hint
        assert "endpoint" in hint

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        away_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            away_xpix,
            away_ypix,
        )
        away_event.inaxes = axes
        editor._on_generated_mouse_move(away_event)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_generated_hover_status_for_line_series_body_mentions_nearest_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-hover-status",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        hover_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        hover_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )
        hover_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            hover_xpix,
            hover_ypix,
        )
        hover_event.inaxes = axes
        editor._on_generated_mouse_move(hover_event)

        hint = editor._status_label.text().lower()
        assert "line" in hint
        assert "nearest point" in hint

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_status_for_line_series_body_mentions_nearest_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-hover-status",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        hover_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        hover_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        hint = editor._status_label.text().lower()
        assert "line" in hint
        assert "nearest point" in hint
        assert editor._hovered_figure_object_id == "series-line"
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        _send_matplotlib_canvas_move(editor._canvas, away_xpix, away_ypix)

        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")
        assert editor._hovered_figure_object_id == ""

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_markerless_line_series_shows_nearest_point_preview(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-hover-preview-point.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-hover-preview-point",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        hover_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        hover_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        _send_matplotlib_canvas_move(editor._canvas, away_xpix, away_ypix)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert cleared_preview_handle_artists == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_markerless_line_series_point_shows_point_preview(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-hover-point-preview.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-hover-point-preview",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Line",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert cleared_preview_handle_artists == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_on_markerless_line_series_renders_selected_point_handle(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-selected-point-handle.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-selected-point-handle",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        click_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        click_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )
        _send_matplotlib_canvas_click(editor._canvas, click_xpix, click_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 1

        handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(handle_artists) == 1
        np.testing.assert_allclose(
            handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_selected_markerless_line_series_handle_drag_keeps_current_point_index(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-selected-handle-redrag.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-selected-handle-redrag",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        select_xpix, select_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, select_xpix, select_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 1

        press_event = MouseEvent(
            "button_press_event",
            editor._canvas,
            select_xpix,
            select_ypix,
            button=1,
        )
        press_event.inaxes = axes
        editor._on_generated_button_press(press_event)

        move_xpix, move_ypix = axes.transData.transform((2.4, 2.6))
        move_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            move_xpix,
            move_ypix,
            button=1,
        )
        move_event.inaxes = axes
        editor._on_generated_mouse_move(move_event)

        release_event = MouseEvent(
            "button_release_event",
            editor._canvas,
            move_xpix,
            move_ypix,
            button=1,
        )
        release_event.inaxes = axes
        editor._on_generated_button_release(release_event)

        document = load_figure_document(str(figure_path))
        series = document["objects"][0]
        assert series["data"]["x"] == [1.0, 2.4, 3.0]
        assert series["data"]["y"] == [1.0, 2.6, 2.0]

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_on_another_point_of_selected_line_series_retargets_current_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-retarget-current-point.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-retarget-current-point",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        first_xpix, first_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, first_xpix, first_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        second_xpix, second_ypix = axes.transData.transform((3.0, 2.0))
        _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 2
        assert round(editor._annotation_x_spin.value(), 4) == 3.0
        assert round(editor._annotation_y_spin.value(), 4) == 2.0

        handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(handle_artists) == 1
        np.testing.assert_allclose(
            handle_artists[0].get_offsets(),
            [[3.0, 2.0]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_on_another_segment_of_selected_line_series_retargets_current_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-retarget-current-point-from-segment.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-retarget-current-point-from-segment",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        first_xpix, first_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, first_xpix, first_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        pixel_points = axes.transData.transform([(2.0, 3.0), (3.0, 2.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        second_xpix = float(
            pixel_points[0][0] + 0.75 * (pixel_points[1][0] - pixel_points[0][0]) + normal_x * 6.0
        )
        second_ypix = float(
            pixel_points[0][1] + 0.75 * (pixel_points[1][1] - pixel_points[0][1]) + normal_y * 6.0
        )
        _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 2
        assert round(editor._annotation_x_spin.value(), 4) == 3.0
        assert round(editor._annotation_y_spin.value(), 4) == 2.0

        handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(handle_artists) == 1
        np.testing.assert_allclose(
            handle_artists[0].get_offsets(),
            [[3.0, 2.0]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_on_another_point_of_selected_scatter_retargets_current_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-retarget-current-point.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-retarget-current-point",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        first_xpix, first_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, first_xpix, first_ypix)

        assert editor._selected_figure_object_id == "series-scatter"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        second_xpix, second_ypix = axes.transData.transform((3.0, 2.0))
        _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

        assert editor._selected_figure_object_id == "series-scatter"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"
        assert editor._selected_generated_plot_series_handle_index == 2
        assert round(editor._annotation_x_spin.value(), 4) == 3.0
        assert round(editor._annotation_y_spin.value(), 4) == 2.0

        handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-scatter"
        ]
        assert len(handle_artists) == 1
        np.testing.assert_allclose(
            handle_artists[0].get_offsets(),
            [[1.0, 1.0], [2.0, 3.0], [3.0, 2.0]],
        )
        current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:series-scatter"
        ]
        assert len(current_handle_artists) == 1
        np.testing.assert_allclose(
            current_handle_artists[0].get_offsets(),
            [[3.0, 2.0]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_click_on_another_point_of_selected_marker_line_retargets_current_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-marker-line-retarget-current-point.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-marker-line-retarget-current-point",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2, "marker": "o", "marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        first_xpix, first_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, first_xpix, first_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        second_xpix, second_ypix = axes.transData.transform((3.0, 2.0))
        _send_matplotlib_canvas_click(editor._canvas, second_xpix, second_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 2
        assert round(editor._annotation_x_spin.value(), 4) == 3.0
        assert round(editor._annotation_y_spin.value(), 4) == 2.0

        current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:series-line"
        ]
        assert len(current_handle_artists) == 1
        np.testing.assert_allclose(
            current_handle_artists[0].get_offsets(),
            [[3.0, 2.0]],
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_selected_marker_line_uses_subtler_preview_than_current_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-marker-line-hover-weight.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-marker-line-hover-weight",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2, "marker": "o", "marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        first_xpix, first_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_click(editor._canvas, first_xpix, first_ypix)

        second_xpix, second_ypix = axes.transData.transform((3.0, 2.0))
        _send_matplotlib_canvas_move(editor._canvas, second_xpix, second_ypix)

        current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:series-line"
        ]
        hover_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert len(current_handle_artists) == 1
        assert len(hover_handle_artists) == 1
        assert float(hover_handle_artists[0].get_sizes()[0]) < float(
            current_handle_artists[0].get_sizes()[0]
        )
        np.testing.assert_allclose(
            current_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        np.testing.assert_allclose(
            hover_handle_artists[0].get_offsets(),
            [[3.0, 2.0]],
        )
        assert editor._selected_generated_plot_series_handle_index == 1
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Line",
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_selected_line_series_body_shows_drag_hint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-selected-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-selected-hover-status",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-line"
        _assert_selected_status(editor, "Plot Series: Line")

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        hover_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        hover_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_NEAREST_POINT",
            "Plot Series: Line",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        _assert_selected_status(editor, "Plot Series: Line")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_object_list_selected_markerless_line_series_shows_nearest_point_preview(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-selected-hover-preview-point.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-selected-hover-preview-point",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 0
        assert round(editor._annotation_x_spin.value(), 4) == 1.0
        assert round(editor._annotation_y_spin.value(), 4) == 1.0

        selection_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(selection_handle_artists) == 1
        np.testing.assert_allclose(
            selection_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        hover_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        hover_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        selection_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(selection_handle_artists) == 1
        np.testing.assert_allclose(
            selection_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_NEAREST_POINT",
            "Plot Series: Line",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert cleared_preview_handle_artists == []
        _assert_selected_status(editor, "Plot Series: Line")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_object_list_selected_markerless_line_series_point_shows_point_preview(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-selected-hover-point-preview.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-selected-hover-point-preview",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._selected_generated_plot_series_handle_index == 0
        assert round(editor._annotation_x_spin.value(), 4) == 1.0
        assert round(editor._annotation_y_spin.value(), 4) == 1.0

        selection_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(selection_handle_artists) == 1
        np.testing.assert_allclose(
            selection_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        selection_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-selection-handles:series-line"
        ]
        assert len(selection_handle_artists) == 1
        np.testing.assert_allclose(
            selection_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Line",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert cleared_preview_handle_artists == []
        _assert_selected_status(editor, "Plot Series: Line")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_line_series_body_hover_and_click_selects_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-near-body-click.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-near-body-click",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 9.0)
        hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 9.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "series-line"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        hint = editor._status_label.text().lower()
        assert "line" in hint
        assert "nearest point" in hint

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._selected_object_label.text() == "Plot Series: Line"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Plot Series: Line")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_large_marker_line_series_hover_and_click_selects_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-large-marker-near-click.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-large-marker-near-click",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2, "marker": "o", "marker_size": 18.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        hover_xpix = float(point_xpix + 15.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "series-line"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        hint = editor._status_label.text().lower()
        assert "line" in hint
        assert "drag" in hint

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._selected_object_label.text() == "Plot Series: Line"
        _assert_selected_status(editor, "Plot Series: Line")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_from_large_marker_line_series_does_not_select_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-large-marker-far-click.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-large-marker-far-click",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2, "marker": "o", "marker_size": 18.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        point_xpix, point_ypix = axes.transData.transform((2.0, 3.0))
        hover_xpix = float(point_xpix + 24.0)
        hover_ypix = float(point_ypix)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_line_series_click_selects_hovered_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-hover-click-consistency.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-hover-click-consistency",
            objects=[
                {
                    "id": "series-line-a",
                    "type": "plot_series",
                    "name": "Line A",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2, "color": "#0072B2"},
                },
                {
                    "id": "series-line-b",
                    "type": "plot_series",
                    "name": "Line B",
                    "data": {"x": [4.0, 5.0, 6.0], "y": [2.0, 4.0, 3.0]},
                    "style": {"line_width": 1.2, "color": "#D55E00"},
                },
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(4.0, 2.0), (5.0, 4.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 9.0)
        hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 9.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "series-line-b"
        hint = editor._status_label.text().lower()
        assert "line b" in hint
        assert "nearest point" in hint

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "series-line-b"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line-b"
        assert editor._selected_object_label.text() == "Plot Series: Line B"

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_from_line_series_body_does_not_select_series(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-far-body-click.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-far-body-click",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 16.0)
        hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 16.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_selected_line_endpoint_shows_drag_hint(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-endpoint-selected-hover-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-endpoint-selected-hover-status",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)

        assert editor._selected_figure_object_id == "guide-line"
        _assert_selected_status(editor, "Line: Guide")

        axes = editor._figure.axes[0]
        hover_xpix, hover_ypix = axes.transData.transform((1.0, 1.0))
        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert editor._hovered_figure_object_id == ""
        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:guide-line"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_ENDPOINT",
            "Line: Guide",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:guide-line"
        ]
        assert cleared_preview_handle_artists == []
        _assert_selected_status(editor, "Line: Guide")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_hover_on_unselected_line_endpoint_shows_endpoint_preview(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-endpoint-hover-preview.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-endpoint-hover-preview",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.0, 1.0), (3.0, 2.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float(pixel_points[0][0] + normal_x * 13.0)
        hover_ypix = float(pixel_points[0][1] + normal_y * 13.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:guide-line"
        ]
        assert len(preview_handle_artists) == 1
        np.testing.assert_allclose(
            preview_handle_artists[0].get_offsets(),
            [[1.0, 1.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_ENDPOINT",
            "Line: Guide",
        )

        _send_matplotlib_canvas_move(editor._canvas, 5.0, 5.0)

        cleared_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:guide-line"
        ]
        assert cleared_preview_handle_artists == []

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_near_line_endpoint_hover_and_click_selects_line(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-endpoint-near-real-click.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-endpoint-near-real-click",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.0, 1.0), (3.0, 2.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float(pixel_points[0][0] + normal_x * 13.0)
        hover_ypix = float(pixel_points[0][1] + normal_y * 13.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == "guide-line"
        assert editor._selected_figure_object_id == ""
        assert editor._canvas.cursor().shape() == Qt.CursorShape.CrossCursor
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_ENDPOINT",
            "Line: Guide",
        )

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == "guide-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "guide-line"
        assert editor._selected_object_label.text() == "Line: Guide"
        assert editor._hovered_figure_object_id == ""
        _assert_selected_status(editor, "Line: Guide")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_far_from_line_endpoint_does_not_select_line(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-endpoint-far-real-click.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-endpoint-far-real-click",
            objects=[
                {
                    "id": "guide-line",
                    "type": "line",
                    "name": "Guide",
                    "x1": 1.0,
                    "y1": 1.0,
                    "x2": 3.0,
                    "y2": 2.0,
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        pixel_points = axes.transData.transform([(1.0, 1.0), (3.0, 2.0)])
        segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
        segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
        segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
        assert segment_length > 0.0
        normal_x = -segment_dy / segment_length
        normal_y = segment_dx / segment_length
        hover_xpix = float(pixel_points[0][0] + normal_x * 20.0)
        hover_ypix = float(pixel_points[0][1] + normal_y * 20.0)

        _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

        assert editor._hovered_figure_object_id == ""
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

        assert editor._selected_figure_object_id == ""
        assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
        assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_generated_drag_updates_status_hint_for_scatter_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-scatter-drag-status.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-scatter-drag-status",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

        axes = editor._figure.axes[0]
        start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
        press_event = MouseEvent(
            "button_press_event",
            editor._canvas,
            start_xpix,
            start_ypix,
            button=1,
        )
        press_event.inaxes = axes
        editor._on_generated_button_press(press_event)

        move_xpix, move_ypix = axes.transData.transform((2.35, 2.45))
        move_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            move_xpix,
            move_ypix,
            button=1,
        )
        move_event.inaxes = axes
        editor._on_generated_mouse_move(move_event)

        hint = editor._status_label.text().lower()
        assert "scatter" in hint
        assert "2.35" in hint
        assert "2.45" in hint

        release_event = MouseEvent(
            "button_release_event",
            editor._canvas,
            move_xpix,
            move_ypix,
            button=1,
        )
        release_event.inaxes = axes
        editor._on_generated_button_release(release_event)

        away_xpix, away_ypix = axes.transData.transform((10.0, 10.0))
        away_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            away_xpix,
            away_ypix,
        )
        away_event.inaxes = axes
        editor._on_generated_mouse_move(away_event)

        restored_hint = editor._status_label.text().lower()
        assert "selected" in restored_hint
        assert "scatter" in restored_hint

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_escape_key_cancels_generated_scatter_drag_and_restores_values(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-escape-cancel-drag.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-escape-cancel-drag",
            objects=[
                {
                    "id": "series-scatter",
                    "type": "plot_series",
                    "chart_kind": "scatter",
                    "name": "Scatter",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))
        editor._object_list.setCurrentRow(1)
        assert editor._selected_figure_object_id == "series-scatter"

        axes = editor._figure.axes[0]
        start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
        press_event = MouseEvent(
            "button_press_event",
            editor._canvas,
            start_xpix,
            start_ypix,
            button=1,
        )
        press_event.inaxes = axes
        editor._on_generated_button_press(press_event)

        move_xpix, move_ypix = axes.transData.transform((2.35, 2.45))
        move_event = MouseEvent(
            "motion_notify_event",
            editor._canvas,
            move_xpix,
            move_ypix,
            button=1,
        )
        move_event.inaxes = axes
        editor._on_generated_mouse_move(move_event)

        preview_geometry = editor._generated_handle_drag_state["preview_geometry"]
        assert preview_geometry["x_values"] == [1.0, 2.35, 3.0]
        assert preview_geometry["y_values"] == [1.0, 2.45, 2.0]
        assert editor._figure_document["objects"][0]["data"] == {
            "x": [1.0, 2.0, 3.0],
            "y": [1.0, 3.0, 2.0],
        }
        moved_scatter_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
        ]
        assert len(moved_scatter_artists) == 1
        np.testing.assert_allclose(
            moved_scatter_artists[0].get_offsets(),
            [[1.0, 1.0], [2.35, 2.45], [3.0, 2.0]],
        )

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._generated_handle_drag_state is None
        assert editor._selected_figure_object_id == "series-scatter"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-scatter"
        assert editor._status_label.text().lower().startswith("selected")
        restored_series = editor._figure_document["objects"][0]
        assert restored_series["data"]["x"] == [1.0, 2.0, 3.0]
        assert restored_series["data"]["y"] == [1.0, 3.0, 2.0]

        restored_document = load_figure_document(str(figure_path))
        persisted_series = restored_document["objects"][0]
        assert persisted_series["data"]["x"] == [1.0, 2.0, 3.0]
        assert persisted_series["data"]["y"] == [1.0, 3.0, 2.0]
        restored_scatter_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if editor._figure_render_adapter.object_id_for_artist(artist) == "series-scatter"
        ]
        assert len(restored_scatter_artists) == 1
        np.testing.assert_allclose(
            restored_scatter_artists[0].get_offsets(),
            [[1.0, 1.0], [2.0, 3.0], [3.0, 2.0]],
        )
        immediate_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-scatter"
        ]
        assert immediate_preview_handle_artists == []

        restore_hover_xpix, restore_hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(
            editor._canvas,
            restore_hover_xpix,
            restore_hover_ypix,
        )

        restored_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-scatter"
        ]
        assert len(restored_preview_handle_artists) == 1
        np.testing.assert_allclose(
            restored_preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Scatter",
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_real_canvas_escape_cancels_marker_line_series_drag_and_restores_values(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-marker-line-real-escape-cancel.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-marker-line-real-escape-cancel",
            objects=[
                {
                    "id": "series-marked",
                    "type": "plot_series",
                    "name": "Marked",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2, "marker": "o", "marker_size": 8.0},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        start_xpix, start_ypix = axes.transData.transform((2.0, 3.0))
        move_xpix, move_ypix = axes.transData.transform((2.35, 2.45))

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            start_xpix,
            start_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            move_xpix,
            move_ypix,
            buttons=Qt.LeftButton,
        )

        preview_geometry = editor._generated_handle_drag_state["preview_geometry"]
        assert preview_geometry["x_values"] == [1.0, 2.35, 3.0]
        assert preview_geometry["y_values"] == [1.0, 2.45, 2.0]
        assert editor._figure_document["objects"][0]["data"] == {
            "x": [1.0, 2.0, 3.0],
            "y": [1.0, 3.0, 2.0],
        }
        assert round(editor._annotation_x_spin.value(), 4) == 2.35
        assert round(editor._annotation_y_spin.value(), 4) == 2.45

        moved_line_artists = [
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "series-marked"
        ]
        assert len(moved_line_artists) == 1
        np.testing.assert_allclose(
            moved_line_artists[0].get_xdata(),
            [1.0, 2.35, 3.0],
        )
        np.testing.assert_allclose(
            moved_line_artists[0].get_ydata(),
            [1.0, 2.45, 2.0],
        )
        moved_current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:series-marked"
        ]
        assert len(moved_current_handle_artists) == 1
        np.testing.assert_allclose(
            moved_current_handle_artists[0].get_offsets(),
            [[2.35, 2.45]],
        )

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._generated_handle_drag_state is None
        assert editor._selected_figure_object_id == "series-marked"
        assert editor._selected_generated_plot_series_object_id == "series-marked"
        assert editor._selected_generated_plot_series_handle_index == 1
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-marked"
        assert editor._status_label.text().lower().startswith("selected")
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        restored_series = editor._figure_document["objects"][0]
        assert restored_series["data"]["x"] == [1.0, 2.0, 3.0]
        assert restored_series["data"]["y"] == [1.0, 3.0, 2.0]

        restored_document = load_figure_document(str(figure_path))
        persisted_series = restored_document["objects"][0]
        assert persisted_series["data"]["x"] == [1.0, 2.0, 3.0]
        assert persisted_series["data"]["y"] == [1.0, 3.0, 2.0]

        restored_line_artists = [
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "series-marked"
        ]
        assert len(restored_line_artists) == 1
        np.testing.assert_allclose(
            restored_line_artists[0].get_xdata(),
            [1.0, 2.0, 3.0],
        )
        np.testing.assert_allclose(
            restored_line_artists[0].get_ydata(),
            [1.0, 3.0, 2.0],
        )
        restored_current_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-current-handle:series-marked"
        ]
        assert len(restored_current_handle_artists) == 1
        np.testing.assert_allclose(
            restored_current_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        immediate_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-marked"
        ]
        assert immediate_preview_handle_artists == []

        restore_hover_xpix, restore_hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(
            editor._canvas,
            restore_hover_xpix,
            restore_hover_ypix,
        )

        restored_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-marked"
        ]
        assert len(restored_preview_handle_artists) == 1
        np.testing.assert_allclose(
            restored_preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Marked",
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_generated_hover_highlights_line_series_without_selecting_it(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-hover-highlight.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-hover-highlight",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    line_artist = next(
        artist
        for artist in editor._figure.axes[0].lines
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
    )
    assert line_artist.get_path_effects() == []
    assert editor._selected_figure_object_id == ""

    start_axes = editor._figure.axes[0]
    start_points = start_axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
    hover_xpix = float(start_points[0][0] + 0.75 * (start_points[1][0] - start_points[0][0]))
    hover_ypix = float(start_points[0][1] + 0.75 * (start_points[1][1] - start_points[0][1]))
    hover_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        hover_xpix,
        hover_ypix,
    )
    hover_event.inaxes = start_axes
    editor._on_generated_mouse_move(hover_event)

    assert line_artist.get_path_effects()
    assert editor._selected_figure_object_id == ""

    away_xpix, away_ypix = start_axes.transData.transform((10.0, 10.0))
    away_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        away_xpix,
        away_ypix,
    )
    away_event.inaxes = start_axes
    editor._on_generated_mouse_move(away_event)

    assert line_artist.get_path_effects() == []
    assert editor._selected_figure_object_id == ""

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_real_canvas_escape_cancels_line_series_drag_and_restores_values(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    previous = get_language()
    try:
        set_language("en")

        figure_path = tmp_path / "figures" / "generated-line-series-real-escape-cancel.png"
        figure_path.parent.mkdir(parents=True)
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(figure_path))

        save_generated_figure_document(
            str(figure_path),
            technique="waxs",
            figure_id="generated-line-series-real-escape-cancel",
            objects=[
                {
                    "id": "series-line",
                    "type": "plot_series",
                    "name": "Line",
                    "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                    "style": {"line_width": 1.2},
                }
            ],
        )

        editor = ChartEditor()
        editor.retranslate()
        editor.set_source_figure(str(figure_path))

        axes = editor._figure.axes[0]
        segment_points = axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
        start_xpix = float(
            segment_points[0][0] + 0.75 * (segment_points[1][0] - segment_points[0][0])
        )
        start_ypix = float(
            segment_points[0][1] + 0.75 * (segment_points[1][1] - segment_points[0][1])
        )
        move_xpix, move_ypix = axes.transData.transform((2.35, 2.45))

        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseButtonPress,
            start_xpix,
            start_ypix,
            button=Qt.LeftButton,
            buttons=Qt.LeftButton,
        )
        _send_matplotlib_canvas_mouse_event(
            editor._canvas,
            QEvent.MouseMove,
            move_xpix,
            move_ypix,
            buttons=Qt.LeftButton,
        )

        preview_geometry = editor._generated_handle_drag_state["preview_geometry"]
        assert preview_geometry["x_values"] == [1.0, 2.35, 3.0]
        assert preview_geometry["y_values"] == [1.0, 2.45, 2.0]
        assert editor._figure_document["objects"][0]["data"] == {
            "x": [1.0, 2.0, 3.0],
            "y": [1.0, 3.0, 2.0],
        }
        assert round(editor._annotation_x_spin.value(), 4) == 2.35
        assert round(editor._annotation_y_spin.value(), 4) == 2.45

        moved_line_artists = [
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
        ]
        assert len(moved_line_artists) == 1
        np.testing.assert_allclose(
            moved_line_artists[0].get_xdata(),
            [1.0, 2.35, 3.0],
        )
        np.testing.assert_allclose(
            moved_line_artists[0].get_ydata(),
            [1.0, 2.45, 2.0],
        )

        escape_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
        app.sendEvent(editor._canvas, escape_event)

        assert escape_event.isAccepted()
        assert editor._generated_handle_drag_state is None
        assert editor._selected_figure_object_id == "series-line"
        assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"
        assert editor._status_label.text().lower().startswith("selected")
        assert round(editor._annotation_x_spin.value(), 4) == 2.0
        assert round(editor._annotation_y_spin.value(), 4) == 3.0

        restored_series = editor._figure_document["objects"][0]
        assert restored_series["data"]["x"] == [1.0, 2.0, 3.0]
        assert restored_series["data"]["y"] == [1.0, 3.0, 2.0]

        restored_document = load_figure_document(str(figure_path))
        persisted_series = restored_document["objects"][0]
        assert persisted_series["data"]["x"] == [1.0, 2.0, 3.0]
        assert persisted_series["data"]["y"] == [1.0, 3.0, 2.0]

        restored_line_artists = [
            artist
            for artist in editor._figure.axes[0].lines
            if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
        ]
        assert len(restored_line_artists) == 1
        np.testing.assert_allclose(
            restored_line_artists[0].get_xdata(),
            [1.0, 2.0, 3.0],
        )
        np.testing.assert_allclose(
            restored_line_artists[0].get_ydata(),
            [1.0, 3.0, 2.0],
        )
        immediate_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert immediate_preview_handle_artists == []

        restore_hover_xpix, restore_hover_ypix = axes.transData.transform((2.0, 3.0))
        _send_matplotlib_canvas_move(
            editor._canvas,
            restore_hover_xpix,
            restore_hover_ypix,
        )

        restored_preview_handle_artists = [
            artist
            for artist in editor._figure.axes[0].collections
            if artist.get_gid() == "pn-hover-handle:series-line"
        ]
        assert len(restored_preview_handle_artists) == 1
        np.testing.assert_allclose(
            restored_preview_handle_artists[0].get_offsets(),
            [[2.0, 3.0]],
        )
        assert editor._status_label.text() == tr(
            "EDITOR_HOVER_HINT_DRAG_POINT",
            "Plot Series: Line",
        )

        editor.deleteLater()
        app.processEvents()
    finally:
        set_language(previous)


def test_chart_editor_direct_press_on_unselected_line_series_body_drags_nearest_point(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-line-series-body-press-drag.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-line-series-body-press-drag",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Line",
                "data": {"x": [1.0, 2.0, 3.0], "y": [1.0, 3.0, 2.0]},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_figure_object_id == ""

    start_axes = editor._figure.axes[0]
    start_points = start_axes.transData.transform([(1.0, 1.0), (2.0, 3.0)])
    press_xpix = float(start_points[0][0] + 0.75 * (start_points[1][0] - start_points[0][0]))
    press_ypix = float(start_points[0][1] + 0.75 * (start_points[1][1] - start_points[0][1]))
    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        press_xpix,
        press_ypix,
        button=1,
    )
    press_event.inaxes = start_axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = start_axes.transData.transform((2.35, 2.45))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = start_axes
    editor._on_generated_mouse_move(move_event)

    preview_axes = editor._figure.axes[0]
    preview_handle_artists = [
        artist
        for artist in preview_axes.collections
        if artist.get_gid() == "pn-selection-handles:series-line"
    ]
    assert len(preview_handle_artists) == 1
    np.testing.assert_allclose(
        preview_handle_artists[0].get_offsets(),
        [[2.35, 2.45]],
    )

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = start_axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == [1.0, 2.35, 3.0]
    assert series["data"]["y"] == [1.0, 2.45, 2.0]
    assert editor._selected_figure_object_id == "series-line"
    assert editor._object_list.currentItem().data(Qt.UserRole) == "series-line"

    line_artists = [
        artist
        for artist in editor._figure.axes[0].lines
        if editor._figure_render_adapter.object_id_for_artist(artist) == "series-line"
    ]
    assert len(line_artists) == 1
    np.testing.assert_allclose(
        line_artists[0].get_xdata(),
        [1.0, 2.35, 3.0],
    )
    np.testing.assert_allclose(
        line_artists[0].get_ydata(),
        [1.0, 2.45, 2.0],
    )
    handle_artists = [
        artist
        for artist in editor._figure.axes[0].collections
        if artist.get_gid() == "pn-selection-handles:series-line"
    ]
    assert len(handle_artists) == 1
    np.testing.assert_allclose(
        handle_artists[0].get_offsets(),
        [[2.35, 2.45]],
    )

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_dense_line_series_body_hit_does_not_activate_far_from_points(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-dense-line-series-hit.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    x_values = np.linspace(0.0, 1.0, 200).tolist()
    y_values = np.linspace(0.0, 1.0, 200).tolist()

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-dense-line-series-hit",
        objects=[
            {
                "id": "series-line",
                "type": "plot_series",
                "name": "Dense Line",
                "data": {"x": x_values, "y": y_values},
                "style": {"line_width": 1.2},
            }
        ],
    )

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    pixel_points = axes.transData.transform(
        [(x_values[100], y_values[100]), (x_values[101], y_values[101])]
    )
    segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
    segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
    segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
    assert segment_length > 0.0
    normal_x = -segment_dy / segment_length
    normal_y = segment_dx / segment_length
    hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 6.0)
    hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 6.0)

    initial_cursor = editor._canvas.cursor().shape()
    hover_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        hover_xpix,
        hover_ypix,
    )
    hover_event.inaxes = axes
    editor._on_generated_mouse_move(hover_event)

    assert editor._canvas.cursor().shape() == initial_cursor
    assert editor._hovered_figure_object_id == ""
    assert editor._selected_figure_object_id == ""

    press_event = MouseEvent(
        "button_press_event",
        editor._canvas,
        hover_xpix,
        hover_ypix,
        button=1,
    )
    press_event.inaxes = axes
    editor._on_generated_button_press(press_event)

    move_xpix, move_ypix = axes.transData.transform((0.8, 0.65))
    move_event = MouseEvent(
        "motion_notify_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    move_event.inaxes = axes
    editor._on_generated_mouse_move(move_event)

    release_event = MouseEvent(
        "button_release_event",
        editor._canvas,
        move_xpix,
        move_ypix,
        button=1,
    )
    release_event.inaxes = axes
    editor._on_generated_button_release(release_event)

    document = load_figure_document(str(figure_path))
    series = document["objects"][0]
    assert series["data"]["x"] == x_values
    assert series["data"]["y"] == y_values
    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_dense_marker_line_series_does_not_hover_or_select_far_from_visible_markers(
    tmp_path, monkeypatch
):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "generated-dense-marker-line-series-hit.png"
    figure_path.parent.mkdir(parents=True)
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    x_values = np.linspace(0.0, 1.0, 200).tolist()
    y_values = np.linspace(0.0, 1.0, 200).tolist()

    save_generated_figure_document(
        str(figure_path),
        technique="waxs",
        figure_id="generated-dense-marker-line-series-hit",
        objects=[
            {
                "id": "series-marked",
                "type": "plot_series",
                "name": "Dense Marked",
                "data": {"x": x_values, "y": y_values},
                "style": {"line_width": 1.2, "marker": "o", "marker_size": 2.0},
            }
        ],
    )

    editor = ChartEditor()
    editor.retranslate()
    editor.set_source_figure(str(figure_path))

    axes = editor._figure.axes[0]
    pixel_points = axes.transData.transform(
        [(x_values[100], y_values[100]), (x_values[101], y_values[101])]
    )
    segment_dx = float(pixel_points[1][0] - pixel_points[0][0])
    segment_dy = float(pixel_points[1][1] - pixel_points[0][1])
    segment_length = (segment_dx ** 2 + segment_dy ** 2) ** 0.5
    assert segment_length > 0.0
    normal_x = -segment_dy / segment_length
    normal_y = segment_dx / segment_length
    hover_xpix = float((pixel_points[0][0] + pixel_points[1][0]) / 2.0 + normal_x * 6.0)
    hover_ypix = float((pixel_points[0][1] + pixel_points[1][1]) / 2.0 + normal_y * 6.0)

    initial_cursor = editor._canvas.cursor().shape()
    _send_matplotlib_canvas_move(editor._canvas, hover_xpix, hover_ypix)

    assert editor._canvas.cursor().shape() == initial_cursor
    assert editor._hovered_figure_object_id == ""
    assert editor._selected_figure_object_id == ""
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

    _send_matplotlib_canvas_click(editor._canvas, hover_xpix, hover_ypix)

    assert editor._selected_figure_object_id == ""
    assert editor._object_list.currentItem().data(Qt.UserRole) == "__background__"
    assert editor._selected_object_label.text() == tr("EDITOR_OBJECT_BACKGROUND")
    assert editor._status_label.text() == tr("EDITOR_OBJECT_MODE_HINT")

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_controls_update_selected_object_position(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_text_annotation("Point", 20, 10)
    editor._annotation_canvas.select_annotation(annotation_id)

    assert round(editor._annotation_x_spin.value(), 4) == 0.25
    assert round(editor._annotation_y_spin.value(), 4) == 0.25

    editor._annotation_x_spin.setValue(0.5)
    editor._annotation_y_spin.setValue(0.75)

    annotation = editor._annotation_canvas.annotation_state()[0]
    assert annotation["x"] == 0.5
    assert annotation["y"] == 0.75

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_canvas_move_refreshes_geometry_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_text_annotation("Point", 20, 10)
    editor._annotation_canvas.select_annotation(annotation_id)

    item = next(
        item for item in editor._annotation_canvas._scene.items()
        if item.data(0) == annotation_id
    )
    item.moveBy(20, 10)
    viewport = editor._annotation_canvas._view.viewport()
    release = QMouseEvent(
        QEvent.MouseButtonRelease,
        QPointF(0, 0),
        QPointF(0, 0),
        QPointF(viewport.mapToGlobal(viewport.rect().center())),
        Qt.LeftButton,
        Qt.NoButton,
        Qt.NoModifier,
    )
    app.sendEvent(viewport, release)
    app.processEvents()

    assert round(editor._annotation_x_spin.value(), 4) == 0.5
    assert round(editor._annotation_y_spin.value(), 4) == 0.5

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_size_controls_update_selected_rectangle(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_rectangle_annotation(10, 5, 30, 15)
    editor._annotation_canvas.select_annotation(annotation_id)

    assert round(editor._annotation_w_spin.value(), 4) == 0.3
    assert round(editor._annotation_h_spin.value(), 4) == 0.3

    editor._annotation_w_spin.setValue(0.6)
    editor._annotation_h_spin.setValue(0.5)

    annotation = editor._annotation_canvas.annotation_state()[0]
    assert annotation["width"] == 0.6
    assert annotation["height"] == 0.5

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_controls_update_selected_arrow_endpoints(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    annotation_id = editor._annotation_canvas.add_arrow_annotation(10, 5, 40, 20)
    editor._annotation_canvas.select_annotation(annotation_id)

    assert round(editor._annotation_x_spin.value(), 4) == 0.1
    assert round(editor._annotation_y_spin.value(), 4) == 0.1
    assert round(editor._annotation_w_spin.value(), 4) == 0.4
    assert round(editor._annotation_h_spin.value(), 4) == 0.4

    editor._annotation_x_spin.setValue(0.2)
    editor._annotation_y_spin.setValue(0.3)
    editor._annotation_w_spin.setValue(0.8)
    editor._annotation_h_spin.setValue(0.9)

    annotation = editor._annotation_canvas.annotation_state()[0]
    assert annotation["x1"] == 0.2
    assert annotation["y1"] == 0.3
    assert annotation["x2"] == 0.8
    assert annotation["y2"] == 0.9

    editor.deleteLater()
    app.processEvents()


def test_chart_editor_geometry_labels_follow_selected_object_type(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("POLYNEXUS_USER_CONFIG_DIR", str(tmp_path / "user_config"))

    figure_path = tmp_path / "figures" / "source.png"
    figure_path.parent.mkdir()
    pixmap = QPixmap(100, 50)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))

    text_id = editor._annotation_canvas.add_text_annotation("Point", 20, 10)
    editor._annotation_canvas.select_annotation(text_id)
    assert editor._annotation_x_label.text() == "X"
    assert editor._annotation_y_label.text() == "Y"

    rect_id = editor._annotation_canvas.add_rectangle_annotation(10, 5, 30, 15)
    editor._annotation_canvas.select_annotation(rect_id)
    assert editor._annotation_w_label.text() == "W"
    assert editor._annotation_h_label.text() == "H"

    arrow_id = editor._annotation_canvas.add_arrow_annotation(10, 5, 40, 20)
    editor._annotation_canvas.select_annotation(arrow_id)
    assert editor._annotation_x_label.text() == "X1"
    assert editor._annotation_y_label.text() == "Y1"
    assert editor._annotation_w_label.text() == "X2"
    assert editor._annotation_h_label.text() == "Y2"

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
