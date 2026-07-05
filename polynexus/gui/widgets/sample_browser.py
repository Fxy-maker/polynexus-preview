"""PolyNexus sample browser widget."""

import csv
import os
from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..import_suggestions import suggest_import
from ..i18n import tr

TECHNIQUE_OPTIONS = ("saxs", "waxs", "dsc", "ir", "nmr")
_WINDOWS_FILENAME_FORBIDDEN = '<>:"/\\|?*'


def _suggested_technique_for_path(file_path: str) -> str:
    suggestion = suggest_import(file_path, is_dir=False)
    technique = str(getattr(suggestion, "technique", "") or "").strip().lower() if suggestion else ""
    return technique if technique in TECHNIQUE_OPTIONS else ""


def _safe_export_stem(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "sample"
    sanitized = "".join(" " if char in _WINDOWS_FILENAME_FORBIDDEN else char for char in text)
    sanitized = " ".join(sanitized.split()).strip(" ._")
    sanitized = sanitized.replace(" ", "_")
    return sanitized or "sample"


class CreateSampleDialog(QDialog):
    """Minimal dialog for creating a sample library entry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("SAMPLE_CREATE_TITLE"))
        self.setModal(True)
        self.resize(420, 140)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        self._name_input = QLineEdit()
        self._name_input.textChanged.connect(self._update_accept_state)
        self._aliases_input = QLineEdit()
        form.addRow(tr("SAMPLE_CREATE_NAME"), self._name_input)
        form.addRow(tr("SAMPLE_CREATE_ALIASES"), self._aliases_input)
        layout.addLayout(form)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        ok_button = self._buttons.button(QDialogButtonBox.Ok)
        cancel_button = self._buttons.button(QDialogButtonBox.Cancel)
        if ok_button is not None:
            ok_button.setText(tr("SAMPLE_CREATE_CONFIRM"))
            self._ok_button = ok_button
        if cancel_button is not None:
            cancel_button.setText(tr("COMMON_CANCEL"))
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_input.setFocus(Qt.TabFocusReason)
        self._update_accept_state()

    def sample_name(self) -> str:
        return self._name_input.text().strip()

    def aliases(self) -> list[str]:
        raw = self._aliases_input.text().strip()
        if not raw:
            return []
        normalized = raw.replace(";", ",").replace("\uff0c", ",").replace("\uff1b", ",")
        return [part.strip() for part in normalized.split(",") if part.strip()]

    def _update_accept_state(self):
        ok_button = getattr(self, "_ok_button", None)
        if ok_button is None:
            return
        ok_button.setEnabled(bool(self.sample_name()))


class EditSampleDialog(QDialog):
    """Minimal dialog for editing an existing sample entry."""

    def __init__(self, sample_name="", aliases=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("SAMPLE_EDIT_TITLE"))
        self.setModal(True)
        self.resize(420, 140)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        self._name_input = QLineEdit(str(sample_name or ""))
        self._name_input.textChanged.connect(self._update_accept_state)
        aliases_text = ", ".join(
            str(item).strip() for item in (aliases or []) if str(item).strip()
        )
        self._aliases_input = QLineEdit(aliases_text)
        form.addRow(tr("SAMPLE_CREATE_NAME"), self._name_input)
        form.addRow(tr("SAMPLE_CREATE_ALIASES"), self._aliases_input)
        layout.addLayout(form)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        ok_button = self._buttons.button(QDialogButtonBox.Ok)
        cancel_button = self._buttons.button(QDialogButtonBox.Cancel)
        if ok_button is not None:
            ok_button.setText(tr("SAMPLE_EDIT_CONFIRM"))
            self._ok_button = ok_button
        if cancel_button is not None:
            cancel_button.setText(tr("COMMON_CANCEL"))
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._name_input.setFocus(Qt.TabFocusReason)
        self._name_input.selectAll()
        self._update_accept_state()

    def sample_name(self) -> str:
        return self._name_input.text().strip()

    def aliases(self) -> list[str]:
        raw = self._aliases_input.text().strip()
        if not raw:
            return []
        normalized = raw.replace(";", ",").replace("\uff0c", ",").replace("\uff1b", ",")
        return [part.strip() for part in normalized.split(",") if part.strip()]

    def _update_accept_state(self):
        ok_button = getattr(self, "_ok_button", None)
        if ok_button is None:
            return
        ok_button.setEnabled(bool(self.sample_name()))


class CreateBatchDialog(QDialog):
    """Minimal dialog for creating a batch and attaching one raw file."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("SAMPLE_BATCH_CREATE_TITLE"))
        self.setModal(True)
        self.resize(520, 190)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        self._label_input = QLineEdit()
        self._label_input.textChanged.connect(self._update_accept_state)
        self._technique_combo = QComboBox()
        self._technique_auto_detect_enabled = True
        self._auto_updating_technique = False
        for technique in TECHNIQUE_OPTIONS:
            self._technique_combo.addItem(technique.upper(), technique)
        self._technique_combo.currentIndexChanged.connect(self._on_technique_changed)

        self._file_input = QLineEdit()
        self._file_input.setReadOnly(True)
        self._btn_browse = QPushButton(tr("SAMPLE_BATCH_CREATE_BROWSE"))
        self._btn_browse.clicked.connect(self._browse_file)

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(6)
        file_layout.addWidget(self._file_input, 1)
        file_layout.addWidget(self._btn_browse)

        form.addRow(tr("SAMPLE_BATCH_CREATE_LABEL"), self._label_input)
        form.addRow(tr("SAMPLE_BATCH_CREATE_TECHNIQUE"), self._technique_combo)
        form.addRow(tr("SAMPLE_BATCH_CREATE_FILE"), file_row)
        layout.addLayout(form)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        ok_button = self._buttons.button(QDialogButtonBox.Ok)
        cancel_button = self._buttons.button(QDialogButtonBox.Cancel)
        if ok_button is not None:
            ok_button.setText(tr("SAMPLE_BATCH_CREATE_CONFIRM"))
            self._ok_button = ok_button
        if cancel_button is not None:
            cancel_button.setText(tr("COMMON_CANCEL"))
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._label_input.setFocus(Qt.TabFocusReason)
        self._update_accept_state()

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("FILE_DIALOG_DATA"),
            self._browse_start_dir(),
            "All Files (*.*)",
        )
        if file_path:
            self._file_input.setText(file_path)
            if not self._label_input.text().strip():
                self._label_input.setText(Path(file_path).stem or "")
            self._apply_suggested_technique(file_path)
            self._update_accept_state()

    def _browse_start_dir(self) -> str:
        current_path = self._file_input.text().strip()
        if not current_path:
            return ""
        path = Path(current_path)
        return str(path if path.is_dir() else path.parent)

    def batch_label(self) -> str:
        return self._label_input.text().strip()

    def technique(self) -> str:
        return self._technique_combo.currentData() or "saxs"

    def file_path(self) -> str:
        return self._file_input.text().strip()

    def _on_technique_changed(self, _index):
        if not self._auto_updating_technique:
            self._technique_auto_detect_enabled = False

    def _apply_suggested_technique(self, file_path: str):
        if not self._technique_auto_detect_enabled:
            return
        technique = _suggested_technique_for_path(file_path)
        if not technique:
            return
        target_index = self._technique_combo.findData(technique)
        if target_index < 0:
            return
        self._auto_updating_technique = True
        try:
            self._technique_combo.setCurrentIndex(target_index)
        finally:
            self._auto_updating_technique = False

    def _update_accept_state(self):
        ok_button = getattr(self, "_ok_button", None)
        if ok_button is None:
            return
        ok_button.setEnabled(bool(self.batch_label()) and bool(self.file_path()))


