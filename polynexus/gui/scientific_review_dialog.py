"""Generic Qt entry form for reviewer-owned scientific decisions."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from ..core.scientific_review import (
    ScientificReviewRecord,
    required_decision_keys,
    validate_review_record,
)


class ScientificReviewDialog(QDialog):
    """Build one validated review record without technique-specific logic."""

    _FIELD_NAMES = ("record_id", "reviewer", "reviewed_at", "policy_version")
    _STATUSES = ("pending", "accepted", "conditional", "rejected", "stale")

    def __init__(
        self,
        scope: str,
        *,
        source_refs: Iterable[str] = (),
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.scope = str(scope or "").strip().lower()
        self._decision_keys = required_decision_keys(self.scope)
        if not self._decision_keys:
            raise ValueError(f"unsupported review scope: {self.scope}")

        self.setWindowTitle("Scientific Review")
        self._fields: dict[str, QLineEdit] = {}
        self._decision_fields: dict[str, QLineEdit] = {}
        self._record: ScientificReviewRecord | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        for name in self._FIELD_NAMES:
            edit = QLineEdit(self)
            edit.setObjectName(f"scientific_review_{name}")
            self._fields[name] = edit
            form.addRow(name.replace("_", " ").title(), edit)

        self._source_refs = QLineEdit(self)
        self._source_refs.setText("; ".join(str(item).strip() for item in source_refs if str(item).strip()))
        self._source_refs.setToolTip("Separate source references with semicolons.")
        form.addRow("Source refs", self._source_refs)

        self._status = QComboBox(self)
        self._status.addItems(self._STATUSES)
        form.addRow("Status", self._status)
        layout.addLayout(form)

        decisions_label = QLabel("Required decisions", self)
        layout.addWidget(decisions_label)
        decisions_form = QFormLayout()
        for key in self._decision_keys:
            edit = QLineEdit(self)
            edit.setObjectName(f"scientific_review_decision_{key}")
            self._decision_fields[key] = edit
            decisions_form.addRow(key.replace("_", " ").title(), edit)
        layout.addLayout(decisions_form)

        self._conditions = QPlainTextEdit(self)
        self._conditions.setPlaceholderText("One follow-up condition per line")
        self._conditions.setMaximumHeight(80)
        layout.addWidget(QLabel("Conditions", self))
        layout.addWidget(self._conditions)

        self._error = QLabel(self)
        self._error.setWordWrap(True)
        self._error.setStyleSheet("color: #b42318;")
        self._error.setVisible(False)
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self._accept_validated)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def set_field(self, name: str, value: str) -> None:
        """Set a scalar field; intended for Workbench hydration and tests."""

        if name not in self._fields:
            raise KeyError(name)
        self._fields[name].setText(str(value or ""))

    def set_decision_value(self, key: str, value: str) -> None:
        if key not in self._decision_fields:
            raise KeyError(key)
        self._decision_fields[key].setText(str(value or ""))

    def set_status(self, status: str) -> None:
        index = self._status.findText(str(status or "").strip().lower())
        if index < 0:
            raise ValueError(f"unsupported review status: {status}")
        self._status.setCurrentIndex(index)

    def build_record(self) -> ScientificReviewRecord:
        """Construct and validate the record without changing dialog state."""

        source_refs = tuple(
            item.strip()
            for item in self._source_refs.text().replace(",", ";").split(";")
            if item.strip()
        )
        decisions = {
            key: field.text().strip()
            for key, field in self._decision_fields.items()
            if field.text().strip()
        }
        conditions = tuple(
            line.strip()
            for line in self._conditions.toPlainText().splitlines()
            if line.strip()
        )
        record = ScientificReviewRecord(
            record_id=self._fields["record_id"].text().strip(),
            scope=self.scope,
            reviewer=self._fields["reviewer"].text().strip(),
            reviewed_at=self._fields["reviewed_at"].text().strip(),
            policy_version=self._fields["policy_version"].text().strip(),
            source_refs=source_refs,
            decisions=decisions,
            status=self._status.currentText(),
            conditions=conditions,
        )
        return validate_review_record(record)

    def serialized_record(self) -> dict:
        return self.build_record().to_dict()

    def _accept_validated(self) -> None:
        try:
            record = self.build_record()
        except (TypeError, ValueError) as exc:
            self._record = None
            self._error.setText(str(exc))
            self._error.setVisible(True)
            return
        self._record = record
        self._error.clear()
        self._error.setVisible(False)
        super().accept()


__all__ = ["ScientificReviewDialog"]
