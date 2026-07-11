import os
import sys
from types import ModuleType
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.gui.i18n import tr
from polynexus.gui.plot_gallery_service import (
    FIGURE_CATEGORY_PER_FRAME,
    FIGURE_CATEGORY_SERIES_OVERVIEW,
    FigureGalleryEntry,
)
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


def test_chart_viewer_jsonable_propagates_unexpected_runtime_errors():
    app = QApplication.instance() or QApplication([])
    viewer = ChartViewer()

    class Broken:
        def item(self):
            raise RuntimeError("boom")

    try:
        with pytest.raises(RuntimeError, match="boom"):
            viewer._jsonable(Broken())
    finally:
        viewer.deleteLater()
        app.processEvents()


def test_chart_viewer_populate_data_table_propagates_unexpected_runtime_errors():
    app = QApplication.instance() or QApplication([])
    viewer = ChartViewer()

    try:
        with pytest.raises(RuntimeError, match="boom"):
            with patch.object(viewer, "_normalize_data_to_table", side_effect=RuntimeError("boom")):
                viewer._populate_data_table({"rows": []})
    finally:
        viewer.deleteLater()
        app.processEvents()


def test_chart_viewer_export_csv_propagates_unexpected_runtime_errors(tmp_path):
    app = QApplication.instance() or QApplication([])
    viewer = ChartViewer()
    viewer._full_data_headers = ["name"]
    viewer._full_data_rows = [["alpha"]]

    class BrokenWriter:
        def writerow(self, row):
            raise RuntimeError("boom")

        def writerows(self, rows):
            raise RuntimeError("boom")

    try:
        with patch("polynexus.gui.widgets.chart_viewer.QFileDialog.getSaveFileName", return_value=(str(tmp_path / "data.csv"), "CSV Files (*.csv)")):
            with patch("polynexus.gui.widgets.chart_viewer.csv.writer", return_value=BrokenWriter()):
                with pytest.raises(RuntimeError, match="boom"):
                    viewer._export_data_csv()
    finally:
        viewer.deleteLater()
        app.processEvents()


def test_chart_viewer_pdf_close_errors_are_not_swallowed():
    app = QApplication.instance() or QApplication([])
    preview = FigureFilePreview(show_edit_button=False)

    class BrokenPdfDocument:
        def __init__(self, parent=None):
            self.parent = parent

        def load(self, filepath):
            return True

        def pageCount(self):
            return 0

        def close(self):
            raise AttributeError("boom")

    fake_module = ModuleType("PySide6.QtPdf")
    fake_module.QPdfDocument = BrokenPdfDocument

    try:
        with patch.dict(sys.modules, {"PySide6.QtPdf": fake_module}):
            with pytest.raises(AttributeError, match="boom"):
                preview._render_pdf_first_page("fake.pdf")
    finally:
        preview.deleteLater()
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


def test_chart_gallery_load_files_groups_related_assets_into_one_card(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    png_path = figure_dir / "temperature_overview.png"
    svg_path = figure_dir / "temperature_overview.svg"
    pdf_path = figure_dir / "temperature_overview.pdf"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(png_path))
    svg_path.write_text("<svg width='80' height='40'></svg>", encoding="utf-8")
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Page /MediaBox [0 0 80 40] >>\nendobj\n"
    )
    save_generated_figure_document(
        str(svg_path),
        figure_id="temperature_overview",
        objects=[],
    )

    gallery = ChartGallery()
    gallery.load_files([str(png_path), str(svg_path), str(pdf_path)])
    app.processEvents()

    assert len(gallery._thumbnails) == 1
    assert gallery._thumbnails[0]._label.text() == "temperature overview"
    assert gallery._thumbnails[0]._state_badge.text() == tr("CHART_STATE_OBJECT")
    assert gallery._thumbnails[0]._btn_primary.text() == tr("CHART_BTN_CONTINUE_EDITING")
    assert gallery._thumbnails[0]._btn_secondary.text() == tr("CHART_BTN_VIEW_EXPORTS")
    assert set(gallery.figure_paths()) == {
        str(png_path.resolve()),
        str(svg_path.resolve()),
        str(pdf_path.resolve()),
    }

    gallery.deleteLater()
    app.processEvents()


