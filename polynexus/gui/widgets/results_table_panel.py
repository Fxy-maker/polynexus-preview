"""Reusable Qt panel for structured analysis-result presentations."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..result_table_models import HeroMetric, ResultTableSection, TableColumn, TableScalar
from ..styles import C_BG_CARD, C_BORDER, C_DANGER, C_SUCCESS, C_TEXT_PRIMARY, C_WARNING

_RAW_ROLE = Qt.UserRole
_STATUS_ROLE = int(Qt.UserRole) + 1
_STATUS_COLORS = {
    "reliable": C_SUCCESS,
    "review": C_WARNING,
    "blocked": C_DANGER,
}
_STATUS_TEXT_KEYS = {
    "reliable": "RESULTS_STATUS_RELIABLE",
    "review": "RESULTS_STATUS_REVIEW",
    "blocked": "RESULTS_STATUS_BLOCKED",
}


def _tooltip_text(tooltip: str, provenance: str) -> str:
    parts = [part for part in (tooltip.strip(), provenance.strip()) if part]
    return "\n".join(dict.fromkeys(parts))


def _status_text(status: str) -> str:
    normalized = status.casefold()
    if normalized in {"", "neutral"}:
        return ""
    key = _STATUS_TEXT_KEYS.get(normalized)
    return tr(key) if key is not None else status.replace("_", " ")


def _hero_text(label: str, display: str, unit: str, status: str) -> str:
    value = f"{display} {unit}" if unit else display
    lines = [label, value]
    visible_status = _status_text(status)
    if visible_status:
        lines.append(visible_status)
    return "\n".join(lines)


def _sort_key(value: Any) -> tuple[Any, ...]:
    if isinstance(value, bool):
        return (0, value, 0, str(value))
    if isinstance(value, int):
        return (0, value, 1, str(value))
    if isinstance(value, float) and math.isfinite(value):
        return (0, value, 2, str(value))
    if isinstance(value, str):
        return (1, value.casefold(), value, "")
    if isinstance(value, bytes):
        return (2, value.hex(), "", "")
    if isinstance(value, complex) and math.isfinite(value.real) and math.isfinite(value.imag):
        return (3, value.real, value.imag, "")
    if value is None:
        return (4, 0, "", "")
    if isinstance(value, float):
        if value == float("-inf"):
            rank = 1
        elif value == float("inf"):
            rank = 2
        else:
            rank = 3
        return (4, rank, "", "")
    if isinstance(value, complex):
        return (4, 4, str(value), "")
    return (4, 5, type(value).__name__, repr(value))


class TypedTableWidgetItem(QTableWidgetItem):
    """A table item that retains its typed value for reliable sorting."""

    def __init__(
        self,
        display: str,
        *,
        raw: TableScalar = None,
        status: str = "neutral",
        tooltip: str = "",
    ) -> None:
        super().__init__(display)
        self._raw = raw
        self._status = status
        self.setToolTip(tooltip)

    def data(self, role: int) -> Any:
        if int(role) == int(_RAW_ROLE):
            return self._raw
        if int(role) == _STATUS_ROLE:
            return self._status
        return super().data(role)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        return _sort_key(self.data(_RAW_ROLE)) < _sort_key(other.data(_RAW_ROLE))


class ResultsTablePanel(QWidget):
    """Display hero metrics and primary, detail, and diagnostic result tables."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("results_table_panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._metrics_widget = QWidget(self)
        self._metrics_widget.setObjectName("results_metrics")
        self._metrics_layout = QGridLayout(self._metrics_widget)
        self._metrics_layout.setContentsMargins(0, 0, 0, 0)
        self._metrics_layout.setHorizontalSpacing(8)
        self._metrics_layout.setVerticalSpacing(8)
        for column in range(3):
            self._metrics_layout.setColumnStretch(column, 1)
        layout.addWidget(self._metrics_widget)

        self.hero_labels: list[QLabel] = []

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("results_table_tabs")
        self.primary_table = self._create_table("results_primary_table")
        self.detail_table = self._create_table("results_detail_table")
        self.diagnostic_table = self._create_table("results_diagnostic_table")
        self.tabs.addTab(self.primary_table, tr("RESULTS_TAB_KEY"))
        self.tabs.addTab(self.detail_table, tr("RESULTS_TAB_DETAIL"))
        self.tabs.addTab(self.diagnostic_table, tr("RESULTS_TAB_DIAGNOSTICS"))
        layout.addWidget(self.tabs, 1)

        self._metrics_widget.setVisible(False)
        self.tabs.setTabVisible(0, True)
        self.tabs.setTabVisible(1, False)
        self.tabs.setTabVisible(2, False)

    def retranslate(self) -> None:
        """Refresh localized captions and visible status indicators."""
        self.tabs.setTabText(0, tr("RESULTS_TAB_KEY"))
        self.tabs.setTabText(1, tr("RESULTS_TAB_DETAIL"))
        self.tabs.setTabText(2, tr("RESULTS_TAB_DIAGNOSTICS"))
        for label in self.hero_labels:
            label.setText(
                _hero_text(
                    str(label.property("metricLabel")),
                    str(label.property("metricDisplay")),
                    str(label.property("metricUnit")),
                    str(label.property("metricStatus")),
                )
            )
        for table in (self.primary_table, self.detail_table, self.diagnostic_table):
            for label in table.findChildren(QLabel):
                status = label.property("resultStatus")
                if status is not None:
                    text = _status_text(str(status))
                    label.setText(text)
                    label.setAccessibleName(text)

    @staticmethod
    def _create_table(object_name: str) -> QTableWidget:
        table = QTableWidget()
        table.setObjectName(object_name)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(80)
        return table

    def set_content(
        self,
        *,
        heroes: tuple[HeroMetric, ...],
        primary: ResultTableSection,
        detail: ResultTableSection,
        diagnostics: ResultTableSection,
    ) -> None:
        """Replace the complete structured result presentation."""
        self._set_heroes(heroes)
        self._populate_table(self.primary_table, primary)
        self._populate_table(self.detail_table, detail)
        self._populate_table(self.diagnostic_table, diagnostics)
        self.tabs.setTabVisible(0, True)
        self.tabs.setTabVisible(1, bool(detail.rows))
        self.tabs.setTabVisible(2, bool(diagnostics.rows))

    def _set_heroes(self, heroes: tuple[HeroMetric, ...]) -> None:
        while self._metrics_layout.count():
            item = self._metrics_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.hero_labels.clear()

        for index, metric in enumerate(heroes[:6]):
            label = QLabel(
                _hero_text(metric.label, metric.display, metric.unit, metric.status),
                self._metrics_widget,
            )
            label.setObjectName(f"result_metric_{metric.status or 'neutral'}")
            label.setProperty("metricLabel", metric.label)
            label.setProperty("metricDisplay", metric.display)
            label.setProperty("metricUnit", metric.unit)
            label.setProperty("metricStatus", metric.status)
            label.setToolTip(_tooltip_text(metric.tooltip, metric.provenance))
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                f"background: {C_BG_CARD}; border: 1px solid {C_BORDER}; "
                f"border-radius: 4px; color: {C_TEXT_PRIMARY}; padding: 8px;"
            )
            self._metrics_layout.addWidget(label, index // 3, index % 3)
            self.hero_labels.append(label)

        self._metrics_widget.setVisible(bool(self.hero_labels))

    @staticmethod
    def _populate_table(table: QTableWidget, section: ResultTableSection) -> None:
        sorting_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        try:
            table.clear()
            table.setColumnCount(len(section.columns))
            table.setRowCount(len(section.rows))
            table.setHorizontalHeaderLabels([column.header for column in section.columns])
            for row_index, row in enumerate(section.rows):
                for column_index, cell in enumerate(row[: len(section.columns)]):
                    column = section.columns[column_index]
                    item = TypedTableWidgetItem(
                        cell.display,
                        raw=cell.raw,
                        status=cell.status,
                        tooltip=_tooltip_text(cell.tooltip, cell.provenance),
                    )
                    item.setTextAlignment(_alignment_for(column))
                    color = _STATUS_COLORS.get(cell.status.casefold())
                    if color is not None:
                        item.setForeground(QColor(color))
                    table.setItem(row_index, column_index, item)
                    if _status_text(cell.status):
                        table.setCellWidget(
                            row_index,
                            column_index,
                            _status_cell_widget(
                                cell.display,
                                cell.status,
                                column,
                                item.toolTip(),
                            ),
                        )
            table.resizeColumnsToContents()
            for column_index in range(table.columnCount()):
                width = min(max(table.columnWidth(column_index) + 12, 96), 420)
                table.setColumnWidth(column_index, width)
        finally:
            table.setSortingEnabled(sorting_enabled)


def _alignment_for(column: TableColumn) -> Qt.AlignmentFlag:
    alignment = column.alignment.casefold()
    if alignment == "right":
        return Qt.AlignRight | Qt.AlignVCenter
    if alignment == "center":
        return Qt.AlignHCenter | Qt.AlignVCenter
    return Qt.AlignLeft | Qt.AlignVCenter


def _status_cell_widget(
    display: str,
    status: str,
    column: TableColumn,
    tooltip: str,
) -> QWidget:
    container = QWidget()
    container.setObjectName("result_cell_with_status")
    container.setToolTip(tooltip)
    container.setAttribute(Qt.WA_TransparentForMouseEvents)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 0, 4, 0)
    layout.setSpacing(6)

    display_label = QLabel(display, container)
    display_label.setObjectName("result_cell_display")
    display_label.setToolTip(tooltip)
    display_label.setAlignment(_alignment_for(column))
    layout.addWidget(display_label, 1)

    normalized = status.casefold()
    text = _status_text(status)
    status_label = QLabel(text, container)
    status_label.setObjectName(f"result_cell_status_{normalized}")
    status_label.setProperty("resultStatus", status)
    status_label.setAccessibleName(text)
    status_label.setToolTip(tooltip)
    color = _STATUS_COLORS.get(normalized, C_TEXT_PRIMARY)
    status_label.setStyleSheet(f"color: {color}; font-weight: 600;")
    layout.addWidget(status_label)
    return container
