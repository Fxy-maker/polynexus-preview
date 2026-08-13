"""GUI adapter for the technique-neutral evidence package DTO."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from polynexus.core.project_workflow.evidence_view import EvidencePackageView


class EvidencePackageViewAdapter:
    """Expose compact presentation data without provider-specific branching."""

    def __init__(self, view: EvidencePackageView) -> None:
        self.view = view

    def summary(self) -> dict[str, object]:
        return {
            "status": self.view.status,
            "techniques": tuple(item.key for item in self.view.techniques),
            "metric_count": len(self.view.metrics),
            "human_review_count": len(self.view.human_review),
        }

    def techniques(self):
        return self.view.techniques

    def evidence(self):
        return self.view.evidence

    def metrics(self):
        return self.view.metrics

    def human_review(self):
        return self.view.human_review


class EvidencePackageDialog(QDialog):
    """Read-only package inspector built exclusively from the public DTO."""

    def __init__(self, view: EvidencePackageView, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.view = view
        self.setWindowTitle(f"Evidence package: {view.package_id}")
        self.resize(980, 650)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._overview_tab(), "Overview")
        self.tabs.addTab(self._evidence_tab(), "Evidence")
        self.tabs.addTab(self._metrics_tab(), "Metrics")
        self.tabs.addTab(self._review_tab(), "Review")
        layout.addWidget(self.tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _overview_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.addRow("Package", QLabel(f"{self.view.package_id}-v{self.view.version:03d}"))
        form.addRow("Status", QLabel(self.view.status))
        form.addRow("Techniques", QLabel(", ".join(item.key.upper() for item in self.view.techniques)))
        form.addRow("Questions", QLabel("; ".join(self.view.questions) or "-"))
        form.addRow("Metrics", QLabel(str(len(self.view.metrics))))
        form.addRow("Human review", QLabel(str(len(self.view.human_review))))
        return page

    def _evidence_tab(self) -> QWidget:
        table = self._table(["Technique", "Status", "Evidence", "Figures", "Tables", "Results", "Discussion"])
        for row, item in enumerate(self.view.evidence):
            table.insertRow(row)
            values = (
                item.technique.upper(), item.status, item.evidence_id,
                ", ".join(item.figures) or "-", ", ".join(item.tables) or "-",
                str(len(item.results_metric_ids)), str(len(item.discussion_metric_ids)),
            )
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        return table

    def _metrics_tab(self) -> QWidget:
        self.metrics_table = self._table(["Technique", "Metric", "Value", "Method", "Source", "Eligibility", "Reasons"])
        for row, item in enumerate(self.view.metrics):
            self.metrics_table.insertRow(row)
            value = f"{item.value} {item.unit}".strip()
            values = (
                item.technique.upper(), item.metric_key, value, item.method,
                item.source_locator, item.writing_eligibility, ", ".join(item.reason_codes) or "-",
            )
            for column, text in enumerate(values):
                cell = QTableWidgetItem(text)
                cell.setToolTip(f"Evidence: {item.evidence_id}\nRun: {item.run_id}")
                self.metrics_table.setItem(row, column, cell)
        return self.metrics_table

    def _review_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.review_table = self._table(["Evidence", "Action", "Reason"])
        for row, item in enumerate(self.view.human_review):
            self.review_table.insertRow(row)
            for column, text in enumerate((item.evidence_id, item.action, item.reason)):
                self.review_table.setItem(row, column, QTableWidgetItem(text))
        layout.addWidget(self.review_table)
        self.package_limitations = QLabel("Package limitations: " + ("; ".join(self.view.limitations) or "-"))
        self.package_limitations.setWordWrap(True)
        layout.addWidget(self.package_limitations)
        return page

    @staticmethod
    def _table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        return table


__all__ = ["EvidencePackageDialog", "EvidencePackageViewAdapter"]
