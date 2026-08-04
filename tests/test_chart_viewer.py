import os
import sys
from types import ModuleType
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import QApplication

from polynexus.core.figure_document import save_generated_figure_document
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.figure_window_service import FigureDataResolution
from polynexus.gui.styles import C_ACCENT_WAXS
from polynexus.gui.theme import ThemeEngine
from polynexus.gui.plot_gallery_service import (
    FIGURE_CATEGORY_ALL,
    FIGURE_CATEGORY_PER_FRAME,
    FIGURE_CATEGORY_SERIES_OVERVIEW,
    FIGURE_ROLE_DIAGNOSTIC,
    FIGURE_ROLE_SI,
    FigureGalleryEntry,
)
from polynexus.gui.widgets.chart_viewer import (
    ChartGallery,
    ChartThumbnail,
    ChartViewer,
    FigureFilePreview,
)


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


def test_chart_viewer_reports_missing_source_without_replacing_preview(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "missing-source.png"
    pixmap = QPixmap(48, 32)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    viewer = ChartViewer()
    statuses = []
    viewer.status_message.connect(lambda message, level: statuses.append((message, level)))
    viewer.load_figure(
        str(figure_path),
        {"wrong": [99]},
        data_resolution=FigureDataResolution(error="source_missing"),
    )
    app.processEvents()

    assert viewer._preview.current_file() == str(figure_path)
    assert statuses[-1][1] == "warning"
    status_text = statuses[-1][0].lower()
    assert "data" in status_text or "数据" in statuses[-1][0]

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


def test_chart_thumbnail_rescales_image_to_fit_narrow_card(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "wide-gallery.png"
    pixmap = QPixmap(1200, 200)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    entry = FigureGalleryEntry(
        figure_id="wide-gallery",
        title="wide gallery",
        category=FIGURE_CATEGORY_SERIES_OVERVIEW,
        state="static_background",
        preview_path=str(figure_path.resolve()),
        primary_path=str(figure_path.resolve()),
        editable_path=str(figure_path.resolve()),
        document_mode="static_background",
        asset_paths=(str(figure_path.resolve()),),
        assets=(),
    )

    thumbnail = ChartThumbnail(entry)
    thumbnail.resize(240, 320)
    thumbnail.show()
    app.processEvents()

    pixmap = thumbnail._thumb.pixmap()
    assert pixmap is not None
    assert pixmap.width() <= thumbnail._thumb.contentsRect().width()
    assert pixmap.height() <= thumbnail._thumb.contentsRect().height()

    thumbnail.deleteLater()
    app.processEvents()


def test_chart_thumbnail_hover_border_moves_without_overriding_selection(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "hover-gallery.png"
    pixmap = QPixmap(120, 80)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))
    entry = FigureGalleryEntry(
        figure_id="hover-gallery",
        title="hover gallery",
        category=FIGURE_CATEGORY_SERIES_OVERVIEW,
        state="static_background",
        preview_path=str(figure_path.resolve()),
        primary_path=str(figure_path.resolve()),
        editable_path=str(figure_path.resolve()),
        document_mode="static_background",
        asset_paths=(str(figure_path.resolve()),),
        assets=(),
    )

    thumbnail = ChartThumbnail(entry)
    thumbnail.set_selected(True)
    thumbnail.enterEvent(None)
    hovered_style = thumbnail.styleSheet()
    thumbnail.leaveEvent(None)
    selected_style = thumbnail.styleSheet()

    assert C_ACCENT_WAXS in hovered_style
    assert C_ACCENT_WAXS not in selected_style
    assert ThemeEngine.instance().tokens.border_light in selected_style
    assert thumbnail._thumb.minimumHeight() >= 220
    assert thumbnail._selected is True
    assert thumbnail._hovered is False

    thumbnail.deleteLater()
    app.processEvents()


def test_chart_gallery_summary_text_tracks_visible_filtered_entries(tmp_path):
    app = QApplication.instance() or QApplication([])

    overview_path = tmp_path / "summary-overview.png"
    frame_path = tmp_path / "summary-frame.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(overview_path))
    assert pixmap.save(str(frame_path))

    gallery = ChartGallery()
    gallery.load_entries(
        [
            FigureGalleryEntry(
                figure_id="summary-overview",
                title="summary overview",
                category=FIGURE_CATEGORY_SERIES_OVERVIEW,
                state="static_background",
                preview_path=str(overview_path.resolve()),
                primary_path=str(overview_path.resolve()),
                editable_path=str(overview_path.resolve()),
                document_mode="static_background",
                asset_paths=(str(overview_path.resolve()),),
                assets=(),
            ),
            FigureGalleryEntry(
                figure_id="summary-frame",
                title="summary frame",
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
        gallery._category_combo.findData(FIGURE_CATEGORY_ALL)
    )
    app.processEvents()

    assert "2" in gallery.summary_text()

    gallery._category_combo.setCurrentIndex(
        gallery._category_combo.findData(FIGURE_CATEGORY_PER_FRAME)
    )
    app.processEvents()

    assert "1" in gallery.summary_text()

    gallery.deleteLater()
    app.processEvents()


def test_chart_gallery_toolbar_has_named_surface_and_borderless_scroll_area():
    app = QApplication.instance() or QApplication([])

    gallery = ChartGallery()

    assert gallery._toolbar_widget.objectName() == "gallery_toolbar"
    assert gallery._scroll.objectName() == "chart_gallery_scroll"
    assert "border: none" in gallery._scroll.styleSheet()

    gallery.deleteLater()
    app.processEvents()


def test_chart_gallery_retranslate_updates_filters_and_thumbnail_actions(tmp_path):
    app = QApplication.instance() or QApplication([])
    previous_language = get_language()

    figure_path = tmp_path / "retranslate-gallery.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    try:
        set_language("en")
        gallery = ChartGallery()
        gallery.load_files([str(figure_path)])
        set_language("zh")
        gallery.retranslate()

        assert gallery._category_label.text() == tr("CHART_CATEGORY_LABEL")
        assert gallery._role_label.text() == tr("CHART_ROLE_LABEL")
        assert gallery._category_combo.itemText(0) == tr("CHART_CATEGORY_ALL")
        assert gallery._role_combo.itemText(0) == tr("CHART_ROLE_ALL")
        assert gallery._thumbnails[0]._btn_copy.text() == tr("COMMON_COPY")
        assert gallery._thumbnails[0]._state_badge.text() == tr("CHART_STATE_STATIC")

        gallery.deleteLater()
        app.processEvents()
    finally:
        set_language(previous_language)


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


def test_chart_gallery_publication_role_filter_separates_si_and_diagnostics(tmp_path):
    app = QApplication.instance() or QApplication([])
    paths = []
    for name in ("main", "si", "diagnostic"):
        path = tmp_path / f"{name}.png"
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(path))
        paths.append(path)

    gallery = ChartGallery()
    gallery.load_entries(
        [
            FigureGalleryEntry(
                figure_id=name,
                title=name,
                category=FIGURE_CATEGORY_SERIES_OVERVIEW,
                state="object_editing",
                preview_path=str(path.resolve()),
                primary_path=str(path.resolve()),
                editable_path=str(path.resolve()),
                document_mode="object",
                asset_paths=(str(path.resolve()),),
                assets=(),
                publication_role=role,
            )
            for name, path, role in (
                ("main", paths[0], "main"),
                ("si", paths[1], FIGURE_ROLE_SI),
                ("diagnostic", paths[2], FIGURE_ROLE_DIAGNOSTIC),
            )
        ]
    )

    gallery._role_combo.setCurrentIndex(
        gallery._role_combo.findData(FIGURE_ROLE_SI)
    )
    app.processEvents()
    assert [thumb.entry.figure_id for thumb in gallery._thumbnails] == ["si"]

    gallery._role_combo.setCurrentIndex(
        gallery._role_combo.findData(FIGURE_ROLE_DIAGNOSTIC)
    )
    app.processEvents()
    assert [thumb.entry.figure_id for thumb in gallery._thumbnails] == ["diagnostic"]

    gallery.deleteLater()
    app.processEvents()


def test_chart_gallery_reflows_cards_without_horizontal_clipping(tmp_path):
    app = QApplication.instance() or QApplication([])
    paths = []
    for index in range(3):
        path = tmp_path / f"figure-{index}.png"
        pixmap = QPixmap(320, 180)
        pixmap.fill(QColor("white"))
        assert pixmap.save(str(path))
        paths.append(path)

    gallery = ChartGallery()
    gallery.resize(900, 640)
    gallery.show()
    gallery.load_entries(
        [
            FigureGalleryEntry(
                figure_id=f"figure-{index}",
                title=f"Figure {index}",
                category=FIGURE_CATEGORY_SERIES_OVERVIEW,
                state="static_background",
                preview_path=str(path.resolve()),
                primary_path=str(path.resolve()),
                editable_path=str(path.resolve()),
                document_mode="static_background",
                asset_paths=(str(path.resolve()),),
                assets=(),
            )
            for index, path in enumerate(paths)
        ]
    )
    app.processEvents()

    assert gallery._scroll.horizontalScrollBar().maximum() == 0
    assert gallery._thumbnails[2].mapTo(gallery, gallery._thumbnails[2].rect().topLeft()).y() > (
        gallery._thumbnails[0].mapTo(gallery, gallery._thumbnails[0].rect().topLeft()).y()
    )

    gallery.resize(1800, 640)
    app.processEvents()
    assert gallery._scroll.horizontalScrollBar().maximum() == 0
    assert gallery._thumbnails[2].mapTo(gallery, gallery._thumbnails[2].rect().topLeft()).y() == (
        gallery._thumbnails[0].mapTo(gallery, gallery._thumbnails[0].rect().topLeft()).y()
    )

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


def test_chart_gallery_double_click_passes_the_matching_entry_to_viewer(tmp_path):
    app = QApplication.instance() or QApplication([])

    figure_path = tmp_path / "entry-bound.png"
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(figure_path))

    gallery = ChartGallery()
    gallery.load_entries(
        [
            FigureGalleryEntry(
                figure_id="entry-bound",
                title="entry bound",
                category=FIGURE_CATEGORY_SERIES_OVERVIEW,
                state="static_background",
                preview_path=str(figure_path.resolve()),
                primary_path=str(figure_path.resolve()),
                editable_path=str(figure_path.resolve()),
                document_mode="static_background",
                asset_paths=(str(figure_path.resolve()),),
                assets=(),
            )
        ]
    )

    class _Viewer:
        def __init__(self):
            self.loaded = None

        def load_figure(self, filepath, *, entry=None):
            self.loaded = (filepath, entry)

        def show(self):
            pass

        def raise_(self):
            pass

    viewer = _Viewer()
    gallery._viewer = viewer
    gallery._open_viewer(str(figure_path.resolve()))

    assert viewer.loaded[0] == str(figure_path.resolve())
    assert viewer.loaded[1].figure_id == "entry-bound"

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
