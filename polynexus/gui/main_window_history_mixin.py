from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .analysis_history_service import (
    collect_history_rows,
    format_history_timestamp,
    history_action_state,
    history_compare_counts,
    history_compare_record as select_history_compare_record,
    history_compare_rows,
    history_compare_tooltip_key,
    history_copy_summary_tooltip_key,
    history_export_rows as build_history_export_rows,
    history_has_available_source,
    history_record_confirmed,
    history_record_context_ref,
    history_result_metrics,
    history_metrics_summary,
    history_filter_items,
    history_restore_tooltip_key,
    history_rerun_tooltip_key,
    history_status_label_parts,
    history_status_text_parts,
    history_summary_lines as build_history_summary_lines,
    history_tooltip_translation_key,
    history_validation_summary_text,
)
from .history_compare_service import history_compare_summary_text
from .history_compare_service import (
    history_compare_counts_text,
    history_compare_state_color,
    history_compare_state_label,
)
from .history_table_service import build_history_table_rows, write_history_export_table
from .table_clipboard_service import (
    copy_table_selection_to_clipboard as copy_table_selection_text_to_clipboard,
    extract_table_text_matrix,
)
from .i18n import get_language, tr
from .window_text_helpers import is_default_project_label
from ..core.engine import logger


def resolve_joint_history_project_label(current_label, report) -> str:
    """Resolve display-only identity for a Joint run without inventing data."""

    label = str(current_label or "").strip()
    if label and not is_default_project_label(label):
        return label
    rows = report.get("rows") if isinstance(report, dict) else None
    if not isinstance(rows, list):
        return label
    samples = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sample = str(row.get("sample") or "").strip()
        if sample and sample not in samples:
            samples.append(sample)
    if len(samples) == 1:
        return samples[0]
    if len(samples) > 1:
        return tr("WORKFLOW_TASK_JOINT_TITLE")
    return label


class MainWindowHistoryMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    @classmethod
    def _analysis_run_persistence_context_class(cls):
        return cls._main_window_module().AnalysisRunPersistenceContext

    @classmethod
    def _persist_gui_analysis_run_fn(cls):
        return cls._main_window_module().persist_gui_analysis_run

    @classmethod
    def _analysis_run_result_payload_fn(cls):
        return cls._main_window_module().analysis_run_result_payload

    @classmethod
    def _analysis_run_result_r2_fn(cls):
        return cls._main_window_module().analysis_run_result_r2

    @classmethod
    def _build_history_context_snapshot_fn(cls):
        return cls._main_window_module().build_history_context_snapshot_from_window

    @classmethod
    def _history_context_line_parts_fn(cls):
        return cls._main_window_module().history_context_line_parts

    @classmethod
    def _history_result_origin_fn(cls):
        return cls._main_window_module().history_result_origin

    @classmethod
    def _result_to_jsonable_fn(cls):
        return cls._main_window_module().result_to_jsonable

    @classmethod
    def _sidebar_module_text(cls):
        return cls._main_window_module().SIDEBAR_MODULE_TEXT

    @classmethod
    def _technique_labels(cls):
        return cls._main_window_module().TECHNIQUE_LABELS

    @classmethod
    def _lang_text_fn(cls):
        return cls._main_window_module()._lang_text

    def _copy_table_selection_to_clipboard(self, table):
        copy_table_selection_text_to_clipboard(table)

    def _history_compare_record(self, record):
        if not isinstance(record, dict):
            return None
        batch_id = str(record.get("batch_id") or "")
        if not batch_id:
            return None
        db = self._ensure_sample_db()
        runs = db.get_analysis_runs(batch_id)
        return select_history_compare_record(record, runs)

    def _history_has_comparison_target(self, record) -> bool:
        return self._history_compare_record(record) is not None

    def _history_status_text(self, record) -> str:
        status = self._history_status_label(record)
        origin_label = self._history_result_origin_label(record)
        parts = history_status_text_parts(
            status,
            origin_label,
            source_available=history_has_available_source(record),
        )
        labels = list(parts.labels)
        if parts.source_missing:
            labels.append(tr("HISTORY_STATUS_SOURCE_MISSING"))
        return " | ".join(labels)

    def _history_status_label(self, record) -> str:
        parts = history_status_label_parts(record)
        label = tr(parts.translation_key) if parts.translation_key else parts.fallback_label
        if not label or not parts.include_saxs_suffix or not isinstance(record, dict):
            return label

        metrics = self._history_result_metrics(record)
        lc_status = self._saxs_lc_status_text(metrics.get("lc_reliability_status") or record.get("lc_reliability_status"))
        lc_method = self._saxs_calibration_method_text(metrics.get("lc_method") or record.get("lc_method"))
        fallback_active = metrics.get("calibrated_fallback_active")
        suffix_bits = [bit for bit in [lc_status, lc_method] if bit]
        if not suffix_bits and fallback_active is not None:
            suffix_bits.append("回退" if get_language() == "zh" else "fallback")
        if suffix_bits:
            label = f"{label} | " + " | ".join(suffix_bits[:3])
        return label

    def _history_restore_tooltip(self, record) -> str:
        key = history_restore_tooltip_key(record, has_source=history_has_available_source(record))
        return tr(history_tooltip_translation_key(key))

    def _history_rerun_tooltip(self, record) -> str:
        key = history_rerun_tooltip_key(record, has_source=history_has_available_source(record))
        return tr(history_tooltip_translation_key(key))

    def _history_compare_tooltip(self, record) -> str:
        key = history_compare_tooltip_key(record, has_compare=self._history_has_comparison_target(record))
        return tr(history_tooltip_translation_key(key))

    def _history_copy_summary_tooltip(self, record) -> str:
        key = history_copy_summary_tooltip_key(record)
        return tr(history_tooltip_translation_key(key))

    def _history_result_metrics(self, record):
        return history_result_metrics(record)

    def _history_validation_summary(self, record) -> str:
        return history_validation_summary_text(
            record,
            quality_flag_summary_fn=self._quality_flag_summary_text,
        )

    def _history_metrics_tooltip(self, record, *, limit=4):
        metrics = self._history_result_metrics(record)
        technique = str(record.get("technique") or self._current_technique or "").strip().lower() if isinstance(record, dict) else ""

        return history_metrics_summary(metrics, technique=technique, limit=limit)

    def _history_compare_state_label(self, state: str) -> str:
        return history_compare_state_label(self, state)

    def _history_compare_counts_text(self, counts) -> str:
        return history_compare_counts_text(self, counts)

    def _history_compare_state_color(self, state: str):
        return history_compare_state_color(self, state)

    def _history_record_context_text(self, record) -> str:
        ref = history_record_context_ref(record)
        if ref.kind == "submodule":
            return self._history_submodule_text(ref.value)
        if ref.kind == "technique":
            return self._history_technique_text(ref.value)
        return ""

    def _history_context_snapshot(self, tuning_context=None, joint_context=None) -> dict:
        return self._build_history_context_snapshot_fn()(self)

    def _history_context_lines(self, record) -> list[str]:
        lines = []
        for part in self._history_context_line_parts_fn()(
            record,
            validation_summary=self._history_validation_summary(record),
            origin_label=self._history_result_origin_label(record),
            boundary_text=self._responsibility_boundary_summary(),
            chain_summary_fn=self._ai_tuning_chain_snapshot,
        ):
            if part.kind == "review_chain":
                lines.append(tr("RESULTS_REVIEW_CHAIN", part.text))
            else:
                lines.append(part.text)
        return lines

    def _history_result_origin_label(self, record) -> str:
        origin = self._history_result_origin_fn()(record)
        if not origin:
            return ""
        return self._result_origin_label(origin)

    def _result_to_jsonable(self, value):
        return self._result_to_jsonable_fn()(
            value,
            warning_fn=lambda message: logger.warning(message, exc_info=True),
        )

    def _history_submodule_text(self, submodule_id: str) -> str:
        key = str(submodule_id or "").strip()
        if not key:
            return ""
        mapping = self._sidebar_module_text().get(key)
        if isinstance(mapping, dict):
            return self._lang_text_fn()(mapping, key)
        return key

    def _history_technique_text(self, technique_id: str) -> str:
        key = str(technique_id or "").strip()
        if not key:
            return ""
        return self._technique_labels().get(key, key.upper())

    def _build_history_panel(self):

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self._history_tech_label = QLabel(tr("HISTORY_TECHNIQUE"))
        toolbar.addWidget(self._history_tech_label)

        self._history_filter_combo = QComboBox()
        self._set_history_filter_items(["saxs", "waxs", "dsc", "ir", "nmr"])
        self._history_filter_combo.currentIndexChanged.connect(self._refresh_history)
        toolbar.addWidget(self._history_filter_combo)

        self._history_refresh_btn = QPushButton(tr("HISTORY_REFRESH"))
        self._history_refresh_btn.setObjectName("secondary_btn")
        self._history_refresh_btn.clicked.connect(self._refresh_history)
        toolbar.addWidget(self._history_refresh_btn)

        self._history_export_btn = QPushButton(tr("HISTORY_EXPORT"))
        self._history_export_btn.setObjectName("secondary_btn")
        self._history_export_btn.clicked.connect(self._export_history_table)
        toolbar.addWidget(self._history_export_btn)

        self._history_copy_summary_btn = QPushButton(tr("HISTORY_COPY_SUMMARY"))
        self._history_copy_summary_btn.setObjectName("secondary_btn")
        self._history_copy_summary_btn.clicked.connect(self._copy_history_summary)
        toolbar.addWidget(self._history_copy_summary_btn)

        self._history_restore_btn = QPushButton(tr("HISTORY_RESTORE"))
        self._history_restore_btn.setObjectName("secondary_btn")
        self._history_restore_btn.clicked.connect(self._on_history_restore_requested)
        toolbar.addWidget(self._history_restore_btn)

        self._history_rerun_btn = QPushButton(tr("HISTORY_RERUN"))
        self._history_rerun_btn.setObjectName("secondary_btn")
        self._history_rerun_btn.clicked.connect(self._on_history_rerun_requested)
        toolbar.addWidget(self._history_rerun_btn)

        self._history_confirm_btn = QPushButton(tr("RESULTS_CONFIRM_MARK"))
        self._history_confirm_btn.setObjectName("secondary_btn")
        self._history_confirm_btn.clicked.connect(self._on_history_confirm_requested)
        toolbar.addWidget(self._history_confirm_btn)

        self._history_compare_btn = QPushButton(tr("HISTORY_COMPARE"))
        self._history_compare_btn.setObjectName("secondary_btn")
        self._history_compare_btn.clicked.connect(self._on_history_compare_requested)
        toolbar.addWidget(self._history_compare_btn)

        toolbar.addStretch()

        toolbar_content = QWidget()
        toolbar_content.setObjectName("history_toolbar_content")
        toolbar_content.setMinimumWidth(0)
        toolbar_content.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        toolbar_content.setLayout(toolbar)

        toolbar_scroll = QScrollArea()
        toolbar_scroll.setObjectName("history_toolbar_scroll")
        toolbar_scroll.setFrameShape(QScrollArea.NoFrame)
        toolbar_scroll.setWidgetResizable(False)
        toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        toolbar_scroll.setMinimumWidth(0)
        toolbar_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        toolbar_scroll.setWidget(toolbar_content)
        layout.addWidget(toolbar_scroll)

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(7)
        self._history_table.setHorizontalHeaderLabels(
            [
                tr("HISTORY_COL_TIME"),
                tr("HISTORY_COL_TECHNIQUE"),
                tr("HISTORY_COL_SUBMODULE"),
                tr("HISTORY_COL_SCORE"),
                tr("HISTORY_COL_STATUS"),
                tr("HISTORY_COL_VALIDATION"),
                tr("HISTORY_COL_CONFIRMED"),
            ]
        )
        self._history_table.setAlternatingRowColors(True)
        self._history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._history_table.setWordWrap(False)
        self._history_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._history_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._history_table.cellDoubleClicked.connect(self._on_history_row_activated)
        self._history_table.itemActivated.connect(
            lambda item: self._on_history_row_activated(item.row(), item.column()) if item is not None else None
        )
        self._history_copy_shortcut = QShortcut(QKeySequence.Copy, self._history_table)
        self._history_copy_shortcut.activated.connect(self._copy_history_summary)
        self._history_table.itemSelectionChanged.connect(self._update_history_action_state)
        layout.addWidget(self._history_table, 1)

        self._refresh_history()
        self._update_history_action_state()
        return w

    def _persist_analysis_run(self, result):
        try:
            db = self._ensure_sample_db()
            project_label = self._project_label.text().strip()
            if str(getattr(self, "_current_technique", "") or "").strip().lower() == "joint":
                display_project_label = resolve_joint_history_project_label(project_label, result)
                if display_project_label and hasattr(self, "_project_label"):
                    self._project_label.setText(display_project_label)
            context = self._analysis_run_persistence_context_class()(
                technique=str(getattr(self, "_current_technique", "") or ""),
                submodule=str(getattr(self, "_current_submodule_id", "") or ""),
                data_file=str(getattr(self, "_current_filepath", "") or ""),
                output_dir=str(getattr(self, "_output_dir", "") or ""),
                project_label=project_label,
                current_sample_name=str(getattr(self, "_current_sample_name", "") or ""),
                current_sample_id=str(getattr(self, "_current_sample_id", "") or ""),
                current_batch_id=str(getattr(self, "_current_batch_id", "") or ""),
                current_batch_label=str(getattr(self, "_current_batch_label", "") or ""),
                ai_tuned=bool(getattr(self, "_last_ai_tuned_run", False)),
                confirmed=bool(getattr(self, "_current_result_confirmed_flag", False)),
                history_context=self._result_to_jsonable(self._history_context_snapshot()),
            )
            self._last_persisted_run_id = self._persist_gui_analysis_run_fn()(db, result, context)
            record_context = getattr(self, "_record_result_context", None)
            if callable(record_context):
                record_context(
                    context.technique,
                    status="complete",
                    run_id=self._last_persisted_run_id,
                )
            payload = self._analysis_run_result_payload_fn()(result)
            logger.info(
                "Analysis result persisted. technique=%s r2=%.4f",
                str(payload.get("technique") or context.technique or "unknown"),
                self._analysis_run_result_r2_fn()(payload),
            )
            self._refresh_history()
        except Exception as e:
            logger.warning("Failed to persist analysis result: %s", e)
            logger.warning("Analysis persistence traceback follows.", exc_info=True)

    def _refresh_history(self):

        try:
            if not hasattr(self, "_history_table"):
                return

            selected_record = self._selected_history_record()
            selected_run_id = (
                str(selected_record.get("id") or "")
                if isinstance(selected_record, dict)
                else ""
            )

            db = self._ensure_sample_db()
            selected = (
                self._history_filter_combo.currentData()
                if hasattr(self, "_history_filter_combo")
                else ""
            )

            all_rows = collect_history_rows(db)

            if hasattr(self, "_history_filter_combo"):
                current = str(self._history_filter_combo.currentData() or "")
                items = history_filter_items(all_rows)
                self._set_history_filter_items(items, current)
                active_filter = str(self._history_filter_combo.currentData() or "")
            else:
                active_filter = selected

            if not active_filter:
                rows = all_rows
            else:
                rows = [
                    run for run in all_rows
                    if str(run.get("technique") or "") == active_filter
                ]

            self._history_cache = rows
            self._history_table.clearSpans()
            self._history_table.setRowCount(len(rows))
            if not rows:
                empty_text = (
                    tr("HISTORY_EMPTY_ALL")
                    if not active_filter
                    else tr("HISTORY_EMPTY_FILTER", self._history_technique_text(active_filter))
                )
                self._history_table.setRowCount(1)
                self._history_table.setSpan(0, 0, 1, self._history_table.columnCount())
                item = QTableWidgetItem(empty_text)
                item.setToolTip(empty_text)
                self._history_table.setItem(0, 0, item)
                self._history_table.clearSelection()
                self._update_history_action_state()
                return

            history_rows = build_history_table_rows(
                rows,
                metrics_tooltip_fn=self._history_metrics_tooltip,
                technique_text_fn=self._history_technique_text,
                submodule_text_fn=self._history_submodule_text,
                status_text_fn=self._history_status_text,
                validation_summary_fn=self._history_validation_summary,
                confirmation_label_fn=self._history_confirmation_label,
                has_source_fn=history_has_available_source,
            )

            for row_index, row in enumerate(history_rows):
                for col_index, value in enumerate(row.values):
                    item = QTableWidgetItem(value)
                    item.setToolTip(row.tooltips[col_index])
                    self._history_table.setItem(row_index, col_index, item)

            if selected_run_id:
                for row_index, run in enumerate(rows):
                    if str(run.get("id") or "") == selected_run_id:
                        self._history_table.selectRow(row_index)
                        break
            self._update_history_action_state()
        except Exception as e:
            logger.warning("Failed to refresh history records: %s", e)
            logger.warning("History refresh traceback follows.", exc_info=True)


    def _set_history_filter_items(self, techniques, current_value="") -> None:

        if not hasattr(self, "_history_filter_combo"):
            return

        combo = self._history_filter_combo
        current = str(current_value or "")
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(tr("HISTORY_FILTER_ALL"), "")
        for technique in techniques:
            tech = str(technique or "").strip()
            if not tech:
                continue
            combo.addItem(self._history_technique_text(tech), tech)
        idx = combo.findData(current)
        if idx < 0:
            idx = 0
        combo.setCurrentIndex(idx)
        combo.blockSignals(False)


    def _selected_history_row(self):

        table = getattr(self, "_history_table", None)
        if table is None:
            return -1
        selection = table.selectionModel()
        if selection is None or not selection.hasSelection():
            return -1
        rows = selection.selectedRows()
        if not rows:
            return -1
        return rows[0].row()


    def _selected_history_record(self):

        row = self._selected_history_row()
        cache = getattr(self, "_history_cache", [])
        if row < 0 or row >= len(cache):
            return None
        return cache[row]


    def _update_history_action_state(self):

        record = self._selected_history_record()
        has_source = history_has_available_source(record)
        has_compare = self._history_has_comparison_target(record)
        action_state = history_action_state(record, has_source=has_source, has_compare=has_compare)
        if hasattr(self, "_history_copy_summary_btn"):
            self._history_copy_summary_btn.setEnabled(action_state.can_copy_summary)
            self._history_copy_summary_btn.setToolTip(self._history_copy_summary_tooltip(record))
        if hasattr(self, "_history_restore_btn"):
            self._history_restore_btn.setEnabled(action_state.can_restore)
            self._history_restore_btn.setToolTip(self._history_restore_tooltip(record))
        if hasattr(self, "_history_rerun_btn"):
            self._history_rerun_btn.setEnabled(action_state.can_rerun)
            self._history_rerun_btn.setToolTip(self._history_rerun_tooltip(record))
        if hasattr(self, "_history_compare_btn"):
            self._history_compare_btn.setEnabled(action_state.can_compare)
            self._history_compare_btn.setToolTip(self._history_compare_tooltip(record))
        if hasattr(self, "_history_confirm_btn"):
            self._history_confirm_btn.setEnabled(action_state.can_confirm)
            self._history_confirm_btn.setText(
                tr("RESULTS_CONFIRM_CLEAR") if self._history_confirmation_label(record) == tr("RESULTS_CONFIRM_STATUS_CONFIRMED") else tr("RESULTS_CONFIRM_MARK")
            )
            self._history_confirm_btn.setToolTip(
                self._history_confirmation_label(record) if action_state.has_record else tr("HISTORY_TOOLTIP_SELECT")
            )


    def _restore_history_record(self, record, log_key="LOG_HISTORY_RESTORED"):

        if not isinstance(record, dict):
            return False

        technique = str(record.get("technique") or "")
        submodule = str(record.get("submodule") or "")
        created_at = str(record.get("created_at") or "")
        output_dir = str(record.get("output_dir") or "").strip()
        parameters = record.get("parameters") if isinstance(record.get("parameters"), dict) else {}
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        data_file = str(summary.get("data_file") or "").strip()

        if not technique:
            return False

        is_joint = technique.strip().lower() == "joint"
        if is_joint:
            self._on_joint_selected(submodule or "joint.compare")
        else:
            self._on_technique_selected(technique)
            btn = self._nav_buttons.get(technique)
            if btn:
                btn.setChecked(True)

        if submodule and not is_joint:
            btn = self._nav_buttons.get(submodule)
            if btn:
                btn.setChecked(True)
            self._on_submodule_selected(technique or self._current_technique, submodule)

        if data_file and Path(data_file).exists():
            self._set_input_path(data_file, is_dir=Path(data_file).is_dir())
            self._save_last_dir(data_file)
        elif data_file:
            self.log(tr("LOG_HISTORY_DATA_MISSING", data_file))
            return False

        if output_dir:
            self._output_dir = output_dir
            if hasattr(self, "_output_input"):
                self._output_input.setText(output_dir)
            populate_plots = getattr(self, "_populate_plots", None)
            if callable(populate_plots):
                populate_plots()

        if parameters:
            self._apply_best_config(parameters)

        self._current_result_confirmed_flag = history_record_confirmed(record)
        self._update_results_confirm_panel()

        history_context = summary.get("history_context") if isinstance(summary.get("history_context"), dict) else {}
        if isinstance(history_context, dict) and history_context:
            restored_tuning_context = history_context.get("tuning_context") if isinstance(history_context.get("tuning_context"), dict) else {}
            if isinstance(restored_tuning_context, dict):
                restored_tuning_context = dict(restored_tuning_context)
                joint_context = history_context.get("joint_ai_context") if isinstance(history_context.get("joint_ai_context"), dict) else {}
                if isinstance(joint_context, dict) and joint_context and not isinstance(restored_tuning_context.get("joint_ai_context"), dict):
                    restored_tuning_context["joint_ai_context"] = joint_context
                if restored_tuning_context:
                    self._last_ai_tuning_context = restored_tuning_context

        restored_payload = self._result_to_jsonable(record)
        if isinstance(restored_payload, dict) and restored_payload:
            self._results[str(technique).strip().lower()] = restored_payload
        self._last_persisted_run_id = str(record.get("id") or "")
        record_context = getattr(self, "_record_result_context", None)
        if callable(record_context):
            record_context(
                technique,
                status="complete",
                run_id=self._last_persisted_run_id,
            )
        joint_report = summary.get("result") if is_joint and isinstance(summary.get("result"), dict) else None
        if joint_report is not None:
            project_label = resolve_joint_history_project_label(
                summary.get("project_label"),
                joint_report,
            )
            if project_label and hasattr(self, "_project_label"):
                self._project_label.setText(project_label)
            self._joint_report = joint_report
            self._results["joint"] = joint_report
            self._display_joint_report(joint_report)
        else:
            self._display_results(parameters, restored_payload or record)

        self._update_workspace_context()
        self._update_work_memory_panel()
        self._update_results_review_panel()

        if hasattr(self, "_tabs"):
            self._tabs.setCurrentIndex(0)

        ts = datetime.now().strftime("%H:%M:%S")
        technique_label = self._history_technique_text(technique)
        submodule_label = self._history_record_context_text(record)
        created_label = format_history_timestamp(created_at)
        line = (
            f'[{ts}] <span style="color:#2563eb;">'
            f"{tr(log_key, technique_label, submodule_label, created_label)}"
            f"</span>"
        )
        self._log_panel.append(line)
        sb = self._log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())
        return True


    def _on_history_restore_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return
        self._restore_history_record(record)


    def _on_history_rerun_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return
        if not self._restore_history_record(record, log_key="LOG_HISTORY_RERUN_READY"):
            return
        self._run_analysis()


    def _history_table_text_matrix(self):
        return extract_table_text_matrix(self._history_table)

    def _history_export_rows(self):

        headers, matrix = self._history_table_text_matrix()
        return build_history_export_rows(
            headers,
            matrix,
            getattr(self, "_history_cache", []),
            origin_label_fn=self._history_result_origin_label,
        )


    def _export_history_table(self):

        self._refresh_history()
        headers, matrix = self._history_export_rows()
        if not headers or not matrix:
            return

        current_filter = ""
        if hasattr(self, "_history_filter_combo"):
            current_filter = str(self._history_filter_combo.currentData() or "").strip()
        suffix = current_filter or "all"
        default_name = f"history_{suffix}.tsv"
        start_dir = self._output_dir or self._get_last_dir()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("HISTORY_EXPORT_TITLE"),
            os.path.join(start_dir, default_name),
            tr("HISTORY_EXPORT_FILTER"),
        )
        if not path:
            return

        from . import main_window as main_window_module

        export_writer = getattr(
            main_window_module,
            "write_history_export_table",
            write_history_export_table,
        )
        written_path = export_writer(
            path,
            headers,
            matrix,
            selected_filter=selected_filter,
        )
        if not written_path:
            return

        self._save_last_dir(os.path.dirname(written_path) or start_dir)
        self.log(tr("LOG_HISTORY_EXPORTED", len(matrix), written_path))


    def _copy_history_summary(self):

        record = self._selected_history_record()
        if not isinstance(record, dict):
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return

        lines = build_history_summary_lines(
            record,
            technique_text_fn=self._history_technique_text,
            context_text_fn=self._history_record_context_text,
            timestamp_text_fn=format_history_timestamp,
            metrics_text_fn=lambda item: self._history_metrics_tooltip(item, limit=6),
            context_lines_fn=self._history_context_lines,
        )
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        context = self._history_record_context_text(record)
        technique = self._history_technique_text(str(record.get("technique") or ""))
        created = format_history_timestamp(record.get("created_at"))
        self.log(tr("LOG_HISTORY_SUMMARY_COPIED", context or technique or created))


    def _show_history_comparison(self, current_record, baseline_record):

        current_metrics = self._history_result_metrics(current_record)
        baseline_metrics = self._history_result_metrics(baseline_record)

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("HISTORY_COMPARE_TITLE"))
        dialog.resize(760, 460)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(8)

        layout.addWidget(
            QLabel(
                history_compare_summary_text(
                    current_record,
                    baseline_record,
                    timestamp_text_fn=format_history_timestamp,
                    context_text_fn=self._history_record_context_text,
                )
            )
        )

        rows = history_compare_rows(current_metrics, baseline_metrics)
        layout.addWidget(QLabel(self._history_compare_counts_text(history_compare_counts(rows))))

        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels([
            tr("HISTORY_COMPARE_COL_METRIC"),
            tr("HISTORY_COMPARE_COL_CURRENT"),
            tr("HISTORY_COMPARE_COL_BASELINE"),
            tr("HISTORY_COMPARE_COL_STATE"),
        ])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        dialog._history_compare_copy_shortcut = QShortcut(QKeySequence.Copy, table)
        dialog._history_compare_copy_shortcut.activated.connect(
            lambda: self._copy_table_selection_to_clipboard(table)
        )

        for row_index, (key, current_value, baseline_value, state) in enumerate(rows):
            state_label = self._history_compare_state_label(state)
            for col_index, value in enumerate([key, current_value, baseline_value, state_label]):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                if col_index == 3:
                    item.setForeground(self._history_compare_state_color(state))
                table.setItem(row_index, col_index, item)

        layout.addWidget(table, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        dialog._history_compare_copy_button = QPushButton(tr("COMMON_COPY"))
        dialog._history_compare_copy_button.clicked.connect(
            lambda: self._copy_table_selection_to_clipboard(table)
        )
        button_row.addWidget(dialog._history_compare_copy_button)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(tr("COMMON_CLOSE"))
        button_row.addWidget(buttons)
        layout.addLayout(button_row)

        dialog.exec()


    def _on_history_compare_requested(self):

        record = self._selected_history_record()
        if record is None:
            self.log(tr("LOG_HISTORY_SELECT_RUN"))
            return

        baseline = self._history_compare_record(record)
        if baseline is None:
            self.log(tr("LOG_HISTORY_COMPARE_UNAVAILABLE"))
            return

        self._show_history_comparison(record, baseline)


    def _on_history_row_activated(self, row: int, col: int):

        try:
            if row < 0:
                return
            cache = getattr(self, "_history_cache", [])
            if row >= len(cache):
                return
            self._history_table.selectRow(row)
            self._update_history_action_state()
            self._restore_history_record(cache[row])
        except Exception as e:
            logger.warning("Failed to restore history record: %s", e)
            logger.warning("History restore traceback follows.", exc_info=True)
