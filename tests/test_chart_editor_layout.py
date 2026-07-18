import os
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.widgets.chart_editor import ChartEditor


def _app():
    return QApplication.instance() or QApplication([])


def _write_static_source(tmp_path):
    path = tmp_path / "figure.png"
    image = QImage(16, 16, QImage.Format_RGBA8888)
    image.fill(0xFFFFFFFF)
    assert image.save(str(path))
    return path


def test_editor_uses_canvas_first_inspector_layout():
    _app()
    editor = ChartEditor()

    assert editor._inspector_tabs.count() == 4
    assert [editor._inspector_tabs.tabText(i) for i in range(4)] == [
        tr("EDITOR_INSPECTOR_OBJECT"),
        tr("EDITOR_INSPECTOR_STYLE"),
        tr("EDITOR_INSPECTOR_ANNOTATION"),
        tr("EDITOR_INSPECTOR_EXPORT"),
    ]
    assert not editor._editor_header.isHidden()
    assert not editor._editor_status_bar.isHidden()

    editor.deleteLater()
    _app().processEvents()


def test_editor_keeps_canvas_usable_at_narrow_window_width():
    app = _app()
    editor = ChartEditor()
    editor.resize(640, 520)
    editor.show()
    app.processEvents()

    assert editor._editor_splitter.sizes()[0] >= 220

    editor.deleteLater()
    app.processEvents()


def test_context_toolbar_has_stable_actions_and_retranslates():
    _app()
    editor = ChartEditor()

    assert editor._editor_toolbar.action_ids() == [
        "select",
        "text",
        "line",
        "arrow",
        "rectangle",
        "undo",
        "redo",
        "export",
    ]

    previous = get_language()
    try:
        set_language("en")
        editor.retranslate()
        assert editor._editor_toolbar.action("select").text() == "Select"
        assert editor._editor_toolbar.action("export").text() == "Export"

        set_language("zh")
        editor.retranslate()
        assert editor._editor_toolbar.action("select").text() != "Select"
        assert editor._editor_toolbar.action("export").text() != "Export"
    finally:
        set_language(previous)
        editor.retranslate()

    editor.deleteLater()
    _app().processEvents()


def test_object_and_static_modes_update_header_and_inspector(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))
    assert editor._mode_badge.text() == tr("EDITOR_MODE_OBJECT")
    assert editor._inspector_tabs.currentIndex() == 0

    editor.set_source_figure(str(_write_static_source(tmp_path)))
    assert editor._mode_badge.text() == tr("EDITOR_MODE_STATIC")
    assert editor._inspector_tabs.currentIndex() == 2
    assert editor._source_title_label.text()

    editor.deleteLater()
    _app().processEvents()


def test_edit_marks_dirty_and_successful_save_clears_it(monkeypatch, tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))

    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")
    editor._on_grid_toggled(False)
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_UNSAVED")

    monkeypatch.setattr(
        editor,
        "_save_to_path",
        lambda path: editor.figure_saved.emit(str(path)),
    )
    editor._target_path = str(tmp_path / "figure.svg")
    editor.save_to_target()
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")

    editor.deleteLater()
    _app().processEvents()


def test_static_style_edit_marks_dirty(tmp_path):
    _app()
    editor = ChartEditor()
    editor.set_source_figure(str(_write_static_source(tmp_path)))
    assert editor._dirty_badge.text() == tr("EDITOR_STATE_SAVED")

    editor._title_edit.setText("Edited")
    _app().processEvents()

    assert editor._dirty_badge.text() == tr("EDITOR_STATE_UNSAVED")
    editor.deleteLater()
    _app().processEvents()


def test_disabling_grid_does_not_emit_matplotlib_warning():
    _app()
    editor = ChartEditor()
    editor.set_figure_generator(lambda axis: axis.plot([0, 1], [0, 1]))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        editor._on_grid_toggled(False)

    assert not any("grid() is false" in str(item.message) for item in caught)
    editor.deleteLater()
    _app().processEvents()


def test_refresh_clears_selection_when_selected_object_disappears(tmp_path):
    _app()
    figure_path = tmp_path / "generated.png"
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
                "data": {"x": [0.1, 0.2], "y": [1.0, 2.0]},
            }
        ],
    )
    editor = ChartEditor()
    editor.set_source_figure(str(figure_path))
    editor._refresh_object_list()
    editor._object_list.setCurrentRow(1)
    selected_id = editor._object_list.currentItem().data(Qt.UserRole)
    editor._generated_store().soft_delete(selected_id)
    editor._refresh_object_list()

    current = editor._object_list.currentItem()
    assert current is None or current.data(Qt.UserRole) == "__background__"
    assert editor._inspector_tabs.isEnabled()

    editor.deleteLater()
    _app().processEvents()


def test_layout_retranslates_tabs_header_and_accessible_names():
    _app()
    editor = ChartEditor()
    previous = get_language()
    try:
        set_language("en")
        editor.retranslate()
        assert editor._inspector_tabs.tabText(0) == "Object"
        assert editor._btn_header_save.text() == "Save Edits"
        assert editor._btn_header_export.text() == "Export"
        assert editor._status_label.accessibleName() == "Editor status"
        assert editor._inspector_tabs.accessibleName() == "Editor Inspector"
    finally:
        set_language(previous)
        editor.retranslate()

    editor.deleteLater()
    _app().processEvents()
