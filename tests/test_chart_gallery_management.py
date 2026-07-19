from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from polynexus.gui.plot_gallery_service import (
    FIGURE_CATEGORY_SERIES_OVERVIEW,
    FIGURE_STATE_STATIC,
    FigureGalleryEntry,
)
from polynexus.gui.widgets.chart_viewer import ChartGallery, ChartThumbnail


def _entry(path, figure_id, *, working=0, published=0, status=""):
    resolved = str(path.resolve())
    return FigureGalleryEntry(
        figure_id=figure_id,
        title=figure_id.replace("-", " "),
        category=FIGURE_CATEGORY_SERIES_OVERVIEW,
        state=FIGURE_STATE_STATIC,
        preview_path=resolved,
        primary_path=resolved,
        editable_path=resolved,
        document_mode="static_background",
        asset_paths=(resolved,),
        assets=(),
        working_revision=working,
        published_revision=published,
        status=status,
    )


def _png(path):
    pixmap = QPixmap(80, 40)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(path))


def test_chart_gallery_search_filters_visible_cards(tmp_path):
    QApplication.instance() or QApplication([])
    first = tmp_path / "alpha.png"
    second = tmp_path / "peak.png"
    _png(first)
    _png(second)
    gallery = ChartGallery()
    gallery.load_entries([_entry(first, "alpha"), _entry(second, "peak-marker")])

    gallery._search_edit.setText("peak")
    QApplication.instance().processEvents()

    assert [item.entry.figure_id for item in gallery._thumbnails] == ["peak-marker"]
    gallery.deleteLater()


def test_chart_gallery_sort_by_title_reorders_cards(tmp_path):
    QApplication.instance() or QApplication([])
    first = tmp_path / "z.png"
    second = tmp_path / "a.png"
    _png(first)
    _png(second)
    gallery = ChartGallery()
    gallery.load_entries([_entry(first, "zulu"), _entry(second, "alpha")])

    gallery._sort_combo.setCurrentIndex(gallery._sort_combo.findData("title"))
    QApplication.instance().processEvents()

    assert [item.entry.figure_id for item in gallery._thumbnails] == ["alpha", "zulu"]
    gallery.deleteLater()


def test_chart_thumbnail_shows_revision_status(tmp_path):
    QApplication.instance() or QApplication([])
    path = tmp_path / "versioned.png"
    _png(path)
    thumbnail = ChartThumbnail(
        _entry(path, "versioned", working=3, published=2, status="ready")
    )

    assert "3" in thumbnail._version_badge.text()
    assert "2" in thumbnail._version_badge.text()
    thumbnail.deleteLater()


def test_chart_gallery_batch_export_copies_only_checked_cards(monkeypatch, tmp_path):
    QApplication.instance() or QApplication([])
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _png(first)
    _png(second)
    gallery = ChartGallery()
    gallery.load_entries([_entry(first, "first"), _entry(second, "second")])
    gallery._thumbnails[0]._batch_check.setChecked(True)
    destination = tmp_path / "exported"
    destination.mkdir()
    monkeypatch.setattr(
        "polynexus.gui.widgets.chart_viewer.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(destination),
    )

    gallery._export_selected()

    assert (destination / first.name).is_file()
    assert not (destination / second.name).exists()
    gallery.deleteLater()
