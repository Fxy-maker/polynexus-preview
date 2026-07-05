import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QApplication

from polynexus.gui.widgets.chart_viewer import ChartGallery, ChartViewer, FigureFilePreview


def test_chart_viewer_data_table_copy_shortcut_copies_selected_row():
    app = QApplication.instance() or QApplication([])

    viewer = ChartViewer()
    viewer._populate_data_table(
        [
            {"file": "a.csv", "value": 1.2},
            {"file": "b.csv", "value": 3.4},
        ]
    )

    viewer._data_table.selectRow(1)
    app.processEvents()
    viewer._data_copy_shortcut.activated.emit()

    lines = QApplication.clipboard().text().splitlines()
    assert lines[0] == "file\tvalue"
    assert lines[1] == "b.csv\t3.4"
    assert len(lines) == 2

    viewer.deleteLater()
    app.processEvents()


def test_chart_viewer_data_table_copy_button_copies_full_table_when_no_selection():
    app = QApplication.instance() or QApplication([])

    viewer = ChartViewer()
    viewer._populate_data_table(
        [
            {"file": "a.csv", "value": 1.2},
            {"file": "b.csv", "value": 3.4},
        ]
    )

    app.clipboard().clear()
    viewer._btn_copy_data.click()

    lines = QApplication.clipboard().text().splitlines()
    assert lines[0] == "file\tvalue"
    assert lines[1] == "a.csv\t1.2"
    assert lines[2] == "b.csv\t3.4"
    assert len(lines) == 3

    viewer.deleteLater()
    app.processEvents()


def test_figure_file_preview_copy_button_copies_loaded_path(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "preview.png"
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    preview = FigureFilePreview(show_edit_button=False)
    preview.load_figure(str(figure_path))

    app.processEvents()
    app.clipboard().clear()

    assert preview._btn_copy_path.isEnabled()
    preview._btn_copy_path.click()

    assert app.clipboard().text() == str(figure_path)

    preview.deleteLater()
    app.processEvents()


def test_chart_gallery_thumbnail_copy_button_copies_path(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "gallery.png"
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    gallery = ChartGallery()
    gallery.load_files([str(figure_path)])

    app.processEvents()
    app.clipboard().clear()

    assert gallery._thumbnails[0]._btn_copy.isEnabled()
    gallery._thumbnails[0]._btn_copy.click()

    assert app.clipboard().text() == str(figure_path)

    gallery.deleteLater()
    app.processEvents()
