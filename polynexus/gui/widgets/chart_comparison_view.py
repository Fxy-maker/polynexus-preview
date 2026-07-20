"""Side-by-side chart comparison widget."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSplitter, QVBoxLayout, QWidget

from ..i18n import tr
from .chart_viewer import FigureFilePreview


@dataclass(frozen=True)
class ChartComparisonRequest:
    left_id: str
    right_id: str
    left_title: str
    right_title: str
    left_path: str
    right_path: str
    left_revision: int = 0
    right_revision: int = 0


class ChartComparisonView(QWidget):
    """Show two figure previews with revision/source identity side by side."""

    def __init__(self, request: ChartComparisonRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.setWindowTitle(tr("CHART_COMPARE_TITLE"))
        self.resize(1400, 800)
        self._splitter = QSplitter(Qt.Horizontal, self)
        self._left_title = QLabel(self._title_text(request.left_title, request.left_revision))
        self._right_title = QLabel(self._title_text(request.right_title, request.right_revision))
        self._left_preview = FigureFilePreview(show_edit_button=False)
        self._right_preview = FigureFilePreview(show_edit_button=False)
        self._left_preview.load_figure(request.left_path)
        self._right_preview.load_figure(request.right_path)
        self._splitter.addWidget(self._panel(self._left_title, self._left_preview))
        self._splitter.addWidget(self._panel(self._right_title, self._right_preview))
        layout = QVBoxLayout(self)
        layout.addWidget(self._splitter, 1)

    @staticmethod
    def _title_text(title: str, revision: int) -> str:
        return f"{title} · r{int(revision)}"

    @staticmethod
    def _panel(title: QLabel, preview: FigureFilePreview) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(title)
        layout.addWidget(preview, 1)
        return panel


__all__ = ["ChartComparisonRequest", "ChartComparisonView"]
