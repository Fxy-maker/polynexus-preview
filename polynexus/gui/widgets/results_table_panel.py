"""Reusable Qt panel for structured analysis-result presentations."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import Qt, Signal
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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import get_language, tr, tr_for_language
from ..result_table_models import HeroMetric, ResultTableSection, TableColumn, TableScalar
from ..results_workbench_profiles import ResultsWorkbenchProfile, profile_for
from ..theme import ThemeEngine

_RAW_ROLE = Qt.UserRole
_STATUS_ROLE = int(Qt.UserRole) + 1
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


def _review_hint_status_text(status: str) -> str:
    normalized = status.casefold()
    if normalized in _STATUS_TEXT_KEYS:
        return _status_text(normalized)
    return normalized.replace("_", " ").title()


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

    figure_link_requested = Signal(str)
    review_action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("results_table_panel")
        self._theme_engine = ThemeEngine.instance()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._profile = profile_for("generic", language=get_language())
        self._workbench_header = QWidget(self)
        self._workbench_header.setObjectName("results_workbench_header")
        header_layout = QVBoxLayout(self._workbench_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        self.workbench_title = QLabel(self._workbench_header)
        self.workbench_title.setObjectName("results_workbench_title")
        self.workbench_title.setAccessibleName(self.workbench_title.objectName())
        header_layout.addWidget(self.workbench_title)
        self.workbench_subtitle = QLabel(self._workbench_header)
        self.workbench_subtitle.setObjectName("results_workbench_subtitle")
        self.workbench_subtitle.setWordWrap(True)
        header_layout.addWidget(self.workbench_subtitle)
        self.figure_links_widget = QWidget(self._workbench_header)
        self.figure_links_widget.setObjectName("results_workbench_figure_links")
        self.figure_links_layout = QHBoxLayout(self.figure_links_widget)
        self.figure_links_layout.setContentsMargins(0, 4, 0, 2)
        self.figure_links_layout.setSpacing(6)
        header_layout.addWidget(self.figure_links_widget)
        self.workbench_review_action = QPushButton(self._workbench_header)
        self.workbench_review_action.setObjectName("results_workbench_review_action")
        self.workbench_review_action.clicked.connect(self._emit_profile_review_action)
        header_layout.addWidget(self.workbench_review_action, 0, Qt.AlignLeft)
        layout.addWidget(self._workbench_header)

        self.workbench_state = QLabel(self)
        self.workbench_state.setObjectName("results_workbench_state")
        self.workbench_state.setWordWrap(True)
        self.workbench_state.hide()
        layout.addWidget(self.workbench_state)

        self._metrics_widget = QWidget(self)
        self._metrics_widget.setObjectName("results_metrics")
        self._metrics_layout = QGridLayout(self._metrics_widget)
        self._metrics_layout.setContentsMargins(0, 0, 0, 0)
        self._metrics_layout.setHorizontalSpacing(8)
        self._metrics_layout.setVerticalSpacing(8)
        for column in range(4):
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

        self.review_hint_widget = QWidget(self)
        self.review_hint_widget.setObjectName("results_review_hint")
        review_hint_layout = QHBoxLayout(self.review_hint_widget)
        review_hint_layout.setContentsMargins(12, 8, 12, 8)
        review_hint_layout.setSpacing(8)

        self._review_hint_status_dot = QLabel("●", self.review_hint_widget)
        self._review_hint_status_dot.setObjectName("results_review_hint_status_dot")
        self._review_hint_status_dot.setFixedWidth(12)
        review_hint_layout.addWidget(self._review_hint_status_dot)

        self.review_hint_status = QLabel(self.review_hint_widget)
        self.review_hint_status.setObjectName("results_review_hint_status")
        review_hint_layout.addWidget(self.review_hint_status)

        self.review_hint_title = QLabel(self.review_hint_widget)
        self.review_hint_title.setObjectName("results_review_hint_title")
        review_hint_layout.addWidget(self.review_hint_title)

        self.review_hint_detail = QLabel(self.review_hint_widget)
        self.review_hint_detail.setObjectName("results_review_hint_detail")
        self.review_hint_detail.setWordWrap(True)
        review_hint_layout.addWidget(self.review_hint_detail, 1)

        self.review_hint_next = QLabel(self.review_hint_widget)
        self.review_hint_next.setObjectName("results_review_hint_next")
        self.review_hint_next.setWordWrap(True)
        review_hint_layout.addWidget(self.review_hint_next, 1)

        self.review_hint_action = QPushButton(self.review_hint_widget)
        self.review_hint_action.setObjectName("results_review_hint_action")
        self.review_hint_action.clicked.connect(self._invoke_review_hint_action)
        self.review_hint_action.hide()
        self.review_hint_action.setEnabled(False)
        review_hint_layout.addWidget(self.review_hint_action)

        self._review_hint_action = None
        self._review_hint_action_text_key = None
        self.review_hint_widget.setVisible(False)
        layout.insertWidget(1, self.review_hint_widget)
        layout.addWidget(self.tabs, 1)

        self._metrics_widget.setVisible(False)
        self.tabs.setTabVisible(0, True)
        self.tabs.setTabVisible(1, False)
        self.tabs.setTabVisible(2, False)
        self._theme_engine.theme_changed.connect(self._refresh_visual_theme)
        self.set_profile(self._profile)

    def retranslate(self) -> None:
        """Refresh localized captions and visible status indicators."""
        self.set_profile(self._profile.for_language(get_language()))
        for label in self.hero_labels:
            label.setText(
                _hero_text(
                    str(label.property("metricLabel")),
                    str(label.property("metricDisplay")),
                    str(label.property("metricUnit")),
                    str(label.property("metricStatus")),
                )
            )
            label.setAccessibleName(label.text())
        for table in (self.primary_table, self.detail_table, self.diagnostic_table):
            for label in table.findChildren(QLabel):
                status = label.property("resultStatus")
                if status is not None:
                    text = _status_text(str(status))
                    label.setText(text)
                    label.setAccessibleName(text)
        status = self.review_hint_widget.property("reviewStatus")
        if status is not None:
            self.review_hint_status.setText(_review_hint_status_text(str(status)))
        if self._review_hint_action_text_key is not None:
            self.review_hint_action.setText(tr(self._review_hint_action_text_key))
        self._refresh_review_hint_style()

    @property
    def profile(self) -> ResultsWorkbenchProfile:
        return self._profile

    def set_profile(self, profile: ResultsWorkbenchProfile | None) -> None:
        """Apply mode-specific narrative metadata without changing result data."""
        self._profile = profile or profile_for("generic", language=get_language())
        language = self._profile.language
        self.workbench_title.setText(self._profile.title)
        self.workbench_subtitle.setText(self._profile.subtitle)
        self.workbench_review_action.setText(self._profile.review_action.label_for(language))
        self.workbench_review_action.setVisible(self._profile.key != "generic")
        self.tabs.setTabText(0, self._profile.tab_labels[0])
        self.tabs.setTabText(1, self._profile.tab_labels[1])
        self.tabs.setTabText(2, self._profile.tab_labels[2])
        while self.figure_links_layout.count():
            item = self.figure_links_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for link in self._profile.figure_links:
            button = QPushButton(link.label_for(language), self.figure_links_widget)
            button.setObjectName(
                "results_figure_link_" + link.key.replace(".", "_").replace("-", "_")
            )
            button.setProperty("figureLinkKey", link.key)
            button.setProperty("figureLinkRole", link.role)
            button.clicked.connect(lambda _checked=False, key=link.key: self.figure_link_requested.emit(key))
            self.figure_links_layout.addWidget(button)
        self.figure_links_layout.addStretch(1)
        self.figure_links_widget.setVisible(bool(self._profile.figure_links))

    def _emit_profile_review_action(self) -> None:
        self.review_action_requested.emit(self._profile.review_action.key)

    def _refresh_visual_theme(self, _theme_name: str = "") -> None:
        """Reapply the small amount of widget-local styling owned by this panel."""
        tokens = self._theme_engine.tokens
        for label in self.hero_labels:
            if label.parent() is not None:
                _apply_hero_style(label, tokens)
        for table in (self.primary_table, self.detail_table, self.diagnostic_table):
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    item = table.item(row, column)
                    if item is not None:
                        item.setForeground(QColor(tokens.text_primary))
            for label in table.findChildren(QLabel):
                status = label.property("resultStatus")
                if status is not None:
                    _apply_status_badge_style(label, str(status), tokens)
                    container = label.parentWidget()
                    if container is not None:
                        display_label = container.findChild(QLabel, "result_cell_display")
                        if display_label is not None:
                            display_label.setStyleSheet(
                                f"color: {tokens.text_primary}; background: transparent; "
                                "border: none;"
                            )
        self._refresh_review_hint_style()

    def _refresh_review_hint_style(self) -> None:
        tokens = self._theme_engine.tokens
        status = str(self.review_hint_widget.property("reviewStatus") or "neutral")
        color, border = _status_colors(status, tokens)
        self.review_hint_widget.setStyleSheet(
            f"background: {tokens.bg_card}; border: 1px solid {border}; "
            f"border-radius: {tokens.radius_md}px;"
        )
        self._review_hint_status_dot.setStyleSheet(
            f"color: {color}; background: transparent; border: none;"
        )
        self.review_hint_status.setStyleSheet(
            f"color: {color}; background: transparent; border: none; font-weight: 600;"
        )
        self.review_hint_title.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent; border: none; "
            "font-weight: 600;"
        )
        self.review_hint_detail.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent; border: none;"
        )
        self.review_hint_next.setStyleSheet(
            f"color: {tokens.text_muted}; background: transparent; border: none;"
        )
        self.review_hint_action.setStyleSheet(
            f"QPushButton {{ background: {tokens.accent_saxs}; color: {tokens.text_on_accent}; "
            f"border: 1px solid {tokens.accent_saxs}; border-radius: {tokens.radius_sm}px; "
            f"padding: {tokens.spacing_xs}px {tokens.spacing_md}px; }} "
            f"QPushButton:hover {{ background: {tokens.bg_hover}; color: {tokens.text_primary}; "
            f"border-color: {tokens.border_focus}; }}"
        )

    def set_review_hint(
        self,
        *,
        title: str,
        detail: str = "",
        next_text: str = "",
        status: str = "neutral",
        action_text: str = "",
        action=None,
    ) -> None:
        """Show a compact, actionable review hint above the result tabs."""
        title_text = str(title or "")
        detail_text = str(detail or "")
        next_text_value = str(next_text or "")
        status_value = str(status or "neutral").strip().casefold() or "neutral"
        action_text_value = str(action_text or "")
        self.review_hint_widget.setProperty("reviewStatus", status_value)
        self.review_hint_status.setText(_review_hint_status_text(status_value))
        self.review_hint_title.setText(title_text)
        self.review_hint_detail.setText(detail_text)
        self.review_hint_next.setText(next_text_value)
        self.review_hint_action.setText(action_text_value)
        self.review_hint_status.setVisible(bool(self.review_hint_status.text()))
        self.review_hint_title.setVisible(bool(title_text))
        self.review_hint_detail.setVisible(bool(detail_text))
        self.review_hint_next.setVisible(bool(next_text_value))
        self._review_hint_action = action if callable(action) else None
        self._review_hint_action_text_key = None
        if self._review_hint_action is not None:
            for action_key in ("SAXS_RESULTS_REVIEW_HINT_ACTION", "RESULTS_WORKBENCH_REVIEW_ACTION"):
                if action_text_value in {
                    tr_for_language(action_key, "zh"),
                    tr_for_language(action_key, "en"),
                }:
                    self._review_hint_action_text_key = action_key
                    break
        has_action = bool(action_text_value and self._review_hint_action is not None)
        self.review_hint_action.setVisible(has_action)
        self.review_hint_action.setEnabled(has_action)
        self._refresh_review_hint_style()
        self.review_hint_widget.setVisible(bool(title_text or detail_text or next_text_value))

    def clear_review_hint(self) -> None:
        """Hide the review hint and release any previously supplied callback."""
        self._review_hint_action = None
        self._review_hint_action_text_key = None
        self.review_hint_widget.setProperty("reviewStatus", None)
        self.review_hint_widget.setVisible(False)
        self.review_hint_status.setText("")
        self.review_hint_title.setText("")
        self.review_hint_detail.setText("")
        self.review_hint_next.setText("")
        self.review_hint_action.setText("")
        self.review_hint_action.setVisible(False)
        self.review_hint_action.setEnabled(False)
        self._refresh_review_hint_style()

    def _invoke_review_hint_action(self) -> None:
        action = self._review_hint_action
        if action is not None:
            action()

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
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(80)
        return table

    def set_content(
        self,
        *,
        heroes: tuple[HeroMetric, ...],
        primary: ResultTableSection,
        detail: ResultTableSection,
        diagnostics: ResultTableSection,
        profile: ResultsWorkbenchProfile | None = None,
        error_text: str = "",
    ) -> None:
        """Replace the complete structured result presentation."""
        self.set_profile(profile or profile_for("generic", language=get_language()))
        self._set_heroes(heroes)
        self._populate_table(self.primary_table, primary)
        self._populate_table(self.detail_table, detail)
        self._populate_table(self.diagnostic_table, diagnostics)
        self.tabs.setTabVisible(0, True)
        self.tabs.setTabVisible(1, bool(detail.rows))
        self.tabs.setTabVisible(2, bool(diagnostics.rows))
        state_text = str(error_text or "") or (
            self._profile.empty_state
            if not (heroes or primary.rows or detail.rows or diagnostics.rows)
            else ""
        )
        self.workbench_state.setText(state_text)
        self.workbench_state.setVisible(bool(state_text))

    def _set_heroes(self, heroes: tuple[HeroMetric, ...]) -> None:
        while self._metrics_layout.count():
            item = self._metrics_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self.hero_labels.clear()

        visible_heroes = heroes[:6]
        columns = 4 if len(visible_heroes) <= 4 else 3
        for column in range(4):
            self._metrics_layout.setColumnStretch(column, 1 if column < columns else 0)

        for index, metric in enumerate(visible_heroes):
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
            label.setAccessibleName(label.text())
            label.setAccessibleDescription(label.toolTip())
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            _apply_hero_style(label, self._theme_engine.tokens)
            self._metrics_layout.addWidget(label, index // columns, index % columns)
            self.hero_labels.append(label)

        self._metrics_widget.setVisible(bool(self.hero_labels))

    def _populate_table(self, table: QTableWidget, section: ResultTableSection) -> None:
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
                    item.setForeground(QColor(self._theme_engine.tokens.text_primary))
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
            table.horizontalHeader().setStretchLastSection(True)
        finally:
            table.setSortingEnabled(sorting_enabled)


def _apply_hero_style(label: QLabel, tokens: Any) -> None:
    label.setMinimumHeight(72)
    label.setStyleSheet(
        f"background: {tokens.bg_card}; border: 1px solid {tokens.border_light}; "
        "border-radius: 10px; "
        f"color: {tokens.text_primary}; padding: {tokens.spacing_sm}px {tokens.spacing_md}px;"
    )


def _status_colors(status: str, tokens: Any) -> tuple[str, str]:
    normalized = status.casefold()
    color = {
        "reliable": tokens.success,
        "review": tokens.warning,
        "blocked": tokens.danger,
    }.get(normalized, tokens.text_muted)
    border = color if normalized in {"reliable", "review", "blocked"} else tokens.border_light
    return color, border


def _apply_status_badge_style(label: QLabel, status: str, tokens: Any) -> None:
    color, border = _status_colors(status, tokens)
    label.setStyleSheet(
        f"color: {color}; background: {tokens.bg_surface}; "
        f"border: 1px solid {border}; border-radius: 10px; "
        "padding: 1px 6px; font-weight: 600;"
    )


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
    display_label.setStyleSheet(
        f"color: {ThemeEngine.instance().tokens.text_primary}; "
        "background: transparent; border: none;"
    )
    layout.addWidget(display_label, 1)

    normalized = status.casefold()
    text = _status_text(status)
    status_label = QLabel(text, container)
    status_label.setObjectName(f"result_cell_status_{normalized}")
    status_label.setProperty("resultStatus", status)
    status_label.setAccessibleName(text)
    status_label.setToolTip(tooltip)
    _apply_status_badge_style(status_label, status, ThemeEngine.instance().tokens)
    layout.addWidget(status_label)
    return container