class EditBatchDialog(QDialog):
    """Minimal dialog for editing a batch and one attached file."""

    def __init__(self, batch, files, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("SAMPLE_BATCH_EDIT_TITLE"))
        self.setModal(True)
        self.resize(560, 240)

        self._files = list(files or [])

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        condition_values = batch.get("condition_values") if isinstance(batch, dict) else {}
        if not isinstance(condition_values, dict):
            condition_values = {}

        self._label_input = QLineEdit(str(batch.get("label", "") or ""))
        self._label_input.textChanged.connect(self._update_accept_state)
        self._technique_combo = QComboBox()
        self._technique_auto_detect_enabled = True
        self._auto_updating_technique = False
        selected_technique = str(
            condition_values.get("technique")
            or (self._files[0].get("technique") if self._files else "")
            or ""
        ).strip().lower()
        selected_index = 0
        for index, technique in enumerate(TECHNIQUE_OPTIONS):
            self._technique_combo.addItem(technique.upper(), technique)
            if technique == selected_technique:
                selected_index = index
        self._technique_combo.setCurrentIndex(selected_index)
        self._technique_combo.currentIndexChanged.connect(self._on_technique_changed)

        self._file_combo = QComboBox()
        if self._files:
            for file_row in self._files:
                file_path = str(file_row.get("file_path", "") or "")
                self._file_combo.addItem(Path(file_path).name or "-", file_row.get("id"))
        else:
            self._file_combo.addItem(tr("SAMPLE_BATCH_EDIT_NO_FILE"), None)
            self._file_combo.setEnabled(False)

        self._file_input = QLineEdit()
        self._file_input.setReadOnly(True)
        self._btn_browse = QPushButton(tr("SAMPLE_BATCH_CREATE_BROWSE"))
        self._btn_browse.clicked.connect(self._browse_file)
        self._remove_file = QCheckBox(tr("SAMPLE_BATCH_EDIT_REMOVE_FILE"))
        self._remove_file.toggled.connect(self._on_remove_toggled)

        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(6)
        file_layout.addWidget(self._file_input, 1)
        file_layout.addWidget(self._btn_browse)

        form.addRow(tr("SAMPLE_BATCH_CREATE_LABEL"), self._label_input)
        form.addRow(tr("SAMPLE_BATCH_CREATE_TECHNIQUE"), self._technique_combo)
        form.addRow(tr("SAMPLE_BATCH_EDIT_TARGET_FILE"), self._file_combo)
        form.addRow(tr("SAMPLE_BATCH_EDIT_REPLACE_FILE"), file_row)
        form.addRow("", self._remove_file)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if ok_button is not None:
            ok_button.setText(tr("SAMPLE_BATCH_EDIT_CONFIRM"))
            self._ok_button = ok_button
        if cancel_button is not None:
            cancel_button.setText(tr("COMMON_CANCEL"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._label_input.setFocus(Qt.TabFocusReason)
        self._label_input.selectAll()
        self._update_accept_state()

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("FILE_DIALOG_DATA"),
            self._browse_start_dir(),
            "All Files (*.*)",
        )
        if file_path:
            self._file_input.setText(file_path)
            self._remove_file.setChecked(False)
            self._apply_suggested_technique(file_path)
            self._update_accept_state()

    def _browse_start_dir(self) -> str:
        current_path = self._file_input.text().strip()
        if current_path:
            path = Path(current_path)
            return str(path if path.is_dir() else path.parent)
        target_file_id = self.target_file_id()
        for file_row in self._files:
            if file_row.get("id") == target_file_id:
                file_path = str(file_row.get("file_path", "") or "").strip()
                if file_path:
                    return str(Path(file_path).parent)
        if self._files:
            first_path = str(self._files[0].get("file_path", "") or "").strip()
            if first_path:
                return str(Path(first_path).parent)
        return ""

    def _on_remove_toggled(self, checked):
        self._file_input.setEnabled(not checked)
        self._btn_browse.setEnabled(not checked)
        if checked:
            self._file_input.clear()
        self._update_accept_state()

    def batch_label(self) -> str:
        return self._label_input.text().strip()

    def technique(self) -> str:
        return str(self._technique_combo.currentData() or "saxs")

    def target_file_id(self):
        return self._file_combo.currentData()

    def replacement_file_path(self) -> str:
        return self._file_input.text().strip()

    def should_remove_file(self) -> bool:
        return self._remove_file.isChecked()

    def _on_technique_changed(self, _index):
        if not self._auto_updating_technique:
            self._technique_auto_detect_enabled = False

    def _apply_suggested_technique(self, file_path: str):
        if not self._technique_auto_detect_enabled:
            return
        technique = _suggested_technique_for_path(file_path)
        if not technique:
            return
        target_index = self._technique_combo.findData(technique)
        if target_index < 0:
            return
        self._auto_updating_technique = True
        try:
            self._technique_combo.setCurrentIndex(target_index)
        finally:
            self._auto_updating_technique = False

    def _update_accept_state(self):
        ok_button = getattr(self, "_ok_button", None)
        if ok_button is None:
            return
        ok_button.setEnabled(bool(self.batch_label()))


class BatchDetailsDialog(QDialog):
    """Read-only batch details dialog for attached files and analysis runs."""

    def __init__(self, batch_label, files, runs, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("SAMPLE_BATCH_DETAILS_TITLE", batch_label))
        self.resize(860, 520)
        self._files = list(files or [])
        self._runs = list(runs or [])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        files_label = QLabel(tr("SAMPLE_BATCH_DETAILS_FILES"))
        files_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(files_label)

        self._files_table = QTableWidget()
        self._files_table.setColumnCount(3)
        self._files_table.setHorizontalHeaderLabels(
            [
                tr("SAMPLE_BATCH_DETAILS_COL_FILE"),
                tr("SAMPLE_BATCH_DETAILS_COL_TECHNIQUE"),
                tr("SAMPLE_BATCH_DETAILS_COL_PATH"),
            ]
        )
        self._files_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._files_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._files_table.setAlternatingRowColors(True)
        self._files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._files_table.horizontalHeader().setStretchLastSection(True)
        self._files_table.setRowCount(max(1, len(self._files)))
        if self._files:
            for row_index, file_row in enumerate(self._files):
                file_path = str(file_row.get("file_path", "") or "")
                self._files_table.setItem(
                    row_index,
                    0,
                    QTableWidgetItem(Path(file_path).name or "-"),
                )
                self._files_table.setItem(
                    row_index,
                    1,
                    QTableWidgetItem(str(file_row.get("technique", "") or "").upper()),
                )
                self._files_table.setItem(
                    row_index,
                    2,
                    QTableWidgetItem(file_path),
                )
        else:
            empty_item = QTableWidgetItem(tr("SAMPLE_BATCH_DETAILS_EMPTY_FILES"))
            self._files_table.setItem(0, 0, empty_item)
        self._files_table.itemDoubleClicked.connect(self._on_files_table_double_clicked)
        self._files_table.itemActivated.connect(self._on_files_table_double_clicked)
        self._copy_files_shortcut = QShortcut(QKeySequence.Copy, self._files_table)
        self._copy_files_shortcut.activated.connect(self._copy_file_paths)
        layout.addWidget(self._files_table, 1)

        file_actions = QHBoxLayout()
        file_actions.setContentsMargins(0, 0, 0, 0)
        file_actions.setSpacing(8)
        self._copy_paths_button = QPushButton(tr("SAMPLE_BATCH_DETAILS_COPY_PATHS"))
        self._copy_paths_button.setToolTip(
            tr("SAMPLE_BATCH_DETAILS_COPY_PATHS_TOOLTIP")
            + "\n"
            + tr("SAMPLE_BATCH_DETAILS_COPY_PATHS_SELECTION_HINT")
        )
        self._copy_paths_button.clicked.connect(self._copy_file_paths)
        file_actions.addWidget(self._copy_paths_button)
        self._open_folder_button = QPushButton(tr("SAMPLE_BATCH_DETAILS_OPEN_FOLDER"))
        self._open_folder_button.setToolTip(tr("SAMPLE_BATCH_DETAILS_OPEN_FOLDER_TOOLTIP"))
        self._open_folder_button.clicked.connect(self._open_first_file_folder)
        file_actions.addWidget(self._open_folder_button)
        file_actions.addStretch(1)
        layout.addLayout(file_actions)

        runs_label = QLabel(tr("SAMPLE_BATCH_DETAILS_RUNS"))
        runs_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(runs_label)

        self._runs_table = QTableWidget()
        self._runs_table.setColumnCount(5)
        self._runs_table.setHorizontalHeaderLabels(
            [
                tr("SAMPLE_BATCH_DETAILS_COL_TIME"),
                tr("SAMPLE_BATCH_DETAILS_COL_TECHNIQUE"),
                tr("SAMPLE_BATCH_DETAILS_COL_SUBMODULE"),
                tr("SAMPLE_BATCH_DETAILS_COL_STATUS"),
                tr("SAMPLE_BATCH_DETAILS_COL_OUTPUT"),
            ]
        )
        self._runs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._runs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._runs_table.setAlternatingRowColors(True)
        self._runs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._runs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._runs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._runs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._runs_table.horizontalHeader().setStretchLastSection(True)
        self._runs_table.setRowCount(max(1, len(self._runs)))
        if self._runs:
            for row_index, run in enumerate(self._runs):
                output_dir = str(run.get("output_dir", "") or "")
                self._runs_table.setItem(
                    row_index,
                    0,
                    QTableWidgetItem(str(run.get("created_at", "") or "")),
                )
                self._runs_table.setItem(
                    row_index,
                    1,
                    QTableWidgetItem(str(run.get("technique", "") or "").upper()),
                )
                self._runs_table.setItem(
                    row_index,
                    2,
                    QTableWidgetItem(str(run.get("submodule", "") or "-")),
                )
                self._runs_table.setItem(
                    row_index,
                    3,
                    QTableWidgetItem(self._run_status_text(run.get("status", ""))),
                )
                self._runs_table.setItem(
                    row_index,
                    4,
                    QTableWidgetItem(output_dir),
                )
        else:
            empty_item = QTableWidgetItem(tr("SAMPLE_BATCH_DETAILS_EMPTY_RUNS"))
            self._runs_table.setItem(0, 0, empty_item)
        self._runs_table.itemDoubleClicked.connect(self._on_runs_table_double_clicked)
        self._runs_table.itemActivated.connect(self._on_runs_table_double_clicked)
        self._copy_runs_shortcut = QShortcut(QKeySequence.Copy, self._runs_table)
        self._copy_runs_shortcut.activated.connect(self._copy_output_dirs)
        layout.addWidget(self._runs_table, 1)

        run_actions = QHBoxLayout()
        run_actions.setContentsMargins(0, 0, 0, 0)
        run_actions.setSpacing(8)
        self._copy_outputs_button = QPushButton(tr("SAMPLE_BATCH_DETAILS_COPY_OUTPUTS"))
        self._copy_outputs_button.setToolTip(
            tr("SAMPLE_BATCH_DETAILS_COPY_OUTPUTS_TOOLTIP")
            + "\n"
            + tr("SAMPLE_BATCH_DETAILS_COPY_OUTPUTS_SELECTION_HINT")
        )
        self._copy_outputs_button.clicked.connect(self._copy_output_dirs)
        run_actions.addWidget(self._copy_outputs_button)
        self._open_output_button = QPushButton(tr("SAMPLE_BATCH_DETAILS_OPEN_OUTPUT"))
        self._open_output_button.setToolTip(tr("SAMPLE_BATCH_DETAILS_OPEN_OUTPUT_TOOLTIP"))
        self._open_output_button.clicked.connect(self._open_selected_output_dir)
        run_actions.addWidget(self._open_output_button)
        run_actions.addStretch(1)
        layout.addLayout(run_actions)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(tr("COMMON_CANCEL"))
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        has_files = bool(self._files)
        self._copy_paths_button.setEnabled(has_files)
        self._open_folder_button.setEnabled(has_files)
        self._runs_table.itemSelectionChanged.connect(self._update_run_actions)
        self._update_run_actions()
        if has_files:
            self._files_table.setFocus(Qt.TabFocusReason)

    def _run_status_text(self, status):
        key = {
            "completed": "SAMPLE_RUN_STATUS_COMPLETED",
            "pending": "SAMPLE_RUN_STATUS_PENDING",
            "failed": "SAMPLE_RUN_STATUS_FAILED",
        }.get(str(status or "").strip().lower(), "SAMPLE_RUN_STATUS_UNKNOWN")
        return tr(key)

    def _copy_file_paths(self):
        paths = self._selected_file_paths()
        if not paths:
            paths = [
                str(file_row.get("file_path", "") or "").strip()
                for file_row in getattr(self, "_files", [])
                if str(file_row.get("file_path", "") or "").strip()
            ]
        if paths:
            QApplication.clipboard().setText("\n".join(paths))

    def _open_first_file_folder(self):
        paths = self._selected_file_paths()
        if not paths:
            paths = [
                str(file_row.get("file_path", "") or "").strip()
                for file_row in getattr(self, "_files", [])
                if str(file_row.get("file_path", "") or "").strip()
            ]
        if not paths:
            return
        try:
            os.startfile(str(Path(paths[0]).parent))
        except OSError:
            pass

    def _on_files_table_double_clicked(self, item):
        if item is None:
            return
        row = item.row()
        if 0 <= row < len(self._files):
            file_path = str(self._files[row].get("file_path", "") or "").strip()
            if file_path:
                try:
                    os.startfile(str(Path(file_path).parent))
                except OSError:
                    pass

    def _selected_file_paths(self):
        indexes = self._files_table.selectionModel().selectedRows() if self._files_table.selectionModel() else []
        paths = []
        for index in indexes:
            row = index.row()
            if 0 <= row < len(self._files):
                file_path = str(self._files[row].get("file_path", "") or "").strip()
                if file_path:
                    paths.append(file_path)
        return paths

    def _run_output_dirs(self):
        return [
            str(run.get("output_dir", "") or "").strip()
            for run in getattr(self, "_runs", [])
            if str(run.get("output_dir", "") or "").strip()
        ]

    def _selected_run_output_dirs(self):
        indexes = self._runs_table.selectionModel().selectedRows() if self._runs_table.selectionModel() else []
        output_dirs = []
        for index in indexes:
            row = index.row()
            if 0 <= row < len(self._runs):
                output_dir = str(self._runs[row].get("output_dir", "") or "").strip()
                if output_dir:
                    output_dirs.append(output_dir)
        return output_dirs

    def _selected_run_output_dir(self):
        selected = self._selected_run_output_dirs()
        if selected:
            return selected[0]
        output_dirs = self._run_output_dirs()
        return output_dirs[0] if output_dirs else ""

    def _update_run_actions(self):
        has_outputs = bool(self._run_output_dirs())
        selected_output = bool(self._selected_run_output_dir())
        self._copy_outputs_button.setEnabled(has_outputs)
        self._open_output_button.setEnabled(selected_output)

    def _copy_output_dirs(self):
        output_dirs = self._selected_run_output_dirs() or self._run_output_dirs()
        if output_dirs:
            QApplication.clipboard().setText("\n".join(output_dirs))

    def _open_selected_output_dir(self):
        output_dir = self._selected_run_output_dir()
        if not output_dir:
            return
        try:
            os.startfile(output_dir)
        except OSError:
            pass

    def _on_runs_table_double_clicked(self, item):
        if item is None:
            return
        row = item.row()
        if 0 <= row < len(self._runs):
            output_dir = str(self._runs[row].get("output_dir", "") or "").strip()
            if output_dir:
                try:
                    os.startfile(output_dir)
                except OSError:
                    pass


class SampleBrowser(QWidget):
    """Sample database browser with search, filter, and batch selection."""

    sample_selected = Signal(str)
    sample_created = Signal(str)
    sample_updated = Signal(str)
    batch_created = Signal(str, str)
    batch_updated = Signal(str)
    batch_analysis_requested = Signal(str)
    joint_analysis_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("PolyNexus", "PolyNexus")
        self._db = None
        self._samples = []
        self._selected_sample_id = None
        self._batch_checkboxes = {}
        self._build_ui()

    def set_db(self, sample_db):
        self._db = sample_db
        self.refresh()

    def refresh(self):
        self._refresh()

    def select_sample(self, sample_id):
        if not sample_id:
            self._table.clearSelection()
            self._selected_sample_id = None
            self._clear_batches()
            return False

        for row_index, sample in enumerate(self._samples):
            if sample.get("id") == sample_id:
                self._table.selectRow(row_index)
                self._table.setCurrentCell(row_index, 0)
                self._selected_sample_id = sample_id
                self.sample_selected.emit(sample_id)
                self._populate_batches(sample_id)
                return True

        self._table.clearSelection()
        self._selected_sample_id = None
        self._clear_batches()
        return False

    def create_batch_with_file(self, sample_id, batch_label, technique, file_path):
        if self._db is None:
            raise RuntimeError(tr("SAMPLE_CREATE_DB_MISSING"))
        if not sample_id:
            raise ValueError(tr("SAMPLE_BATCH_HINT"))

        label = batch_label.strip()
        path = Path(file_path).expanduser()
        if not label:
            raise ValueError(tr("SAMPLE_BATCH_NAME_REQUIRED"))
        if not file_path.strip():
            raise ValueError(tr("SAMPLE_BATCH_FILE_REQUIRED"))
        if not path.exists():
            raise FileNotFoundError(tr("SAMPLE_BATCH_FILE_MISSING"))

        existing_file_batch = self._db.find_batch_by_file(
            sample_id,
            str(path.resolve()),
            technique=technique,
        )
        if existing_file_batch is not None:
            raise ValueError(
                tr(
                    "SAMPLE_BATCH_FILE_DUPLICATE",
                    existing_file_batch.get("label", "") or "-",
                )
            )

        for batch in self._db.get_batches(sample_id):
            existing_label = str(batch.get("label", "")).strip().lower()
            if existing_label == label.lower():
                raise ValueError(tr("SAMPLE_BATCH_DUPLICATE"))

        batch_id = self._db.create_batch(
            sample_id,
            label,
            instrument=technique.upper(),
            condition_type="raw_data",
            condition_values={"technique": technique},
        )
        self._db.add_data_file(
            batch_id,
            str(path.resolve()),
            technique,
            file_type=path.suffix.lower().lstrip("."),
            import_order=0,
        )
        return batch_id, str(path.resolve())

    def update_sample_entry(self, sample_id, sample_name, aliases=None):
        if self._db is None:
            raise RuntimeError(tr("SAMPLE_CREATE_DB_MISSING"))
        if not sample_id:
            raise ValueError(tr("SAMPLE_EDIT_SELECT_FIRST"))

        name = str(sample_name or "").strip()
        if not name:
            raise ValueError(tr("SAMPLE_CREATE_NAME_REQUIRED"))

        existing = self._db.find_sample_by_name(name)
        if existing and existing.get("id") != sample_id:
            raise ValueError(tr("SAMPLE_EDIT_DUPLICATE"))

        sample = self._db.get_sample(sample_id)
        if sample is None:
            raise ValueError(tr("SAMPLE_EDIT_MISSING"))

        self._db.update_sample(
            sample_id,
            polymer_name=name,
            aliases=list(aliases or []),
        )
        return name

    def update_batch_entry(
        self,
        batch_id,
        batch_label,
        technique,
        *,
        target_file_id=None,
        replacement_file_path="",
        remove_file=False,
    ):
        if self._db is None:
            raise RuntimeError(tr("SAMPLE_CREATE_DB_MISSING"))
        if not batch_id:
            raise ValueError(tr("SAMPLE_BATCH_EDIT_SELECT_FIRST"))

        batch = self._db.get_batch(batch_id)
        if batch is None:
            raise ValueError(tr("SAMPLE_BATCH_EDIT_MISSING"))

        label = str(batch_label or "").strip()
        if not label:
            raise ValueError(tr("SAMPLE_BATCH_NAME_REQUIRED"))

        sample_id = str(batch.get("sample_id", "") or "")
        for existing_batch in self._db.get_batches(sample_id):
            if existing_batch.get("id") == batch_id:
                continue
            existing_label = str(existing_batch.get("label", "") or "").strip().lower()
            if existing_label == label.lower():
                raise ValueError(tr("SAMPLE_BATCH_DUPLICATE"))

        technique = str(technique or "").strip().lower() or "saxs"
        files = self._db.get_data_files(batch_id)
        target_file = None
        if target_file_id is not None:
            for file_row in files:
                if file_row.get("id") == target_file_id:
                    target_file = file_row
                    break

        replacement_path = str(replacement_file_path or "").strip()
        resolved_replacement = ""
        if replacement_path:
            path_obj = Path(replacement_path).expanduser()
            if not path_obj.exists():
                raise FileNotFoundError(tr("SAMPLE_BATCH_FILE_MISSING"))
            resolved_replacement = str(path_obj.resolve())

        if remove_file and resolved_replacement:
            raise ValueError(tr("SAMPLE_BATCH_EDIT_CONFLICT"))

        if resolved_replacement:
            existing_file_batch = self._db.find_batch_by_file(sample_id, resolved_replacement)
            if existing_file_batch is not None and existing_file_batch.get("id") != batch_id:
                raise ValueError(
                    tr(
                        "SAMPLE_BATCH_FILE_DUPLICATE",
                        existing_file_batch.get("label", "") or "-",
                    )
                )

            if target_file is None:
                self._db.add_data_file(
                    batch_id,
                    resolved_replacement,
                    technique,
                    file_type=Path(resolved_replacement).suffix.lower().lstrip("."),
                    import_order=len(files),
                )
            else:
                duplicate_within_batch = any(
                    item.get("id") != target_file.get("id")
                    and str(Path(str(item.get("file_path", "") or "")).expanduser().resolve()) == resolved_replacement
                    for item in files
                )
                if duplicate_within_batch:
                    raise ValueError(tr("SAMPLE_BATCH_EDIT_SAME_FILE"))
                self._db.update_data_file(
                    target_file.get("id"),
                    file_path=resolved_replacement,
                    technique=technique,
                    file_type=Path(resolved_replacement).suffix.lower().lstrip("."),
                )
        elif remove_file and target_file is not None:
            self._db.remove_data_file(target_file.get("id"))

        condition_values = batch.get("condition_values") if isinstance(batch.get("condition_values"), dict) else {}
        condition_values = dict(condition_values or {})
        condition_values["technique"] = technique
        self._db.update_batch(
            batch_id,
            label=label,
            instrument=technique.upper(),
            condition_values=condition_values,
        )

        refreshed_files = self._db.get_data_files(batch_id)
        for file_row in refreshed_files:
            if str(file_row.get("technique", "") or "").strip().lower() != technique:
                self._db.update_data_file(file_row.get("id"), technique=technique)

        return label

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        bar = QHBoxLayout()
        bar.setSpacing(6)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(tr("SAMPLE_SEARCH_PLACEHOLDER"))
        self._search_input.textChanged.connect(self._on_search)
        self._search_input.installEventFilter(self)
        bar.addWidget(self._search_input, 2)
        self._search_shortcut = QShortcut(QKeySequence.Find, self)
        self._search_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self._search_shortcut.activated.connect(self._focus_search_input)

        self._family_combo = QComboBox()
        self._family_combo.addItem(tr("SAMPLE_FAMILY_ALL"), None)
        for family in [
            "polyolefin",
            "polyamide",
            "polyester",
            "fluoropolymer",
            "engineering_plastic",
            "elastomer",
            "specialty",
        ]:
            self._family_combo.addItem(family, family)
        self._family_combo.currentIndexChanged.connect(self._on_search)
        bar.addWidget(self._family_combo)

        self._btn_new = QPushButton(tr("SAMPLE_NEW"))
        self._btn_new.clicked.connect(self._on_new_sample)
        bar.addWidget(self._btn_new)

        self._btn_edit = QPushButton(tr("SAMPLE_EDIT"))
        self._btn_edit.clicked.connect(self._on_edit_sample)
        bar.addWidget(self._btn_edit)

        self._btn_new_batch = QPushButton(tr("SAMPLE_BATCH_NEW"))
        self._btn_new_batch.clicked.connect(self._on_new_batch)
        bar.addWidget(self._btn_new_batch)

        layout.addLayout(bar)

        self._empty_state = QLabel(tr("SAMPLE_EMPTY_RESULTS"))
        self._empty_state.setStyleSheet("color: #8a94a6; font-size: 12px;")
        self._empty_state.setWordWrap(True)
        self._empty_state.setVisible(False)
        layout.addWidget(self._empty_state)

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._set_table_headers()
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table.setColumnWidth(0, 120)
        self._table.setColumnWidth(1, 100)
        self._table.setColumnWidth(2, 160)
        self._table.itemSelectionChanged.connect(self._on_table_selection)
        self._table.itemDoubleClicked.connect(self._on_table_item_double_clicked)
        self._table.itemActivated.connect(self._on_table_item_double_clicked)
        self._table_copy_shortcut = QShortcut(QKeySequence.Copy, self._table)
        self._table_copy_shortcut.activated.connect(self._copy_selected_samples_to_clipboard)
        splitter.addWidget(self._table)

        batch_panel = QWidget()
        batch_layout = QVBoxLayout(batch_panel)
        batch_layout.setContentsMargins(0, 8, 0, 0)
        batch_layout.setSpacing(6)

        self._batch_label = QLabel(tr("SAMPLE_BATCH_HINT"))
        self._batch_label.setStyleSheet("font-weight: 600; font-size: 12px;")
        batch_layout.addWidget(self._batch_label)

        self._batch_list = QListWidget()
        self._batch_list.setMaximumHeight(220)
        self._batch_list.itemDoubleClicked.connect(self._on_batch_item_double_clicked)
        self._batch_list.itemActivated.connect(self._on_batch_item_double_clicked)
        batch_layout.addWidget(self._batch_list)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self._btn_select_all = QPushButton(tr("SAMPLE_SELECT_ALL"))
        self._btn_select_all.clicked.connect(self._select_all_batches)
        action_bar.addWidget(self._btn_select_all)

        self._btn_joint = QPushButton(tr("SAMPLE_JOINT"))
        self._btn_joint.setStyleSheet(
            "QPushButton { background-color: #0078d4; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: 600; }"
            "QPushButton:hover { background-color: #106ebe; }"
        )
        self._btn_joint.clicked.connect(self._on_joint_analysis)
        action_bar.addWidget(self._btn_joint)

        action_bar.addStretch()

        self._btn_export = QPushButton(tr("SAMPLE_EXPORT_REPORT"))
        self._btn_export.clicked.connect(self._on_export)
        action_bar.addWidget(self._btn_export)
        batch_layout.addLayout(action_bar)

        splitter.addWidget(batch_panel)
        splitter.setSizes([400, 180])
        layout.addWidget(splitter, 1)

        self._update_batch_actions()

    def _set_table_headers(self):
        self._table.setHorizontalHeaderLabels(
            [
                tr("SAMPLE_NAME"),
                tr("SAMPLE_FAMILY"),
                tr("SAMPLE_ALIASES"),
                tr("SAMPLE_BATCH_COUNT"),
                tr("SAMPLE_LAST_ANALYSIS"),
            ]
        )

    def _copy_selected_samples_to_clipboard(self):
        table = self._table
        cols = table.columnCount()
        rows = table.rowCount()
        if cols <= 0 or rows <= 0:
            return

        headers = []
        for col in range(cols):
            header_item = table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item is not None else "")

        selection = table.selectionModel()
        selected_rows = []
        if selection is not None:
            selected_rows = sorted(index.row() for index in selection.selectedRows())
        row_indexes = selected_rows if selected_rows else list(range(rows))

        lines = ["\t".join(headers)]
        for row in row_indexes:
            values = []
            for col in range(cols):
                item = table.item(row, col)
                values.append(item.text() if item is not None else "")
            lines.append("\t".join(values))

        QApplication.clipboard().setText("\n".join(lines))

    def retranslate(self):
        self._search_input.setPlaceholderText(tr("SAMPLE_SEARCH_PLACEHOLDER"))
        if self._family_combo.count() > 0:
            self._family_combo.setItemText(0, tr("SAMPLE_FAMILY_ALL"))
        self._btn_new.setText(tr("SAMPLE_NEW"))
        self._btn_edit.setText(tr("SAMPLE_EDIT"))
        self._btn_new_batch.setText(tr("SAMPLE_BATCH_NEW"))
        self._btn_joint.setText(tr("SAMPLE_JOINT"))
        self._btn_export.setText(tr("SAMPLE_EXPORT_REPORT"))
        self._empty_state.setText(tr("SAMPLE_EMPTY_RESULTS"))
        self._set_table_headers()
        self._refresh_batch_label()
        self._update_select_all_button_text()

    def _refresh(self):
        if self._db is None:
            self._samples = []
            self._table.setRowCount(0)
            self._clear_batches()
            return

        previous_sample_id = self._selected_sample_id
        family = self._family_combo.currentData()
        search = self._search_input.text().strip() or None
        self._samples = self._db.list_samples(family=family, search=search)

        self._table.setRowCount(len(self._samples))
        for row_index, sample in enumerate(self._samples):
            self._table.setItem(
                row_index,
                0,
                QTableWidgetItem(sample.get("polymer_name", "")),
            )
            self._table.setItem(
                row_index,
                1,
                QTableWidgetItem(sample.get("family", "") or ""),
            )
            aliases = sample.get("aliases", [])
            alias_text = ", ".join(aliases[:3]) if isinstance(aliases, list) else str(aliases)
            self._table.setItem(row_index, 2, QTableWidgetItem(alias_text))
            batch_count = len(self._db.get_batches(sample.get("id", "")))
            self._table.setItem(row_index, 3, QTableWidgetItem(str(batch_count)))
            updated = str(sample.get("updated_at", ""))[:10]
            self._table.setItem(row_index, 4, QTableWidgetItem(updated))

        if not self.select_sample(previous_sample_id):
            if len(self._samples) == 1:
                self.select_sample(self._samples[0].get("id"))
            elif self._samples:
                self._table.clearSelection()
                self._selected_sample_id = None
                self._clear_batches()
            else:
                self._selected_sample_id = None
                self._clear_batches()
        self._empty_state.setVisible(not bool(self._samples))

    def _on_search(self):
        self._refresh()

    def _focus_search_input(self):
        self._search_input.setFocus(Qt.ShortcutFocusReason)
        self._search_input.selectAll()

    def eventFilter(self, watched, event):
        if watched is self._search_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape and self._search_input.text():
                self._search_input.clear()
                return True
        return super().eventFilter(watched, event)

    def _on_table_selection(self):
        rows = {index.row() for index in self._table.selectedIndexes()}
        if len(rows) != 1:
            self._selected_sample_id = None
            self._clear_batches()
            return

        row = next(iter(rows))
        if 0 <= row < len(self._samples):
            sample_id = self._samples[row].get("id")
            self._selected_sample_id = sample_id
            self.sample_selected.emit(sample_id)
            self._populate_batches(sample_id)

    def _on_table_item_double_clicked(self, item):
        if item is None:
            return
        row = item.row()
        if 0 <= row < len(self._samples):
            sample_id = self._samples[row].get("id")
            if sample_id:
                self.select_sample(sample_id)
                self._on_edit_sample()

    def _populate_batches(self, sample_id):
        self._clear_batches()
        if self._db is None:
            return

        batches = self._db.get_batches(sample_id)
        sample = self._db.get_sample(sample_id)
        sample_name = sample.get("polymer_name", "") if sample else ""
        self._batch_label.setText(tr("SAMPLE_BATCH_LIST", sample_name, len(batches)))

        for batch in batches:
            batch_id = batch.get("id", "")
            files = self._db.get_data_files(batch_id)
            runs = self._db.get_analysis_runs(batch_id)
            technique = self._batch_technique_label(batch, files)
            source_text = self._batch_source_summary(files)
            status_kind = self._batch_status_kind(files, runs)
            status_text = self._batch_status_text(files, runs)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, batch_id)
            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(4, 2, 4, 2)
            row.setSpacing(8)

            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self._update_batch_actions)
            self._batch_checkboxes[batch_id] = checkbox
            row.addWidget(checkbox)

            text_block = QWidget()
            text_layout = QVBoxLayout(text_block)
            text_layout.setContentsMargins(0, 0, 0, 0)
            text_layout.setSpacing(2)

            label = QLabel(batch.get("label", ""))
            label.setStyleSheet("font-weight: 600;")
            text_layout.addWidget(label)

            meta = QLabel(
                tr(
                    "SAMPLE_BATCH_META",
                    technique,
                    len(files),
                    len(runs),
                )
            )
            meta.setStyleSheet("color: #888; font-size: 11px;")
            text_layout.addWidget(meta)

            source_label = QLabel(source_text)
            source_label.setStyleSheet("color: #9aa4b2; font-size: 11px;")
            file_paths = self._batch_file_paths(files)
            if file_paths:
                source_label.setToolTip("\n".join(file_paths))
            text_layout.addWidget(source_label)

            recent_label = QLabel(self._batch_recent_summary(runs))
            recent_label.setStyleSheet("color: #8fb3ff; font-size: 11px;")
            text_layout.addWidget(recent_label)

            row.addWidget(text_block, 1)

            status_label = QLabel(status_text)
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setMinimumWidth(86)
            status_label.setToolTip(self._batch_recent_summary(runs) if runs else status_text)
            status_label.setStyleSheet(self._batch_status_style(status_kind))
            row.addWidget(status_label)

            btn_analyze = QPushButton(tr("SAMPLE_BATCH_ANALYZE"))
            btn_analyze.setObjectName("secondary_btn")
            btn_analyze.clicked.connect(
                lambda checked=False, current_batch_id=batch_id: self.batch_analysis_requested.emit(current_batch_id)
            )
            row.addWidget(btn_analyze)

            btn_edit = QPushButton(tr("SAMPLE_BATCH_EDIT"))
            btn_edit.setObjectName("secondary_btn")
            btn_edit.clicked.connect(
                lambda checked=False, current_batch_id=batch_id: self._on_edit_batch(current_batch_id)
            )
            row.addWidget(btn_edit)

            btn_details = QPushButton(tr("SAMPLE_BATCH_DETAILS"))
            btn_details.setObjectName("secondary_btn")
            btn_details.clicked.connect(
                lambda checked=False, current_batch_id=batch_id: self._on_view_batch_details(current_batch_id)
            )
            row.addWidget(btn_details)

            created_at = str(batch.get("created_at", ""))[:10]
            date_label = QLabel(created_at)
            date_label.setStyleSheet("color: #888; font-size: 11px;")
            row.addWidget(date_label)

            item.setSizeHint(widget.sizeHint())
            self._batch_list.addItem(item)
            self._batch_list.setItemWidget(item, widget)

        self._update_batch_actions()

    def _batch_technique_label(self, batch, files):
        if files:
            technique = str(files[0].get("technique", "") or "").upper()
            if technique:
                return technique
        condition_values = batch.get("condition_values")
        if isinstance(condition_values, dict):
            technique = str(condition_values.get("technique", "")).upper()
            if technique:
                return technique
        instrument = str(batch.get("instrument", "")).strip()
        return instrument or "-"

    def _batch_source_summary(self, files):
        if not files:
            return tr("SAMPLE_BATCH_STATUS_EMPTY")
        names = [
            Path(str(file_row.get("file_path", "") or "")).name or "-"
            for file_row in files
        ]
        first_name = names[0]
        if len(files) == 1:
            return tr("SAMPLE_BATCH_SOURCE", first_name)
        if len(files) == 2:
            return tr("SAMPLE_BATCH_SOURCE_TWO", names[0], names[1])
        return tr("SAMPLE_BATCH_SOURCE_MULTI", first_name, len(files) - 1)

    def _batch_file_paths(self, files):
        return [
            str(file_row.get("file_path", "")).strip()
            for file_row in files
            if str(file_row.get("file_path", "")).strip()
        ]

    def _batch_status_kind(self, files, runs):
        if runs:
            latest_status = str(runs[0].get("status", "") or "").strip().lower()
            if latest_status in {"pending", "failed"}:
                return latest_status
            return "completed"
        if files:
            return "imported"
        return "empty"

    def _batch_status_text(self, files, runs):
        kind = self._batch_status_kind(files, runs)
        if kind == "completed":
            return tr("SAMPLE_BATCH_STATUS_ANALYZED", len(runs))
        if kind == "pending":
            return tr("SAMPLE_RUN_STATUS_PENDING")
        if kind == "failed":
            return tr("SAMPLE_RUN_STATUS_FAILED")
        if kind == "imported":
            return tr("SAMPLE_BATCH_STATUS_IMPORTED")
        return tr("SAMPLE_BATCH_STATUS_EMPTY")

    def _batch_recent_summary(self, runs):
        if not runs:
            return tr("SAMPLE_BATCH_RECENT_NONE")
        latest = runs[0]
        technique = str(latest.get("technique", "") or "").upper() or "-"
        submodule = str(latest.get("submodule", "") or "").strip()
        if submodule:
            technique = f"{technique} / {submodule}"
        status = self._run_status_text(latest.get("status", ""))
        created_at = str(latest.get("created_at", "") or "")[:10] or "-"
        return tr("SAMPLE_BATCH_RECENT", technique, status, created_at)

    def _run_status_text(self, status):
        key = {
            "completed": "SAMPLE_RUN_STATUS_COMPLETED",
            "pending": "SAMPLE_RUN_STATUS_PENDING",
            "failed": "SAMPLE_RUN_STATUS_FAILED",
        }.get(str(status or "").strip().lower(), "SAMPLE_RUN_STATUS_UNKNOWN")
        return tr(key)

    def _batch_status_style(self, kind):
        if kind == "completed":
            return (
                "QLabel { background: #153e2a; color: #7ee2a8; border: 1px solid #215c3d; "
                "border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600; }"
            )
        if kind == "pending":
            return (
                "QLabel { background: #4a3410; color: #f8d07a; border: 1px solid #7c5a1a; "
                "border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600; }"
            )
        if kind == "failed":
            return (
                "QLabel { background: #4a1f24; color: #ffb4bd; border: 1px solid #8b313b; "
                "border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600; }"
            )
        return (
            "QLabel { background: #2b3340; color: #c7d0dc; border: 1px solid #465264; "
            "border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: 600; }"
        )

    def _batch_details_snapshot(self, batch_id):
        if self._db is None:
            return None
        batch = self._db.get_batch(batch_id)
        if not batch:
            return None
        return {
            "batch": batch,
            "files": self._db.get_data_files(batch_id),
            "runs": self._db.get_analysis_runs(batch_id),
        }

    def _clear_batches(self):
        self._batch_label.setText(tr("SAMPLE_BATCH_HINT"))
        self._batch_list.clear()
        self._batch_checkboxes.clear()
        self._update_batch_actions()

    def _refresh_batch_label(self):
        if self._selected_sample_id:
            self._populate_batches(self._selected_sample_id)
        else:
            self._batch_label.setText(tr("SAMPLE_BATCH_HINT"))
            self._update_batch_actions()

    def _update_batch_actions(self, *args):
        has_sample = bool(self._selected_sample_id and self._db is not None)
        has_batches = bool(self._batch_checkboxes)
        has_checked = bool(self.get_selected_batch_ids())

        self._btn_edit.setEnabled(has_sample)
        self._btn_new_batch.setEnabled(has_sample)
        self._btn_select_all.setEnabled(has_batches)
        self._btn_joint.setEnabled(has_checked)
        self._btn_export.setEnabled(has_sample and has_batches)
        self._update_select_all_button_text()

    def _update_select_all_button_text(self):
        has_batches = bool(self._batch_checkboxes)
        all_checked = has_batches and all(
            checkbox.isChecked() for checkbox in self._batch_checkboxes.values()
        )
        self._btn_select_all.setText(
            tr("SAMPLE_DESELECT_ALL") if all_checked else tr("SAMPLE_SELECT_ALL")
        )

    def _select_all_batches(self):
        check_all = not all(
            checkbox.isChecked() for checkbox in self._batch_checkboxes.values()
        )
        for checkbox in self._batch_checkboxes.values():
            checkbox.setChecked(check_all)
        self._update_batch_actions()

    def _on_joint_analysis(self):
        selected = self.get_selected_batch_ids()
        if selected:
            self.joint_analysis_requested.emit(selected)

    def _on_export(self):
        if self._db is None or not self._selected_sample_id:
            QMessageBox.warning(
                self,
                tr("SAMPLE_EXPORT_REPORT"),
                tr("SAMPLE_EXPORT_NO_SAMPLE"),
            )
            return

        sample = self._db.get_sample(self._selected_sample_id)
        sample_name = str(sample.get("polymer_name", "")).strip() if sample else ""
        suffix = _safe_export_stem(sample_name)
        start_dir = self._last_export_dir()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("SAMPLE_EXPORT_TITLE"),
            str(Path(start_dir) / f"{suffix}_batches.tsv"),
            tr("SAMPLE_EXPORT_FILTER"),
        )
        if not path:
            return

        delimiter = "\t"
        lower_path = path.lower()
        if lower_path.endswith(".csv") or "csv" in str(selected_filter).lower():
            delimiter = ","
            if not lower_path.endswith(".csv"):
                path = f"{path}.csv"
        elif not lower_path.endswith(".tsv"):
            path = f"{path}.tsv"

        batches = self._db.get_batches(self._selected_sample_id)
        rows = []
        for batch in batches:
            batch_id = batch.get("id", "")
            files = self._db.get_data_files(batch_id)
            runs = self._db.get_analysis_runs(batch_id)
            rows.append(
                {
                    "sample": sample_name,
                    "batch": batch.get("label", ""),
                    "technique": self._batch_technique_label(batch, files),
                    "files": len(files),
                    "runs": len(runs),
                    "status": self._batch_status_text(files, runs),
                    "source": self._batch_source_summary(files),
                    "latest": self._batch_recent_summary(runs),
                }
            )

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["sample", "batch", "technique", "files", "runs", "status", "source", "latest"],
                delimiter=delimiter,
            )
            writer.writeheader()
            writer.writerows(rows)

        self._save_last_export_dir(path)
        QMessageBox.information(
            self,
            tr("SAMPLE_EXPORT_REPORT"),
            tr("SAMPLE_EXPORT_DONE", path),
        )

    def _last_export_dir(self) -> str:
        saved = str(self._settings.value("sample_browser/export_dir", "", type=str) or "").strip()
        return saved or str(Path.home())

    def _save_last_export_dir(self, path: str):
        if not path:
            return
        try:
            directory = str(Path(path).expanduser().resolve().parent)
        except OSError:
            directory = str(Path(path).expanduser().parent)
        if directory:
            self._settings.setValue("sample_browser/export_dir", directory)

    def _on_view_batch_details(self, batch_id):
        snapshot = self._batch_details_snapshot(batch_id)
        if not snapshot:
            return
        dialog = BatchDetailsDialog(
            snapshot["batch"].get("label", "") or batch_id,
            snapshot["files"],
            snapshot["runs"],
            self,
        )
        dialog.exec()

    def _on_batch_item_double_clicked(self, item):
        if item is None:
            return
        batch_id = str(item.data(Qt.UserRole) or "").strip()
        if batch_id:
            self._on_view_batch_details(batch_id)

    def _on_edit_batch(self, batch_id):
        if self._db is None:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_EDIT_TITLE"),
                tr("SAMPLE_CREATE_DB_MISSING"),
            )
            return

        snapshot = self._batch_details_snapshot(batch_id)
        if not snapshot:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_EDIT_TITLE"),
                tr("SAMPLE_BATCH_EDIT_MISSING"),
            )
            return

        if snapshot["runs"]:
            QMessageBox.information(
                self,
                tr("SAMPLE_BATCH_EDIT_TITLE"),
                tr("SAMPLE_BATCH_EDIT_RUN_HINT"),
            )

        dialog = EditBatchDialog(snapshot["batch"], snapshot["files"], self)
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            updated_label = self.update_batch_entry(
                batch_id,
                dialog.batch_label(),
                dialog.technique(),
                target_file_id=dialog.target_file_id(),
                replacement_file_path=dialog.replacement_file_path(),
                remove_file=dialog.should_remove_file(),
            )
        except FileNotFoundError as exc:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_EDIT_TITLE"),
                tr("SAMPLE_BATCH_EDIT_FILE_MISSING", str(exc)),
            )
            return
        except ValueError as exc:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_EDIT_TITLE"),
                tr("SAMPLE_BATCH_EDIT_INVALID", str(exc)),
            )
            return
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("SAMPLE_BATCH_EDIT_TITLE"),
                tr("SAMPLE_BATCH_EDIT_FAILED", str(exc)),
            )
            return

        selected_sample_id = self._selected_sample_id
        self._refresh()
        self.select_sample(selected_sample_id)
        self._highlight_batch(batch_id)
        self.batch_updated.emit(updated_label)

    def _on_new_sample(self):
        if self._db is None:
            QMessageBox.warning(
                self,
                tr("SAMPLE_CREATE_TITLE"),
                tr("SAMPLE_CREATE_DB_MISSING"),
            )
            return

        dialog = CreateSampleDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        name = dialog.sample_name()
        if not name:
            QMessageBox.warning(
                self,
                tr("SAMPLE_CREATE_TITLE"),
                tr("SAMPLE_CREATE_NAME_REQUIRED"),
            )
            return

        existing = self._db.find_sample_by_name(name)
        if existing:
            QMessageBox.warning(
                self,
                tr("SAMPLE_CREATE_TITLE"),
                tr("SAMPLE_CREATE_DUPLICATE"),
            )
            self._search_input.blockSignals(True)
            self._family_combo.blockSignals(True)
            self._search_input.clear()
            self._family_combo.setCurrentIndex(0)
            self._search_input.blockSignals(False)
            self._family_combo.blockSignals(False)
            self._refresh()
            self.select_sample(existing.get("id"))
            return

        try:
            sample_id = self._db.create_sample(name, aliases=dialog.aliases(), temp=False)
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("SAMPLE_CREATE_TITLE"),
                tr("SAMPLE_CREATE_FAILED", str(exc)),
            )
            return

        self._search_input.blockSignals(True)
        self._family_combo.blockSignals(True)
        self._search_input.clear()
        self._family_combo.setCurrentIndex(0)
        self._search_input.blockSignals(False)
        self._family_combo.blockSignals(False)

        self._refresh()
        self.select_sample(sample_id)
        self.sample_created.emit(name)

    def _on_edit_sample(self):
        if self._db is None:
            QMessageBox.warning(
                self,
                tr("SAMPLE_EDIT_TITLE"),
                tr("SAMPLE_CREATE_DB_MISSING"),
            )
            return
        if not self._selected_sample_id:
            QMessageBox.warning(
                self,
                tr("SAMPLE_EDIT_TITLE"),
                tr("SAMPLE_EDIT_SELECT_FIRST"),
            )
            return

        sample = self._db.get_sample(self._selected_sample_id)
        if sample is None:
            QMessageBox.warning(
                self,
                tr("SAMPLE_EDIT_TITLE"),
                tr("SAMPLE_EDIT_MISSING"),
            )
            return

        dialog = EditSampleDialog(
            sample_name=sample.get("polymer_name", ""),
            aliases=sample.get("aliases", []) if isinstance(sample.get("aliases"), list) else [],
            parent=self,
        )
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            updated_name = self.update_sample_entry(
                self._selected_sample_id,
                dialog.sample_name(),
                dialog.aliases(),
            )
        except ValueError as exc:
            QMessageBox.warning(
                self,
                tr("SAMPLE_EDIT_TITLE"),
                tr("SAMPLE_EDIT_INVALID", str(exc)),
            )
            return
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("SAMPLE_EDIT_TITLE"),
                tr("SAMPLE_EDIT_FAILED", str(exc)),
            )
            return

        self._refresh()
        self.select_sample(self._selected_sample_id)
        self.sample_updated.emit(updated_name)

    def _on_new_batch(self):
        if self._db is None:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_CREATE_TITLE"),
                tr("SAMPLE_CREATE_DB_MISSING"),
            )
            return
        if not self._selected_sample_id:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_CREATE_TITLE"),
                tr("SAMPLE_BATCH_HINT"),
            )
            return

        dialog = CreateBatchDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return

        batch_label = dialog.batch_label()
        technique = dialog.technique()
        file_path = dialog.file_path()

        try:
            batch_id, resolved_path = self.create_batch_with_file(
                self._selected_sample_id,
                batch_label,
                technique,
                file_path,
            )
        except FileNotFoundError as exc:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_CREATE_TITLE"),
                tr("SAMPLE_BATCH_CREATE_FILE_MISSING_DETAIL", str(exc)),
            )
            return
        except ValueError as exc:
            QMessageBox.warning(
                self,
                tr("SAMPLE_BATCH_CREATE_TITLE"),
                tr("SAMPLE_BATCH_CREATE_INVALID", str(exc)),
            )
            return
        except Exception as exc:
            QMessageBox.critical(
                self,
                tr("SAMPLE_BATCH_CREATE_TITLE"),
                tr("SAMPLE_BATCH_CREATE_FAILED", str(exc)),
            )
            return

        self._refresh()
        self.select_sample(self._selected_sample_id)
        self._highlight_batch(batch_id)
        self.batch_created.emit(batch_label, resolved_path)

    def get_selected_batch_ids(self):
        return [
            batch_id
            for batch_id, checkbox in self._batch_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _highlight_batch(self, batch_id: str):
        if not batch_id:
            return
        for row_index in range(self._batch_list.count()):
            item = self._batch_list.item(row_index)
            widget = self._batch_list.itemWidget(item)
            if widget is None:
                continue
            checkbox = widget.findChild(QCheckBox)
            if checkbox is None:
                continue
            current_id = next(
                (current_batch_id for current_batch_id, current_checkbox in self._batch_checkboxes.items() if current_checkbox is checkbox),
                None,
            )
            if current_id != batch_id:
                continue
            self._batch_list.setCurrentRow(row_index)
            self._batch_list.scrollToItem(item)
            checkbox.setChecked(True)
            break