def test_chart_gallery_category_filter_hides_non_matching_entries(tmp_path):
    app = QApplication.instance() or QApplication([])

    overview_path = tmp_path / "summary.png"
    frame_path = tmp_path / "frame.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(overview_path))
    assert pixmap.save(str(frame_path))

    gallery = ChartGallery()
    gallery.load_entries(
        [
            FigureGalleryEntry(
                figure_id="Fig_2_waterfall",
                title="Fig 2 waterfall",
                category=FIGURE_CATEGORY_SERIES_OVERVIEW,
                state="object_editing",
                preview_path=str(overview_path.resolve()),
                primary_path=str(overview_path.resolve()),
                editable_path=str(overview_path.resolve()),
                document_mode="object",
                asset_paths=(str(overview_path.resolve()),),
                assets=(),
            ),
            FigureGalleryEntry(
                figure_id="01_scattering",
                title="01 scattering",
                category=FIGURE_CATEGORY_PER_FRAME,
                state="static_background",
                preview_path=str(frame_path.resolve()),
                primary_path=str(frame_path.resolve()),
                editable_path=str(frame_path.resolve()),
                document_mode="static_background",
                asset_paths=(str(frame_path.resolve()),),
                assets=(),
            ),
        ]
    )

    gallery._category_combo.setCurrentIndex(
        gallery._category_combo.findData(FIGURE_CATEGORY_SERIES_OVERVIEW)
    )
    app.processEvents()

    assert [thumb.entry.figure_id for thumb in gallery._thumbnails] == ["Fig_2_waterfall"]

    gallery.deleteLater()
    app.processEvents()


def test_chart_gallery_select_figure_populates_secondary_asset_panel(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    png_path = figure_dir / "summary_panel.png"
    pdf_path = figure_dir / "summary_panel.pdf"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(png_path))
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Page /MediaBox [0 0 80 40] >>\nendobj\n"
    )

    gallery = ChartGallery()
    gallery.load_files([str(png_path), str(pdf_path)])
    gallery.select_figure(str(png_path), emit=False)
    app.processEvents()

    assert gallery._asset_group.isHidden() is False
    assert gallery._asset_group.title() == tr("CHART_ASSET_PANEL_TITLE")
    assert gallery._asset_layout.count() >= 2

    gallery.deleteLater()
    app.processEvents()


def test_chart_gallery_object_entry_primary_route_emits_entry_not_preview(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_dir = tmp_path / "figures"
    figure_dir.mkdir()
    png_path = figure_dir / "temperature_overview.png"
    svg_path = figure_dir / "temperature_overview.svg"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(png_path))
    svg_path.write_text("<svg width='80' height='40'></svg>", encoding="utf-8")
    save_generated_figure_document(
        str(svg_path),
        figure_id="temperature_overview",
        objects=[],
    )

    gallery = ChartGallery()
    gallery.load_files([str(png_path), str(svg_path)])
    preview_hits = []
    edit_hits = []
    gallery.figure_selected.connect(preview_hits.append)
    gallery.edit_requested.connect(edit_hits.append)

    gallery._thumbnails[0]._emit_primary_action()

    assert preview_hits == []
    assert len(edit_hits) == 1
    assert edit_hits[0].figure_id == "temperature_overview"
    assert edit_hits[0].editable_path == str(svg_path.resolve())

    gallery.deleteLater()
    app.processEvents()


def test_figure_file_preview_emits_entry_context_for_edit_requests(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "preview.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    preview = FigureFilePreview(show_edit_button=True)
    preview.load_figure(str(figure_path))
    entry = type(
        "Entry",
        (),
        {
            "state": "static_background",
            "title": "preview",
            "preview_path": str(figure_path),
            "editable_path": str(figure_path),
        },
    )()
    preview.set_entry_context(entry)
    edit_hits = []
    preview.edit_requested.connect(edit_hits.append)

    preview._emit_edit_requested()

    assert edit_hits == [entry]

    preview.deleteLater()
    app.processEvents()


def test_figure_file_preview_entry_context_updates_primary_action_label():
    app = QApplication.instance() or QApplication([])

    preview = FigureFilePreview(show_edit_button=True)
    preview.set_entry_context(
        type(
            "Entry",
            (),
            {
                "state": "static_background",
                "title": "temperature overview",
                "preview_path": "",
            },
        )()
    )

    assert preview._btn_edit.text() == tr("CHART_BTN_STATIC_ANNOTATE")

    preview.deleteLater()
    app.processEvents()
