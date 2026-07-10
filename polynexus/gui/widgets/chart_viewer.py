"""Chart viewer widget for exported figure files in the Qt GUI.

Replaces the simple QListWidget file list in the Plots tab with
interactive exported-figure previews. Theme-aware chrome support.
"""

import logging
logger = logging.getLogger(__name__)

import csv
import json
import os
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QSizePolicy, QFileDialog, QComboBox,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGroupBox, QTabWidget, QTableWidget, QTableWidgetItem, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QTimer
from PySide6.QtGui import QPixmap, QPainter, QKeySequence, QShortcut

from ..styles import (
    C_TEXT_MUTED, C_ACCENT_WAXS,
)
from ..table_clipboard_service import copy_table_selection_to_clipboard
from ..theme import ThemeEngine
from ..plot_gallery_service import (
    FIGURE_CATEGORY_ALL,
    FIGURE_CATEGORY_OTHER_EXPORTS,
    FIGURE_CATEGORY_PER_FRAME,
    FIGURE_CATEGORY_SERIES_OVERVIEW,
    FIGURE_STATE_OBJECT,
    FIGURE_STATE_STATIC,
    FIGURE_STATE_UNLINKED_EXPORT,
    FigureGalleryEntry,
    build_plot_gallery_entries,
)
from ..i18n import tr
from ...core.engine import logger

class ChartThumbnail(QWidget):
    """Single chart preview thumbnail with click-to-zoom."""
    clicked = Signal(str)
    double_clicked = Signal(str)
    edit_clicked = Signal(object)
    open_clicked = Signal(str)
    copy_clicked = Signal(str)

    def __init__(self, entry: FigureGalleryEntry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.filepath = entry.preview_path
        self._selected = False
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(
            f"{entry.title}\n{_gallery_state_text(entry.state)}"
        )
        self.setMinimumWidth(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Thumbnail image
        self._thumb = QLabel()
        self._thumb.setAlignment(Qt.AlignCenter)
        self._thumb.setMinimumSize(300, 220)
        self._thumb.setMaximumSize(520, 340)
        self._thumb.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._thumb)

        self._state_badge = QLabel(_gallery_state_text(entry.state))
        self._state_badge.setObjectName("chart_state_badge")
        layout.addWidget(self._state_badge, 0, Qt.AlignLeft)

        self._label = QLabel(entry.title)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setObjectName("thumb_label")
        self._label.setWordWrap(True)
        layout.addWidget(self._label)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
        self._btn_primary = QPushButton(_gallery_primary_label(entry.state))
        self._btn_primary.clicked.connect(self._emit_primary_action)
        actions.addWidget(self._btn_primary)
        self._btn_secondary = QPushButton(_gallery_secondary_label(entry.state))
        self._btn_secondary.clicked.connect(self._emit_secondary_action)
        actions.addWidget(self._btn_secondary)
        self._btn_copy = QPushButton(tr("COMMON_COPY"))
        self._btn_copy.setToolTip(tr("IMPORT_SUGGESTION_COPY_PATH_TOOLTIP"))
        self._btn_copy.clicked.connect(lambda: self.copy_clicked.emit(self.filepath))
        actions.addWidget(self._btn_copy)
        layout.addLayout(actions)

        self._apply_style()
        self._load_thumbnail()

    def _apply_style(self):
        t = ThemeEngine.instance().tokens
        border = C_ACCENT_WAXS if self._selected else t.border_light
        border_width = 2 if self._selected else 1
        bg = t.bg_surface if self._hovered or self._selected else t.bg_card
        self._thumb.setStyleSheet(
            f"background: {bg}; border: {border_width}px solid {border}; "
            f"border-radius: {t.radius_lg}px; padding: 4px;"
        )
        self._label.setStyleSheet(
            f"color: {t.text_primary if self._selected else t.text_secondary}; "
            f"font-size: {t.font_size_sm2}px; font-weight: {600 if self._selected else 500}; "
            f"background: transparent; border: none;"
        )
        self._state_badge.setStyleSheet(
            f"color: {t.text_primary}; background: {t.bg_surface}; "
            f"border: 1px solid {border}; border-radius: {t.radius_sm}px; "
            f"padding: 2px 8px; font-size: {t.font_size_sm}px; font-weight: 600;"
        )

    def _load_thumbnail(self):
        """Load SVG/PNG as QPixmap thumbnail."""
        ext = os.path.splitext(self.filepath)[1].lower()

        if ext == '.svg':
            try:
                from PySide6.QtSvg import QSvgRenderer
                from PySide6.QtGui import QPainter
                renderer = QSvgRenderer(self.filepath)
                if renderer.isValid():
                    size = renderer.defaultSize()
                    w, h = size.width(), size.height()
                    scale = min(480 / w, 300 / h)
                    pixmap = QPixmap(int(w * scale), int(h * scale))
                    pixmap.fill(Qt.transparent)
                    painter = QPainter()
                    if painter.begin(pixmap):
                        try:
                            renderer.render(painter)
                        finally:
                            painter.end()
                    self._thumb.setPixmap(pixmap)
                    return
            except ImportError:
                pass

        pixmap = QPixmap(self.filepath)
        if not pixmap.isNull():
            scaled = pixmap.scaled(480, 300, Qt.KeepAspectRatio,
                                   Qt.SmoothTransformation)
            self._thumb.setPixmap(scaled)
        else:
            self._thumb.setText(tr("CHART_SVG_FALLBACK"))

    def _emit_primary_action(self):
        if self.entry.state in {FIGURE_STATE_OBJECT, FIGURE_STATE_STATIC} and self.entry.editable_path:
            self.edit_clicked.emit(self.entry)
            return
        self.clicked.emit(self.entry.preview_path)

    def _emit_secondary_action(self):
        self.clicked.emit(self.entry.preview_path)

    def mousePressEvent(self, event):
        if self.entry.state == FIGURE_STATE_OBJECT:
            self._emit_primary_action()
        else:
            self.clicked.emit(self.entry.preview_path)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.filepath)
        super().mouseDoubleClickEvent(event)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style()

    def enterEvent(self, event):
        self._hovered = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._apply_style()
        super().leaveEvent(event)

