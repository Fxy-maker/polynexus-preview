from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QTableWidgetItem,
)

from .analysis_history_service import flatten_params as flatten_history_params
from .export_context_service import (
    build_export_context_payload,
    compose_joint_export_detail,
    copy_export_bundle_sections,
    create_export_bundle_dirs,
    export_relative_report_path,
    write_export_manifest,
    write_export_readme,
)
from .i18n import get_language, tr
from .results_review_service import (
    result_review_ir_temperature_2d_user_summary_lines as build_result_review_ir_temperature_2d_user_summary_lines,
)
from .results_table_service import (
    build_batch_results_table_model,
    build_results_table_model,
)
from .result_table_models import ResultTableSection
from .table_clipboard_service import (
    copy_table_selection_to_clipboard as copy_table_selection_text_to_clipboard,
    extract_table_text_matrix,
)
from .table_export_service import write_table_export
from ..core.engine import logger


class MainWindowOutputMixin:
    @staticmethod
    def _results_table_export_writer():
        try:
            from . import main_window as main_window_module
        except Exception:
            return write_table_export
        return getattr(main_window_module, "write_table_export", write_table_export)

    def _set_results_summary(self, text="", risk_text="", next_text=""):
        summary = str(text or "")
        risk = str(risk_text or "")
        next_step = str(next_text or "")

        if hasattr(self, "_results_summary_group"):
            self._results_summary_label.setText(summary)
            self._results_summary_label.setVisible(bool(summary))
            self._results_summary_risk_label.setText(risk)
            self._results_summary_risk_label.setVisible(bool(risk))
            self._results_summary_next_label.setText(next_step)
            self._results_summary_next_label.setVisible(bool(next_step))
            self._results_summary_group.setVisible(bool(summary or risk or next_step))
        elif hasattr(self, "_results_summary_label"):
            self._results_summary_label.setText(summary)
            self._results_summary_label.setVisible(bool(summary))
        self._update_results_review_panel()
        self._update_results_review_hint(summary, risk, next_step)

    def _update_results_review_hint(self, summary, risk_text="", next_text=""):
        panel = getattr(self, "_results_panel", None)
        if panel is None:
            return

        summary_text = str(summary or "")
        risk_text_value = str(risk_text or "")
        next_text_value = str(next_text or "")

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule_id = str(getattr(self, "_current_submodule_id", "") or "").strip().lower()
        if (
            technique != "saxs"
            or submodule_id not in {"temperature", "saxs.temperature", "saxs.strain"}
            or not any((summary_text, risk_text_value, next_text_value))
        ):
            panel.clear_review_hint()
            return

        def jump_to_results_tab() -> None:
            jump_to_tab = getattr(self, "_jump_to_tab", None)
            if callable(jump_to_tab):
                jump_to_tab(2)
                return
            tabs = getattr(self, "_tabs", None)
            if tabs is not None and hasattr(tabs, "setCurrentIndex"):
                tabs.setCurrentIndex(2)

        panel.set_review_hint(
            title=summary_text or tr("SAXS_RESULTS_REVIEW_HINT_TITLE"),
            detail=risk_text_value,
            next_text=next_text_value,
            status="review" if risk_text_value else "neutral",
            action_text=tr("SAXS_RESULTS_REVIEW_HINT_ACTION"),
            action=jump_to_results_tab,
        )

    def _reset_results_panel_for_legacy_table(self):
        panel = getattr(self, "_results_panel", None)
        if panel is None:
            return
        empty = ResultTableSection.empty()
        panel.set_content(heroes=(), primary=empty, detail=empty, diagnostics=empty)

    def _render_structured_results_model(self, table_model) -> bool:
        panel = getattr(self, "_results_panel", None)
        primary = getattr(table_model, "primary_section", None)
        if panel is None or primary is None:
            return False
        panel.set_content(
            heroes=table_model.hero_metrics,
            primary=primary,
            detail=table_model.detail_section or ResultTableSection.empty(),
            diagnostics=table_model.diagnostic_section or ResultTableSection.empty(),
        )
        return True

    def _set_results_default_order_control_visible(self, visible):
        if hasattr(self, "_btn_results_default_order"):
            self._btn_results_default_order.setVisible(bool(visible))
            self._btn_results_default_order.setEnabled(bool(visible))

    def _set_results_copy_control_visible(self, visible):
        if hasattr(self, "_btn_results_copy"):
            self._btn_results_copy.setVisible(bool(visible))
            self._btn_results_copy.setEnabled(bool(visible))

    def _set_results_export_control_visible(self, visible):
        if hasattr(self, "_btn_results_export"):
            self._btn_results_export.setVisible(bool(visible))
            self._btn_results_export.setEnabled(bool(visible))

    def _store_results_table_default_order(self, cols, rows, sortable=True):
        self._results_table_default_order = {
            "cols": [str(col) for col in cols],
            "rows": [[("" if value is None else str(value)) for value in row] for row in rows],
            "sortable": bool(sortable),
        }
        self._set_results_default_order_control_visible(sortable)

    def _clear_results_table_default_order(self):
        self._results_table_default_order = None
        self._set_results_default_order_control_visible(False)

    def _restore_results_table_default_order(self):
        snapshot = getattr(self, "_results_table_default_order", None)
        if not isinstance(snapshot, dict):
            return

        cols = snapshot.get("cols") or []
        rows = snapshot.get("rows") or []
        sortable = bool(snapshot.get("sortable"))

        current_model = getattr(self, "_current_results_table_model", None)
        if getattr(current_model, "primary_section", None) is not None:
            self._render_structured_results_model(current_model)
            self._results_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
            self._results_table.setSortingEnabled(sortable)
            return

        self._results_table.setSortingEnabled(False)
        self._results_table.setRowCount(len(rows))
        self._results_table.setColumnCount(len(cols))
        self._results_table.setHorizontalHeaderLabels(cols)
        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                self._set_results_item(row_index, col_index, value)
        self._apply_results_table_layout()
        self._results_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self._results_table.setSortingEnabled(sortable)

    def _copy_results_table_to_clipboard(self):
        copied, row_count, col_count = copy_table_selection_text_to_clipboard(self._results_table)
        if copied:
            self.log(tr("LOG_RESULTS_TABLE_COPIED", row_count, col_count))

    def _results_table_text_matrix(self):
        return extract_table_text_matrix(self._results_table)

    def _export_results_table(self):
        default_name = "results_table.tsv"
        start_dir = self._output_dir or self._get_last_dir()
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("RESULTS_EXPORT_TABLE_TITLE"),
            os.path.join(start_dir, default_name),
            tr("RESULTS_EXPORT_TABLE_FILTER"),
        )
        if not path:
            return

        headers, matrix = self._results_table_text_matrix()
        written_path = self._results_table_export_writer()(
            path,
            headers,
            matrix,
            selected_filter=selected_filter,
        )
        if not written_path:
            return

        self._save_last_dir(os.path.dirname(written_path) or start_dir)
        self.log(tr("LOG_RESULTS_TABLE_EXPORTED", len(matrix), len(headers), written_path))

    def _display_table_rows(self, columns, rows):
        self._reset_results_panel_for_legacy_table()
        self._results_table.setRowCount(len(rows))
        self._results_table.setColumnCount(len(columns))
        self._results_table.setHorizontalHeaderLabels(columns)
        for row_index, row_values in enumerate(rows):
            for col_index, value in enumerate(row_values):
                self._set_results_item(row_index, col_index, value)
        self._apply_results_table_layout()

    def _set_results_item(self, row, col, value):
        """Set a result-table item with full-value tooltip."""
        text = "" if value is None else str(value)
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        self._results_table.setItem(row, col, item)

    def _apply_results_table_layout(self):
        """Keep wide result tables readable instead of squeezing columns."""
        table = self._results_table
        cols = table.columnCount()
        rows = table.rowCount()
        header = table.horizontalHeader()

        header.setStretchLastSection(False)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        if cols <= 2:
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            if cols == 2:
                header.setSectionResizeMode(1, QHeaderView.Stretch)
            table.resizeRowsToContents()
            return

        if cols <= 6:
            header.setSectionResizeMode(QHeaderView.Stretch)
            table.resizeRowsToContents()
            return

        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(96)
        header.setDefaultSectionSize(150)

        for col in range(cols):
            label_item = table.horizontalHeaderItem(col)
            label = label_item.text() if label_item is not None else ""
            width = 170 if col == 0 else 132
            if len(label) > 18:
                width = min(220, max(width, len(label) * 8))
            table.setColumnWidth(col, width)

        if rows > 0:
            table.resizeRowsToContents()

    def _display_joint_report(self, report):
        self._current_results_table_model = None
        self._current_results_table_source = {"kind": "joint", "report": report}
        self._update_joint_diagnostics(report)

        rows = report.get("rows", [])
        columns = [
            tr("JOINT_COL_SAMPLE"),
            tr("JOINT_COL_BATCH"),
            tr("JOINT_COL_CONDITION"),
            tr("JOINT_COL_TECHNIQUES"),
            tr("JOINT_COL_ANALYSIS"),
            tr("JOINT_COL_ALERTS"),
        ]
        display_rows = [
            [
                row.get("sample", ""),
                row.get("batch", ""),
                row.get("condition", ""),
                row.get("techniques", ""),
                row.get("opportunities", ""),
                row.get("alerts", ""),
            ]
            for row in rows
        ]
        self._display_table_rows(columns, display_rows)

    def _show_batch_results(self, all_results):
        if not all_results:
            return

        table_model = build_batch_results_table_model(
            all_results,
            ordered_columns_fn=self._ordered_results_columns,
        )
        self._current_results_table_model = table_model
        self._current_results_table_source = {
            "kind": "batch",
            "results": list(all_results),
            "technique": str(getattr(self, "_current_technique", "") or ""),
            "submodule": str(getattr(self, "_current_submodule_id", "") or ""),
        }
        self._display_table_rows(table_model.columns, table_model.display_rows)
        self._store_results_table_default_order(
            table_model.columns,
            table_model.stored_rows,
            sortable=table_model.sortable,
        )
        self._set_results_export_control_visible(table_model.export_enabled)
        self._set_results_copy_control_visible(table_model.copy_enabled)
        self._results_table.setSortingEnabled(table_model.sortable)
        self._set_results_summary(self._batch_results_summary_text(table_model.summary_count))

    def _display_results(self, params, result=None):
        self._hide_joint_diagnostics()
        self._set_results_summary("")
        self._results_table.setSortingEnabled(False)
        self._set_results_export_control_visible(False)
        self._set_results_copy_control_visible(False)
        self._clear_results_table_default_order()
        current_technique = str(getattr(self, "_current_technique", "") or "")
        current_submodule = str(getattr(self, "_current_submodule_id", "") or "")
        dispatch_technique = current_technique
        if not current_submodule.strip():
            dispatch_technique = ""
        table_model = build_results_table_model(
            params,
            ordered_columns_fn=self._ordered_results_columns,
            flatten_params_fn=flatten_history_params,
            technique=dispatch_technique,
            submodule=current_submodule,
            language=get_language(),
        )
        self._current_results_table_model = table_model
        self._current_results_table_source = {
            "kind": "results",
            "params": params,
            "result": result,
            "technique": str(getattr(self, "_current_technique", "") or ""),
            "submodule": str(getattr(self, "_current_submodule_id", "") or ""),
        }
        if not self._render_structured_results_model(table_model):
            self._display_table_rows(table_model.columns, table_model.display_rows)

        self._store_results_table_default_order(
            table_model.columns,
            table_model.stored_rows,
            sortable=table_model.sortable,
        )
        self._set_results_export_control_visible(table_model.export_enabled)
        self._set_results_copy_control_visible(table_model.copy_enabled)
        self._results_table.setSortingEnabled(table_model.sortable)

        if table_model.primary_section is not None:
            if table_model.summary_kind == "multi_sample":
                summary_text = tr("RESULTS_SUMMARY_MULTI_SAMPLE", table_model.summary_count)
            elif table_model.summary_kind == "batch":
                summary_text = self._frame_results_summary_text(table_model.summary_count)
            else:
                summary_text = self._single_results_summary_text(params)
            risk_text = table_model.risk_text
            next_text = table_model.next_text
            if result is not None:
                risk_text = risk_text or self._results_risk_summary_text(params, result)
                next_text = next_text or self._results_next_step_text(params, result)
            self._set_results_summary(summary_text, risk_text, next_text)
            return

        if table_model.kind == "multi_sample":
            if result is not None:
                self._set_results_summary(
                    tr("RESULTS_SUMMARY_MULTI_SAMPLE", table_model.summary_count),
                    self._results_risk_summary_text(params, result),
                    self._results_next_step_text(params, result),
                )
            else:
                self._set_results_summary(tr("RESULTS_SUMMARY_MULTI_SAMPLE", table_model.summary_count))
            return

        if table_model.kind == "batch":
            frame_summary = self._frame_results_summary_text(table_model.summary_count)
            if result is not None:
                self._set_results_summary(
                    frame_summary,
                    self._results_risk_summary_text(params, result),
                    self._results_next_step_text(params, result),
                )
            else:
                self._set_results_summary(
                    frame_summary,
                    self._results_risk_summary_text(params),
                    self._results_next_step_text(params),
                )
            return

        if result is not None:
            self._set_results_summary(
                self._single_results_summary_text(params),
                self._results_risk_summary_text(params, result),
                self._results_next_step_text(params, result),
            )

    def _export_context_payload(self, *, report_path="") -> dict:
        return build_export_context_payload(
            self,
            report_path=report_path,
            ir_summary_fn=build_result_review_ir_temperature_2d_user_summary_lines,
        )

    def _export_results(self, *, scope="project"):
        if not self._results and not self._batch_results:
            self.log(tr("LOG_NO_RESULTS"))
            return

        current_technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        current_scope = str(scope or "project").strip().lower() == "current"
        result_keys = (
            [current_technique]
            if current_scope and current_technique in self._results
            else list(self._results.keys())
        )
        if current_scope and not result_keys:
            self.log(tr("LOG_NO_RESULTS"))
            return
        if current_scope:
            self.log(
                tr(
                    "EXPORT_PREFLIGHT_CURRENT",
                    current_technique.upper(),
                    str(getattr(self, "_last_persisted_run_id", "") or tr("WORKSPACE_RUN_NOT_PERSISTED")),
                )
            )
        else:
            self.log(tr("EXPORT_PREFLIGHT_PROJECT", ", ".join(sorted(str(key).upper() for key in result_keys))))

        save_dir = QFileDialog.getExistingDirectory(self, tr("DIALOG_EXPORT_TITLE"), self._get_last_dir())
        if not save_dir:
            return

        self._save_last_dir(save_dir)
        save_root = os.path.join(save_dir, "PolyNexus_Run_Export" if current_scope else "PolyNexus_Export")
        bundle_dirs = create_export_bundle_dirs(save_root)
        copied_sections = copy_export_bundle_sections(self._output_dir, bundle_dirs)
        for sub in copied_sections:
            self.log(tr("LOG_COPIED").format(sub))

        if str(getattr(self, "_current_technique", "") or "").strip().lower() == "saxs":
            saxs_engine = getattr(self, "_engine_cache", {}).get("saxs")
            export_bundle = getattr(saxs_engine, "export_bundle", None)
            if callable(export_bundle):
                try:
                    saxs_bundle = export_bundle(os.path.join(save_root, "saxs_bundle"))
                    self.log(
                        f"SAXS bundle export: {getattr(saxs_bundle, 'status', 'unknown')}"
                    )
                except Exception as exc:
                    self.log(f"SAXS bundle export skipped: {exc}")

        report_path = ""
        try:
            from ..core.report import generate_report, save_report

            html = generate_report(
                project_name=self._project_label.text(),
                output_dir=self._output_dir,
                dsc_results=[self._results.get("dsc")] if "dsc" in result_keys else None,
                waxs_results=[self._results.get("waxs")] if "waxs" in result_keys else None,
                saxs_results=[self._results.get("saxs")] if "saxs" in result_keys else None,
                ir_results=[self._results.get("ir")] if "ir" in result_keys else None,
                nmr_results=[self._results.get("nmr")] if "nmr" in result_keys else None,
            )

            report_path = save_report(html, str(bundle_dirs["report"]))
            self.log(tr("LOG_REPORT_PATH", report_path))
        except Exception as e:
            self.log(tr("LOG_REPORT_SKIPPED").format(e))
            logger.warning("Failed to generate analysis report.", exc_info=True)

        export_context = self._export_context_payload(report_path=report_path)
        primary_report = export_relative_report_path(report_path, save_root)
        write_export_manifest(
            save_root,
            project_name=self._project_label.text().strip(),
            exported_at=datetime.now().isoformat(),
            bundle_root=str(save_root),
            source_output_dir=str(self._output_dir or ""),
            source_data_path=str(self._current_filepath or ""),
            current_technique=str(self._current_technique or ""),
            current_submodule=str(getattr(self, "_current_submodule_id", "") or ""),
            input_mode=str(getattr(self, "_current_input_mode", "") or ""),
            included_techniques=result_keys,
            copied_sections=copied_sections or [],
            primary_report=primary_report,
            task_context=export_context,
        )

        techniques = ", ".join(sorted(str(key).upper() for key in result_keys))
        if not techniques:
            techniques = "None"
        joint_summary = str(export_context.get("joint_summary") or "").strip()
        history_context = (
            export_context.get("history_context")
            if isinstance(export_context.get("history_context"), dict)
            else {}
        )
        joint_context = (
            history_context.get("joint_ai_context")
            if isinstance(history_context.get("joint_ai_context"), dict)
            else {}
        )
        if not joint_summary and isinstance(joint_context, dict):
            joint_summary = str(joint_context.get("summary") or "").strip()
        joint_reminder = self._joint_ai_reminder_text(joint_context) if isinstance(joint_context, dict) and joint_context else ""
        joint_compare_hint = self._joint_compare_hint_text(joint_context) if isinstance(joint_context, dict) and joint_context else ""
        joint_detail = compose_joint_export_detail(
            joint_summary=joint_summary,
            joint_reminder=joint_reminder,
            joint_compare_hint=joint_compare_hint,
        )

        write_export_readme(
            save_root,
            project_name=self._project_label.text().strip(),
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            techniques=techniques,
            source_data_path=str(self._current_filepath or ""),
            primary_report=primary_report,
            export_context=export_context,
            joint_detail=joint_detail,
            confirmed_review_label=tr("RESULTS_REVIEW_CONFIRMED"),
        )
        self._last_export_bundle = save_root
        self._save_settings()
        self._update_workspace_context()
        self.log(tr("LOG_EXPORT_DONE").format(save_root))
