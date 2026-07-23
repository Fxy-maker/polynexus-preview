"""Compact batch name editor for generated-chart legends."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from ..i18n import tr


class LegendSeriesNameDialog(QDialog):
    """Edit the names represented by one generated legend in a single action."""

    def __init__(self, series: Sequence[dict], parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(tr("EDITOR_LEGEND_EDIT_TITLE"))
        self.setMinimumWidth(340)
        self._name_edits: list[QLineEdit] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("EDITOR_LEGEND_EDIT_DESCRIPTION"), self))
        form = QFormLayout()
        for index, item in enumerate(series, start=1):
            edit = QLineEdit(str(item.get("name") or ""), self)
            edit.setObjectName(f"legend-series-name-{index}")
            form.addRow(tr("EDITOR_LEGEND_SERIES_LABEL", index), edit)
            self._name_edits.append(edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        ok_button = buttons.button(QDialogButtonBox.Ok)
        if ok_button is not None:
            ok_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self._name_edits:
            self._name_edits[0].setFocus()
            self._name_edits[0].selectAll()

    def names(self) -> tuple[str, ...]:
        """Return trimmed editor values in their displayed series order."""

        return tuple(edit.text().strip() for edit in self._name_edits)