class FigureFilePreview(QWidget):
    """Zoomable preview for exported figure files."""

    edit_requested = Signal(object)
    view_requested = Signal(str)
    close_requested = Signal()

    def __init__(
        self,
        parent=None,
        show_edit_button=True,
        edit_label=None,
        show_close_button=False,
        show_view_button=False,
    ):
        super().__init__(parent)
        self.setObjectName("figure_preview")
        self._filepath = ""
        self._entry_context = None
        self._pixmap_item = None
        self._fit_mode = True
        self._zoom = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        self._btn_fit = QPushButton(tr("CHART_BTN_FIT"))
        self._btn_fit.clicked.connect(self.fit_to_window)
        toolbar.addWidget(self._btn_fit)

        self._btn_actual = QPushButton("100%")
        self._btn_actual.clicked.connect(self.actual_size)
        toolbar.addWidget(self._btn_actual)

        self._btn_zoom_out = QPushButton("-")
        self._btn_zoom_out.clicked.connect(lambda: self.zoom_by(0.85))
        toolbar.addWidget(self._btn_zoom_out)

        self._btn_zoom_in = QPushButton("+")
        self._btn_zoom_in.clicked.connect(lambda: self.zoom_by(1.18))
        toolbar.addWidget(self._btn_zoom_in)

        self._btn_refresh = QPushButton(tr("CHART_BTN_REFRESH"))
        self._btn_refresh.clicked.connect(self.refresh)
        toolbar.addWidget(self._btn_refresh)

        self._edit_label = edit_label or tr("CHART_BTN_EDIT_CURRENT")
        if show_edit_button:
            self._btn_edit = QPushButton(self._edit_label)
            self._btn_edit.setObjectName("primary_btn")
            self._btn_edit.clicked.connect(self._emit_edit_requested)
            toolbar.addWidget(self._btn_edit)
        else:
            self._btn_edit = None

        if show_view_button:
            self._btn_view = QPushButton(tr("CHART_BTN_STANDALONE"))
            self._btn_view.clicked.connect(self._emit_view_requested)
            toolbar.addWidget(self._btn_view)
        else:
            self._btn_view = None

        self._btn_open = QPushButton(tr("CHART_BTN_OPEN_FILE"))
        self._btn_open.clicked.connect(self._open_external)
        toolbar.addWidget(self._btn_open)

        self._btn_folder = QPushButton(tr("CHART_BTN_OPEN_FOLDER"))
        self._btn_folder.clicked.connect(self._open_folder)
        toolbar.addWidget(self._btn_folder)

        self._btn_copy_path = QPushButton(tr("COMMON_COPY"))
        self._btn_copy_path.setToolTip(tr("IMPORT_SUGGESTION_COPY_PATH_TOOLTIP"))
        self._btn_copy_path.clicked.connect(self._copy_path_to_clipboard)
        toolbar.addWidget(self._btn_copy_path)

        toolbar.addStretch()

        if show_close_button:
            self._btn_close = QPushButton(tr("CHART_BTN_CLOSE_PREVIEW"))
            self._btn_close.clicked.connect(self.close_requested.emit)
            toolbar.addWidget(self._btn_close)
        else:
            self._btn_close = None

        layout.addLayout(toolbar)

        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setAlignment(Qt.AlignCenter)
        self._view.setDragMode(QGraphicsView.ScrollHandDrag)
        self._view.setMinimumHeight(360)
        self._view.setRenderHints(
            QPainter.Antialiasing | QPainter.SmoothPixmapTransform
        )
        self._apply_chrome_style()
        self._view.viewport().installEventFilter(self)
        layout.addWidget(self._view, 1)

        self._status = QLabel(tr("CHART_STATUS_SELECT"))
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(f"color: {C_TEXT_MUTED}; padding: 6px;")
        layout.addWidget(self._status)
        self._apply_chrome_style()

        self._set_controls_enabled(False)
        ThemeEngine.instance().theme_changed.connect(
            lambda _name: self._apply_chrome_style()
        )
        self.retranslate()

    def _apply_chrome_style(self):
        t = ThemeEngine.instance().tokens
        self._view.setStyleSheet(
            "QGraphicsView {"
            f"  background-color: {t.bg_panel};"
            f"  border: 1px solid {t.border};"
            f"  border-radius: {t.radius_lg}px;"
            "}"
        )
        if hasattr(self, "_status"):
            self._status.setStyleSheet(
                f"color: {t.text_secondary}; padding: 6px;"
                "background: transparent; border: none;"
            )

    def retranslate(self):
        self._btn_fit.setText(tr("CHART_BTN_FIT"))
        self._btn_refresh.setText(tr("CHART_BTN_REFRESH"))
        self._btn_open.setText(tr("CHART_BTN_OPEN_FILE"))
        self._btn_folder.setText(tr("CHART_BTN_OPEN_FOLDER"))
        if self._btn_edit is not None:
            self._btn_edit.setText(self._edit_label)
        if self._btn_view is not None:
            self._btn_view.setText(tr("CHART_BTN_STANDALONE"))
        if self._btn_close is not None:
            self._btn_close.setText(tr("CHART_BTN_CLOSE_PREVIEW"))
        if self._pixmap_item is None:
            self._status.setText(tr("CHART_STATUS_SELECT"))

    def current_file(self):
        return self._filepath

    def set_entry_context(self, entry) -> None:
        self._entry_context = entry
        state = str(getattr(entry, "state", "") or "")
        if self._btn_edit is None:
            return
        if state == FIGURE_STATE_OBJECT:
            self._edit_label = tr("CHART_BTN_CONTINUE_EDITING")
        elif state == FIGURE_STATE_STATIC:
            self._edit_label = tr("CHART_BTN_STATIC_ANNOTATE")
        elif state == FIGURE_STATE_UNLINKED_EXPORT:
            self._edit_label = tr("CHART_BTN_OPEN_AS_STATIC")
        else:
            self._edit_label = tr("CHART_BTN_EDIT_CURRENT")
        self._btn_edit.setText(self._edit_label)

    def load_figure(self, filepath):
        self._filepath = filepath or ""
        if not self._filepath:
            self.clear()
            return

        pixmap = self._load_pixmap(self._filepath)
        if pixmap is None or pixmap.isNull():
            self.clear()
            self._status.setText(
                tr("CHART_STATUS_PREVIEW_FAILED", os.path.basename(self._filepath))
            )
            return

        self._scene.clear()
        self._pixmap_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(self._pixmap_item)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._status.setText(
            f"{os.path.basename(self._filepath)}  "
            f"{pixmap.width()} x {pixmap.height()} px"
        )
        self._set_controls_enabled(True)
        self.fit_to_window()
        QTimer.singleShot(0, self.fit_to_window)
        QTimer.singleShot(80, self.fit_to_window)

    def refresh(self):
        if self._filepath:
            self.load_figure(self._filepath)

    def clear(self):
        self._scene.clear()
        self._pixmap_item = None
        self._set_controls_enabled(False)
        self._status.setText(tr("CHART_STATUS_SELECT"))

    def fit_to_window(self):
        if self._pixmap_item is None:
            return
        rect = self._scene.itemsBoundingRect()
        if rect.isNull():
            return
        self._view.resetTransform()
        self._view.fitInView(rect, Qt.KeepAspectRatio)
        self._fit_mode = True
        self._zoom = 1.0

    def actual_size(self):
        if self._pixmap_item is None:
            return
        self._view.resetTransform()
        self._fit_mode = False
        self._zoom = 1.0

    def zoom_by(self, factor):
        if self._pixmap_item is None:
            return
        self._view.scale(factor, factor)
        self._zoom *= factor
        self._fit_mode = False

    def eventFilter(self, watched, event):
        if watched is self._view.viewport() and event.type() == QEvent.Resize:
            if self._fit_mode and self._pixmap_item is not None:
                self.fit_to_window()
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        if self._fit_mode and self._pixmap_item is not None:
            QTimer.singleShot(0, self.fit_to_window)

    def _set_controls_enabled(self, enabled):
        for btn in (
            self._btn_fit,
            self._btn_actual,
            self._btn_zoom_out,
            self._btn_zoom_in,
            self._btn_refresh,
            self._btn_open,
            self._btn_folder,
            self._btn_copy_path,
        ):
            btn.setEnabled(enabled)
        if self._btn_view is not None:
            self._btn_view.setEnabled(enabled)
        if self._btn_edit is not None:
            self._btn_edit.setEnabled(enabled)

    def _load_pixmap(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".svg":
            return self._render_svg(filepath)
        if ext == ".pdf":
            return self._render_pdf_first_page(filepath)
        pixmap = QPixmap()
        pixmap.load(filepath)
        return pixmap

    def _render_svg(self, filepath):
        try:
            from PySide6.QtSvg import QSvgRenderer
        except ImportError:
            return QPixmap()

        renderer = QSvgRenderer(filepath)
        if not renderer.isValid():
            return QPixmap()

        size = renderer.defaultSize()
        w, h = size.width(), size.height()
        if w <= 0 or h <= 0:
            view_box = renderer.viewBoxF()
            w = int(view_box.width()) if view_box.width() > 0 else 1000
            h = int(view_box.height()) if view_box.height() > 0 else 700

        scale = min(3.0, max(1.0, 2200 / max(w, h)))
        pixmap = QPixmap(max(1, int(w * scale)), max(1, int(h * scale)))
        pixmap.fill(Qt.transparent)

        painter = QPainter()
        if painter.begin(pixmap):
            try:
                painter.setRenderHints(
                    QPainter.Antialiasing
                    | QPainter.TextAntialiasing
                    | QPainter.SmoothPixmapTransform
                )
                renderer.render(painter)
            finally:
                painter.end()
        return pixmap

    def _render_pdf_first_page(self, filepath):
        try:
            from PySide6.QtPdf import QPdfDocument
        except ImportError:
            return QPixmap()

        doc = QPdfDocument(self)
        try:
            doc.load(filepath)
            if doc.pageCount() < 1:
                return QPixmap()
            page_size = doc.pagePointSize(0)
            image_size = QSize(
                max(1, int(page_size.width() * 2.5)),
                max(1, int(page_size.height() * 2.5)),
            )
            image = doc.render(0, image_size)
            if image.isNull():
                return QPixmap()
            return QPixmap.fromImage(image)
        finally:
            try:
                doc.close()
            except RuntimeError:
                logger.warning("Silent exception while closing PDF preview", exc_info=True)

    def _emit_edit_requested(self):
        if self._entry_context is not None:
            self.edit_requested.emit(self._entry_context)
            return
        if self._filepath:
            self.edit_requested.emit(self._filepath)

    def _emit_view_requested(self):
        if self._filepath:
            self.view_requested.emit(self._filepath)

    def _open_external(self):
        if self._filepath and os.path.exists(self._filepath):
            os.startfile(self._filepath)

    def _open_folder(self):
        if self._filepath and os.path.exists(self._filepath):
            os.startfile(os.path.dirname(self._filepath))

    def _copy_path_to_clipboard(self):
        if self._filepath:
            QApplication.clipboard().setText(self._filepath)


class ChartViewer(QWidget):
    """Full-size chart viewer dialog (embedded)."""

    edit_requested = Signal(object)
    status_message = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("CHART_VIEWER_TITLE"))
        self.resize(900, 650)
        self._full_data_headers = []
        self._full_data_rows = []
        self._full_data_row_count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._tabs = QTabWidget(self)
        layout.addWidget(self._tabs)

        self._preview = FigureFilePreview(self)
        self._preview.edit_requested.connect(self.edit_requested.emit)
        self._tabs.addTab(self._preview, tr("CHART_TAB_FIGURE"))
        self._tabs.addTab(self._build_data_tab(), tr("CHART_TAB_DATA"))
        self.retranslate()

    def load_figure(self, filepath, raw_data=None):
        self._preview.load_figure(filepath)
        self._populate_data_table(raw_data)

    def _build_data_tab(self) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._data_stats = QLabel(tr("CHART_DATA_EMPTY"))
        header.addWidget(self._data_stats)
        header.addStretch()
        layout.addLayout(header)

        self._data_table = QTableWidget()
        self._data_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._data_table.setAlternatingRowColors(True)
        self._data_table.verticalHeader().setVisible(False)
        self._data_copy_shortcut = QShortcut(QKeySequence.Copy, self._data_table)
        self._data_copy_shortcut.activated.connect(self._copy_data_table_to_clipboard)
        layout.addWidget(self._data_table, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        self._btn_copy_data = QPushButton(tr("COMMON_COPY"))
        self._btn_copy_data.clicked.connect(self._copy_data_table_to_clipboard)
        footer.addWidget(self._btn_copy_data)
        self._btn_export_csv = QPushButton(tr("CHART_BTN_EXPORT_CSV"))
        self._btn_export_csv.clicked.connect(self._export_data_csv)
        footer.addWidget(self._btn_export_csv)
        layout.addLayout(footer)
        return widget

    def retranslate(self):
        self.setWindowTitle(tr("CHART_VIEWER_TITLE"))
        self._tabs.setTabText(0, tr("CHART_TAB_FIGURE"))
        self._tabs.setTabText(1, tr("CHART_TAB_DATA"))
        self._preview.retranslate()
        self._btn_copy_data.setText(tr("COMMON_COPY"))
        self._btn_export_csv.setText(tr("CHART_BTN_EXPORT_CSV"))
        if not self._full_data_headers:
            self._data_stats.setText(tr("CHART_DATA_EMPTY"))

    def _populate_data_table(self, df_or_array) -> None:
        try:
            headers, rows = self._normalize_data_to_table(df_or_array)
            self._full_data_headers = headers
            self._full_data_rows = rows
            self._full_data_row_count = len(rows)

            display_rows = rows[:5000]
            self._data_table.clear()
            self._data_table.setRowCount(len(display_rows))
            self._data_table.setColumnCount(len(headers))
            self._data_table.setHorizontalHeaderLabels(headers)

            for row_idx, row in enumerate(display_rows):
                for col_idx, value in enumerate(row):
                    self._data_table.setItem(
                        row_idx,
                        col_idx,
                        QTableWidgetItem("" if value is None else str(value)),
                    )

            self._data_table.resizeColumnsToContents()
            self._data_table.resizeRowsToContents()

            if not headers:
                self._data_stats.setText(tr("CHART_DATA_NO_ROWS"))
                return

            suffix = tr("CHART_DATA_LIMIT_SUFFIX") if len(rows) > 5000 else ""
            self._data_stats.setText(
                tr("CHART_DATA_SUMMARY", len(rows), len(headers), suffix)
            )
        except (TypeError, ValueError) as exc:
            logger.warning("ChartViewer data table population failed: %s", exc, exc_info=True)
            self._full_data_headers = []
            self._full_data_rows = []
            self._full_data_row_count = 0
            self._data_table.clear()
            self._data_table.setRowCount(0)
            self._data_table.setColumnCount(0)
            self._data_stats.setText(tr("CHART_DATA_LOAD_FAILED"))
            logger.warning("Exception handled", exc_info=True)

    def _export_data_csv(self) -> None:
        try:
            if not self._full_data_headers:
                self.status_message.emit(tr("CHART_EXPORT_CSV_EMPTY"), "warning")
                return

            base_dir = ""
            preview_path = getattr(self._preview, "_filepath", "")
            if preview_path:
                base_dir = str(Path(preview_path).resolve().parent)
            default_path = (
                str(Path(base_dir) / "chart_data.csv") if base_dir else "chart_data.csv"
            )
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                tr("CHART_EXPORT_CSV_TITLE"),
                default_path,
                "CSV Files (*.csv)",
            )
            if not save_path:
                return

            with open(save_path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.writer(fh)
                writer.writerow(self._full_data_headers)
                writer.writerows(self._full_data_rows)

            self.status_message.emit(tr("CHART_EXPORT_CSV_SUCCESS", save_path), "success")
        except OSError as exc:
            logger.warning("ChartViewer CSV export failed: %s", exc, exc_info=True)
            self.status_message.emit(tr("CHART_EXPORT_CSV_FAILED", exc), "error")
            logger.warning("Exception handled", exc_info=True)

    def _copy_data_table_to_clipboard(self) -> None:
        copy_table_selection_to_clipboard(self._data_table)

    def _normalize_data_to_table(self, data):
        if data is None:
            return [], []

        if hasattr(data, "columns") and hasattr(data, "itertuples"):
            headers = [str(col) for col in list(data.columns)]
            rows = [
                [self._stringify_cell(value) for value in row]
                for row in data.itertuples(index=False, name=None)
            ]
            return headers, rows

        if isinstance(data, np.ndarray):
            return self._array_to_table(data)

        if isinstance(data, dict):
            return self._dict_to_table(data)

        if isinstance(data, list):
            if data and all(isinstance(item, dict) for item in data):
                headers = []
                for item in data:
                    for key in item:
                        key_text = str(key)
                        if key_text not in headers:
                            headers.append(key_text)
                rows = []
                for item in data:
                    rows.append([self._stringify_cell(item.get(key)) for key in headers])
                return headers, rows
            return self._array_to_table(np.asarray(data, dtype=object))

        return ["value"], [[self._stringify_cell(data)]]

    def _dict_to_table(self, data: dict):
        headers = [str(key) for key in data.keys()]
        normalized = {}
        max_rows = 0
        for key, value in data.items():
            series = self._series_from_value(value)
            normalized[str(key)] = series
            max_rows = max(max_rows, len(series))

        rows = []
        for idx in range(max_rows):
            row = []
            for header in headers:
                series = normalized.get(header, [])
                row.append(series[idx] if idx < len(series) else "")
            rows.append(row)
        return headers, rows

    def _array_to_table(self, arr: np.ndarray):
        array = np.asarray(arr, dtype=object)
        if array.ndim == 0:
            return ["value"], [[self._stringify_cell(array.item())]]
        if array.ndim == 1:
            return ["value"], [[self._stringify_cell(value)] for value in array.tolist()]

        headers = [f"col_{idx}" for idx in range(array.shape[1])]
        rows = []
        for row in array.tolist():
            rows.append([self._stringify_cell(value) for value in row])
        return headers, rows

    def _series_from_value(self, value):
        if value is None:
            return [""]

        if hasattr(value, "to_numpy") and hasattr(value, "columns"):
            rows = []
            columns = list(value.columns)
            for row in value.to_numpy().tolist():
                rows.append(
                    json.dumps(
                        {
                            str(col): self._stringify_cell(cell)
                            for col, cell in zip(columns, row)
                        },
                        ensure_ascii=False,
                    )
                )
            return rows

        if isinstance(value, dict):
            return [json.dumps(self._jsonable(value), ensure_ascii=False)]

        if isinstance(value, np.ndarray):
            arr = np.asarray(value, dtype=object)
            if arr.ndim == 0:
                return [self._stringify_cell(arr.item())]
            if arr.ndim == 1:
                return [self._stringify_cell(item) for item in arr.tolist()]
            return [json.dumps(self._jsonable(row), ensure_ascii=False) for row in arr.tolist()]

        if isinstance(value, (list, tuple)):
            scalar_list = all(
                not isinstance(item, (list, tuple, dict, np.ndarray))
                for item in value
            )
            if value and scalar_list:
                return [self._stringify_cell(item) for item in value]
            return [json.dumps(self._jsonable(item), ensure_ascii=False) for item in value]

        return [self._stringify_cell(value)]

    def _jsonable(self, value):
        if isinstance(value, dict):
            return {str(k): self._jsonable(v) for k, v in value.items()}
        if isinstance(value, np.ndarray):
            return self._jsonable(value.tolist())
        if isinstance(value, (list, tuple)):
            return [self._jsonable(v) for v in value]
        if hasattr(value, "item"):
            try:
                return value.item()
            except (TypeError, ValueError):
                logger.warning("Silent exception while normalizing data", exc_info=True)
        return value

    def _stringify_cell(self, value):
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        if isinstance(value, (np.floating, np.integer)):
            return str(value.item())
        if isinstance(value, (list, tuple, dict)):
            return json.dumps(self._jsonable(value), ensure_ascii=False)
        return str(value)
class ChartGallery(QWidget):
    """Scrollable gallery of chart thumbnails."""
    figure_selected = Signal(str)
    edit_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._viewer = None
        self._all_entries = []
        self._entries = []
        self._entry_by_figure_id = {}
        self._thumbnails = []
        self._figure_paths = []
        self._selected_path = ""
        self._selected_figure_id = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        self._category_label = QLabel(tr("CHART_CATEGORY_LABEL"))
        toolbar.addWidget(self._category_label)
        self._category_combo = QComboBox()
        self._category_combo.addItem(tr("CHART_CATEGORY_ALL"), FIGURE_CATEGORY_ALL)
        self._category_combo.addItem(
            tr("CHART_CATEGORY_SERIES_OVERVIEW"),
            FIGURE_CATEGORY_SERIES_OVERVIEW,
        )
        self._category_combo.addItem(
            tr("CHART_CATEGORY_PER_FRAME"),
            FIGURE_CATEGORY_PER_FRAME,
        )
        self._category_combo.addItem(
            tr("CHART_CATEGORY_OTHER_EXPORTS"),
            FIGURE_CATEGORY_OTHER_EXPORTS,
        )
        self._category_combo.currentIndexChanged.connect(self._reload_visible_entries)
        toolbar.addWidget(self._category_combo)
        toolbar.addStretch()
        btn_export = QPushButton(tr("CHART_BTN_EXPORT_ALL"))
        btn_export.clicked.connect(self._export_all)
        toolbar.addWidget(btn_export)
        btn_clear = QPushButton(tr("CHART_BTN_CLEAR"))
        btn_clear.clicked.connect(self.clear)
        toolbar.addWidget(btn_clear)
        layout.addLayout(toolbar)

        # Scroll area for thumbnails
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("background: transparent; border: none;")

        self._grid = QWidget()
        self._grid_layout = QVBoxLayout(self._grid)
        self._grid_layout.setSpacing(8)
        self._grid_layout.addStretch()
        self._scroll.setWidget(self._grid)
        layout.addWidget(self._scroll)

        self._asset_group = QGroupBox(tr("CHART_ASSET_PANEL_TITLE"))
        self._asset_group.setVisible(False)
        self._asset_layout = QVBoxLayout(self._asset_group)
        self._asset_layout.setContentsMargins(8, 8, 8, 8)
        self._asset_layout.setSpacing(6)
        layout.addWidget(self._asset_group)

    def load_directory(self, fig_dir, recursive=False):
        """Load figures from a directory as thumbnails."""
        self.clear()
        if not os.path.isdir(fig_dir):
            return

        exts = ('.svg', '.png', '.pdf', '.jpg', '.jpeg')
        if recursive:
            root = Path(fig_dir)
            filepaths = sorted(
                str(p) for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in exts
            )
        else:
            filepaths = sorted(
                os.path.join(fig_dir, f) for f in os.listdir(fig_dir)
                if f.lower().endswith(exts)
            )

        self.load_files(filepaths)

    def load_files(self, filepaths):
        """Load explicit figure paths as thumbnails."""
        self.load_entries(build_plot_gallery_entries(filepaths))

    def load_entries(self, entries):
        self.clear()
        self._all_entries = list(entries)
        self._figure_paths = [
            path for entry in self._all_entries for path in entry.asset_paths
        ]
        preferred_category = FIGURE_CATEGORY_ALL
        if any(entry.category == FIGURE_CATEGORY_SERIES_OVERVIEW for entry in self._all_entries):
            preferred_category = FIGURE_CATEGORY_SERIES_OVERVIEW
        index = self._category_combo.findData(preferred_category)
        if index >= 0 and self._category_combo.currentIndex() != index:
            self._category_combo.blockSignals(True)
            self._category_combo.setCurrentIndex(index)
            self._category_combo.blockSignals(False)
        self._reload_visible_entries()

    def _reload_visible_entries(self):
        previous_selected_figure_id = self._selected_figure_id
        self._clear_thumbnail_widgets()
        self._clear_asset_panel()
        if self._category_combo.count() == 0:
            return
        category = str(self._category_combo.currentData() or FIGURE_CATEGORY_ALL)
        self._entries = [
            entry
            for entry in self._all_entries
            if category == FIGURE_CATEGORY_ALL or entry.category == category
        ]
        self._entry_by_figure_id = {
            entry.figure_id: entry for entry in self._entries
        }
        self._selected_path = ""
        self._selected_figure_id = ""
        if not self._entries:
            return

        row_widget = None
        row_layout = None
        col = 0

        for entry in self._entries:
            thumb = ChartThumbnail(entry)
            thumb.clicked.connect(self.select_figure)
            thumb.double_clicked.connect(self._open_viewer)
            thumb.edit_clicked.connect(self.edit_requested.emit)
            thumb.copy_clicked.connect(self._copy_path_to_clipboard)
            self._thumbnails.append(thumb)

            if col == 0:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setSpacing(8)
                self._grid_layout.insertWidget(
                    self._grid_layout.count() - 1, row_widget)

            row_layout.addWidget(thumb, 1)
            col = (col + 1) % 3

        if row_layout is not None and col:
            row_layout.addStretch(3 - col)
        if previous_selected_figure_id in self._entry_by_figure_id:
            self.select_figure(previous_selected_figure_id, emit=False)

    def current_file(self):
        return self._selected_path

    def current_entry(self):
        return self._entry_by_figure_id.get(self._selected_figure_id)

    def figure_paths(self):
        return list(self._figure_paths)

    def select_figure(self, filepath, emit=True):
        lookup = str(filepath or "")
        entry = self._entry_by_figure_id.get(lookup)
        if entry is None:
            entry = next(
                (
                    item
                    for item in self._entries
                    if lookup == item.preview_path
                    or lookup == item.editable_path
                    or lookup in item.asset_paths
                ),
                None,
            )
        if entry is None:
            entry = next(
                (
                    item
                    for item in self._all_entries
                    if lookup == item.figure_id
                    or lookup == item.preview_path
                    or lookup == item.editable_path
                    or lookup in item.asset_paths
                ),
                None,
            )
            if entry is not None and entry.figure_id not in self._entry_by_figure_id:
                self._set_active_category(entry.category)
                entry = self._entry_by_figure_id.get(entry.figure_id, entry)
        if entry is None:
            return

        self._selected_figure_id = entry.figure_id
        self._selected_path = entry.preview_path
        for thumb in self._thumbnails:
            thumb.set_selected(thumb.entry.figure_id == entry.figure_id)
        self._rebuild_asset_panel(entry)
        if emit:
            self.figure_selected.emit(entry.preview_path)

    def refresh_figure(self, filepath):
        merged_paths = list(dict.fromkeys(self._figure_paths + [str(Path(filepath).resolve())]))
        self.load_files(merged_paths)
        self.select_figure(filepath, emit=False)

    def _open_viewer(self, filepath):
        if self._viewer is None:
            self._viewer = ChartViewer()
            self._viewer.edit_requested.connect(self.edit_requested.emit)
        self._viewer.load_figure(filepath)
        self._viewer.show()
        self._viewer.raise_()

    def _open_external(self, filepath):
        if filepath and os.path.exists(filepath):
            os.startfile(filepath)

    def _copy_path_to_clipboard(self, filepath):
        if filepath:
            QApplication.clipboard().setText(filepath)

    def _export_all(self):
        if not self._figure_paths:
            return
        save_dir = QFileDialog.getExistingDirectory(self, tr("DIALOG_EXPORT_ALL_TITLE"))
        if not save_dir:
            return
        import shutil
        for filepath in self._figure_paths:
            dst = os.path.join(save_dir, os.path.basename(filepath))
            if not os.path.exists(dst):
                shutil.copy2(filepath, dst)

    def clear(self):
        self._clear_thumbnail_widgets()
        self._clear_asset_panel()
        self._all_entries = []
        self._entries = []
        self._entry_by_figure_id = {}
        self._figure_paths = []
        self._selected_path = ""
        self._selected_figure_id = ""

    def _clear_thumbnail_widgets(self):
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails = []
        while self._grid_layout.count() > 1:
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _clear_asset_panel(self):
        while self._asset_layout.count():
            item = self._asset_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._asset_group.setVisible(False)

    def _set_active_category(self, category: str) -> None:
        target = str(category or FIGURE_CATEGORY_ALL)
        index = self._category_combo.findData(target)
        if index < 0 or self._category_combo.currentIndex() == index:
            return
        self._category_combo.blockSignals(True)
        self._category_combo.setCurrentIndex(index)
        self._category_combo.blockSignals(False)
        self._reload_visible_entries()

    def _rebuild_asset_panel(self, entry: FigureGalleryEntry) -> None:
        while self._asset_layout.count():
            item = self._asset_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for asset in entry.assets:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            label = QLabel(asset.label)
            row_layout.addWidget(label, 1)
            btn_open = QPushButton(tr("CHART_BTN_VIEW"))
            btn_open.clicked.connect(
                lambda _checked=False, path=asset.path: self.figure_selected.emit(path)
            )
            row_layout.addWidget(btn_open)
            btn_copy = QPushButton(tr("COMMON_COPY"))
            btn_copy.clicked.connect(
                lambda _checked=False, path=asset.path: self._copy_path_to_clipboard(path)
            )
            row_layout.addWidget(btn_copy)
            self._asset_layout.addWidget(row)
        self._asset_group.setTitle(tr("CHART_ASSET_PANEL_TITLE"))
        self._asset_group.setVisible(bool(entry.assets))


def _gallery_state_text(state: str) -> str:
    return {
        FIGURE_STATE_OBJECT: tr("CHART_STATE_OBJECT"),
        FIGURE_STATE_STATIC: tr("CHART_STATE_STATIC"),
        FIGURE_STATE_UNLINKED_EXPORT: tr("CHART_STATE_UNLINKED"),
    }.get(state, tr("CHART_STATE_UNLINKED"))


def _gallery_primary_label(state: str) -> str:
    return {
        FIGURE_STATE_OBJECT: tr("CHART_BTN_CONTINUE_EDITING"),
        FIGURE_STATE_STATIC: tr("CHART_BTN_STATIC_ANNOTATE"),
        FIGURE_STATE_UNLINKED_EXPORT: tr("CHART_BTN_VIEW"),
    }.get(state, tr("CHART_BTN_VIEW"))


def _gallery_secondary_label(state: str) -> str:
    return {
        FIGURE_STATE_OBJECT: tr("CHART_BTN_VIEW_EXPORTS"),
        FIGURE_STATE_STATIC: tr("CHART_BTN_VIEW_FILE"),
        FIGURE_STATE_UNLINKED_EXPORT: tr("CHART_BTN_OPEN_AS_STATIC"),
    }.get(state, tr("CHART_BTN_VIEW_FILE"))



