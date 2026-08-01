"""Joint Analysis Hub widget.

The hub presents existing SampleDB analysis runs as a batch-by-technique
matrix.  It lets users select already analysed batches and launch a joint
overview without loading another raw data file.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
)

from ...core.joint.dataset import (
    TECHNIQUES,
    JointBatchRow,
    collect_joint_dataset,
    detect_joint_opportunities,
)
from ..i18n import get_language
from ..table_clipboard_service import copy_table_selection_to_clipboard


def _text(zh: str, en: str) -> str:
    return zh if get_language() == "zh" else en


class JointAnalysisHub(QWidget):
    """Interactive selector for cross-technique analysis runs."""

    selection_changed = Signal(int)
    run_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = None
        self._rows: list[JointBatchRow] = []
        self._table_rows: list[JointBatchRow] = []
        self._populating = False
        self._build_ui()

    def set_db(self, sample_db) -> None:
        self._db = sample_db
        self.refresh()

    def refresh(self) -> None:
        if self._db is None:
            self._rows = []
        else:
            query = self._search.text().strip() or None
            self._rows = collect_joint_dataset(self._db, search=query)
        self._populate_table()
        self._update_summary()

    def selected_rows(self) -> list[JointBatchRow]:
        selected = []
        for table_row, row in enumerate(self._table_rows):
            item = self._table.item(table_row, 0)
            if item is not None and item.checkState() == Qt.Checked:
                selected.append(row)
        return selected

    def selected_batch_ids(self) -> list[str]:
        return [row.batch_id for row in self.selected_rows()]

    def has_selection(self) -> bool:
        return bool(self.selected_rows())

    def select_batch_ids(self, batch_ids: list[str]) -> int:
        batch_filter = set(batch_ids or [])
        self._populating = True
        selected_count = 0
        for table_row, row in enumerate(self._table_rows):
            item = self._table.item(table_row, 0)
            if item is None:
                continue
            checked = row.batch_id in batch_filter
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            if checked:
                selected_count += 1
        self._populating = False
        self._update_summary()
        return selected_count

    def retranslate(self) -> None:
        self._title.setText(_text("联合分析工作台", "Joint Analysis Hub"))
        self._subtitle.setText(
            _text(
                "从已有分析结果选择样品/批次，先看覆盖情况，再生成跨技术一致性和关系概览。",
                "Select existing analysed batches, inspect technique coverage, then generate cross-technique checks.",
            )
        )
        self._search.setPlaceholderText(_text("搜索样品名称 / 别名", "Search sample name / alias"))
        self._btn_refresh.setText(_text("刷新", "Refresh"))
        self._btn_recommended.setText(_text("推荐选择", "Recommended"))
        self._btn_all.setText(_text("全选", "Select all"))
        self._btn_clear.setText(_text("清除", "Clear"))
        self._btn_copy.setText(_text("复制", "Copy"))
        self._btn_run.setText(_text("生成联合概览", "Generate overview"))
        self._set_headers()
        self._update_summary()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("joint_hub_header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(2)
        self._title = QLabel()
        self._title.setStyleSheet("font-weight: 700; font-size: 16px;")
        self._subtitle = QLabel()
        self._subtitle.setWordWrap(True)
        self._subtitle.setStyleSheet("color: #8a95a3;")
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        layout.addWidget(header)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self._search = QLineEdit()
        self._search.returnPressed.connect(self.refresh)
        controls.addWidget(self._search, 1)

        self._btn_refresh = QPushButton()
        self._btn_refresh.clicked.connect(self.refresh)
        controls.addWidget(self._btn_refresh)

        self._btn_recommended = QPushButton()
        self._btn_recommended.clicked.connect(self._select_recommended)
        controls.addWidget(self._btn_recommended)

        self._btn_all = QPushButton()
        self._btn_all.clicked.connect(self._select_all)
        controls.addWidget(self._btn_all)

        self._btn_clear = QPushButton()
        self._btn_clear.clicked.connect(self._clear_selection)
        controls.addWidget(self._btn_clear)

        self._btn_copy = QPushButton(_text("复制", "Copy"))
        self._btn_copy.clicked.connect(self._copy_selected_rows_to_clipboard)
        controls.addWidget(self._btn_copy)

        self._btn_run = QPushButton()
        self._btn_run.setObjectName("primary_btn")
        self._btn_run.clicked.connect(self.run_requested.emit)
        controls.addWidget(self._btn_run)
        layout.addLayout(controls)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self._metric_rows = self._metric_label()
        self._metric_ready = self._metric_label()
        self._metric_selected = self._metric_label()
        self._metric_checks = self._metric_label()
        for label in (
            self._metric_rows,
            self._metric_ready,
            self._metric_selected,
            self._metric_checks,
        ):
            metrics.addWidget(label)
        metrics.addStretch()
        layout.addLayout(metrics)

        group = QGroupBox(_text("分析结果矩阵", "Analysis Result Matrix"))
        group_layout = QVBoxLayout(group)
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.itemChanged.connect(self._on_item_changed)
        self._copy_shortcut = QShortcut(QKeySequence.Copy, self._table)
        self._copy_shortcut.activated.connect(self._copy_selected_rows_to_clipboard)
        self._set_headers()
        group_layout.addWidget(self._table)
        layout.addWidget(group, 1)

        self.retranslate()

    def _metric_label(self) -> QLabel:
        label = QLabel()
        label.setMinimumHeight(28)
        label.setStyleSheet(
            "QLabel { padding: 5px 9px; border: 1px solid #3a4553; "
            "border-radius: 4px; color: #d7dee8; }"
        )
        return label

    def _set_headers(self) -> None:
        headers = [
            "",
            _text("样品", "Sample"),
            _text("批次", "Batch"),
            _text("条件", "Condition"),
            "DSC",
            "SAXS",
            "WAXS",
            "IR",
            "NMR",
            _text("可用联合分析", "Available joint analysis"),
        ]
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setColumnWidth(0, 34)
        self._table.setColumnWidth(1, 130)
        self._table.setColumnWidth(2, 130)
        self._table.setColumnWidth(3, 110)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)

    def _populate_table(self) -> None:
        self._populating = True
        self._table_rows = list(self._rows)
        self._table.setRowCount(len(self._table_rows))
        for table_row, row in enumerate(self._table_rows):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Unchecked)
            self._table.setItem(table_row, 0, check_item)

            self._set_item(table_row, 1, row.sample_name)
            self._set_item(table_row, 2, row.batch_label)
            self._set_item(table_row, 3, row.condition_label or row.condition_type or "-")
            for offset, tech in enumerate(TECHNIQUES, start=4):
                text = row.technique_cell(tech)
                item = self._set_item(table_row, offset, text)
                if tech in row.runs:
                    item.setForeground(QColor("#2fbf71"))
                else:
                    item.setForeground(QColor("#8a95a3"))
            opportunities = detect_joint_opportunities(row)
            self._set_item(table_row, 9, "; ".join(opportunities) if opportunities else "-")
        self._populating = False

    def _set_item(self, row: int, col: int, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self._table.setItem(row, col, item)
        return item

    def _select_recommended(self) -> None:
        self._set_checked(lambda row: row.technique_count >= 2)

    def _select_all(self) -> None:
        self._set_checked(lambda row: True)

    def _clear_selection(self) -> None:
        self._set_checked(lambda row: False)

    def _copy_selected_rows_to_clipboard(self) -> None:
        copy_table_selection_to_clipboard(self._table, start_column=1)

    def _set_checked(self, predicate) -> None:
        self._populating = True
        for table_row, row in enumerate(self._table_rows):
            item = self._table.item(table_row, 0)
            if item is not None:
                item.setCheckState(Qt.Checked if predicate(row) else Qt.Unchecked)
        self._populating = False
        self._update_summary()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating or item.column() != 0:
            return
        self._update_summary()

    def _update_summary(self) -> None:
        selected = self.selected_rows()
        ready = [row for row in self._rows if row.technique_count >= 2]
        opportunities = sum(len(detect_joint_opportunities(row)) for row in selected)
        self._metric_rows.setText(_text(f"批次 {len(self._rows)}", f"Batches {len(self._rows)}"))
        self._metric_ready.setText(_text(f"可联合 {len(ready)}", f"Joint-ready {len(ready)}"))
        self._metric_selected.setText(_text(f"已选 {len(selected)}", f"Selected {len(selected)}"))
        self._metric_checks.setText(_text(f"检查项 {opportunities}", f"Checks {opportunities}"))
        self._btn_run.setEnabled(bool(selected))
        self._btn_copy.setEnabled(self._table.rowCount() > 0)
        self.selection_changed.emit(len(selected))
