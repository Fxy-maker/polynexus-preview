from __future__ import annotations

import os

from .i18n import tr
from .error_diagnostic_service import build_error_diagnostic
from .run_state_service import (
    cancellation_requested,
    should_publish_result,
    transition_run_state,
)
from .workspace_mode import WorkspaceMode


class MainWindowRunMixin:
    def _transition_run_state(self, event):
        self._run_state = transition_run_state(getattr(self, "_run_state", None), event)
        return self._run_state

    def _start_run_lifecycle(self):
        return self._transition_run_state("start")

    def _run_cancellation_requested(self):
        return cancellation_requested(getattr(self, "_run_state", None))

    def _record_error_diagnostic(self, msg, *, operation="analysis"):
        raw_message = str(msg or "").strip()
        message, separator, detail = raw_message.partition("\n")
        self._last_error_diagnostic = build_error_diagnostic(
            operation=operation,
            message=message or raw_message,
            detail=detail if separator else "",
            recovery=tr("RUN_ERROR_RECOVERY_RETRY"),
        )

    def _hide_error_diagnostics(self):
        self._last_error_diagnostic = None
        for attr in ("_btn_retry", "_btn_copy_diagnostics"):
            button = getattr(self, attr, None)
            if button is not None:
                button.setVisible(False)

    def _copy_error_diagnostics(self):
        payload = getattr(self, "_last_error_diagnostic", None)
        if payload is None:
            return False
        QApplication = self._main_window_module().QApplication
        QApplication.clipboard().setText(payload.copy_text)
        self.log(tr("LOG_DIAGNOSTICS_COPIED"))
        return True

    def _on_run_stage(self, stage):
        key = str(stage or "").strip().lower()
        if not key:
            return
        self._run_stage_key = key
        label = tr({
            "reading": "RUN_STAGE_READING",
            "processing": "RUN_STAGE_PROCESSING",
            "exporting": "RUN_STAGE_EXPORTING",
        }.get(key, "RUN_STAGE_PROCESSING"))
        if hasattr(self, "_workflow_metric_state"):
            self._workflow_metric_state.setText(label)
        if hasattr(self, "_progress"):
            self._progress.setToolTip(label)

    def _connect_worker_lifecycle(self, worker):
        worker.stage.connect(self._on_run_stage)
        cancelled = getattr(worker, "cancelled", None)
        if cancelled is not None:
            cancelled.connect(self._on_worker_cancelled)

    def _on_worker_cancelled(self, *, clear_request=True):
        self._transition_run_state("cancelled")
        self._hide_error_diagnostics()
        self._stop_progress_animation_fn()(self._progress)
        self._progress.setVisible(False)
        self._set_running_ui(False, tr("RUN_CANCELLED"))
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("BTN_RUN"))
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)
        if hasattr(self, "_btn_retry"):
            self._btn_retry.setVisible(False)
        self.log(tr("RUN_CANCELLED"))

    def _cancel_run(self):
        worker = None
        for attr in (
            "_worker",
            "_batch_worker",
            "_joint_worker",
            "_saxs_orientation_advisory_worker",
        ):
            candidate = getattr(self, attr, None)
            if candidate is None:
                continue
            is_running = getattr(candidate, "isRunning", None)
            if not callable(is_running) or is_running():
                worker = candidate
                break
        if worker is None:
            return False
        cancel = getattr(worker, "cancel", None)
        if attr == "_saxs_orientation_advisory_worker":
            if callable(cancel):
                cancel()
            elif hasattr(worker, "requestInterruption"):
                worker.requestInterruption()
            return True
        self._transition_run_state("cancel")
        if callable(cancel):
            cancel()
        elif hasattr(worker, "requestInterruption"):
            worker.requestInterruption()
        self._on_worker_cancelled(clear_request=False)
        return True
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    @classmethod
    def _analysis_worker_class(cls):
        return cls._main_window_module().AnalysisWorker

    @classmethod
    def _batch_worker_class(cls):
        return cls._main_window_module().BatchWorker

    @classmethod
    def _joint_hub_worker_class(cls):
        return cls._main_window_module().JointHubWorker

    @classmethod
    def _message_box_class(cls):
        return cls._main_window_module().QMessageBox

    @classmethod
    def _get_engine_fn(cls):
        return cls._main_window_module().get_engine

    @classmethod
    def _check_file_format_fn(cls):
        return cls._main_window_module().check_file_format

    @classmethod
    def _start_progress_animation_fn(cls):
        return cls._main_window_module().start_progress_animation

    @classmethod
    def _stop_progress_animation_fn(cls):
        return cls._main_window_module().stop_progress_animation

    @classmethod
    def _logger(cls):
        return cls._main_window_module().logger

    def _run_analysis(self):
        if not self._current_technique:
            self.log(tr("LOG_NO_TECHNIQUE"))
            return

        if self._workspace_mode_value() is WorkspaceMode.JOINT:
            self._run_joint_hub()
            return

        if not self._current_filepath:
            self.log(tr("LOG_NO_DATA_FILE"))
            return

        if os.path.isdir(self._current_filepath):
            self._output_dir = os.path.join(self._current_filepath, "polynexus_output")
        else:
            self._output_dir = os.path.join(
                os.path.dirname(self._current_filepath),
                "polynexus_output",
            )

        os.makedirs(self._output_dir, exist_ok=True)
        self._analysis_warning_count_before = self._read_warning_count()

        if not self._validate_calibration_inputs():
            return
        if not self._validate_mask_inputs():
            return

        self._save_recent_calibration()

        if os.path.isdir(self._current_filepath):
            self._run_batch()
        else:
            self._run_single()

    def _run_joint_hub(self):
        hub = getattr(self, "_joint_hub", None)
        if hub is None:
            self.log(tr("LOG_JOINT_HUB_UNAVAILABLE"))
            return

        rows = hub.selected_rows()
        if not rows:
            self.log(tr("LOG_JOINT_SELECT_BATCH"))
            return

        if hasattr(self, "_output_input") and self._output_input.text().strip():
            self._output_dir = self._output_input.text().strip()
        if not self._output_dir:
            self._output_dir = os.path.join(os.getcwd(), "polynexus_joint_output")

        os.makedirs(self._output_dir, exist_ok=True)

        self._hide_error_diagnostics()
        self._start_run_lifecycle()
        self._btn_run.setEnabled(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(True)
        self._btn_run.setText(tr("BTN_RUNNING"))
        self._progress.setVisible(True)
        self._start_progress_animation_fn()(self._progress)
        self._set_running_ui(True, tr("WORKFLOW_RUNNING_JOINT"))

        worker_class = self._joint_hub_worker_class()
        self._joint_worker = worker_class(rows, self._output_dir)
        self._joint_worker.finished.connect(self._on_joint_hub_finished)
        self._joint_worker.error_msg.connect(self._on_joint_hub_error)
        self._joint_worker.start()

    def _on_joint_hub_finished(self, report):
        self._transition_run_state("complete")
        if not should_publish_result(self._run_state):
            return self._on_worker_cancelled()
        self._hide_error_diagnostics()
        self._stop_progress_animation_fn()(self._progress)
        self._progress.setVisible(False)
        self._set_running_ui(False)

        self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))
        self._btn_run.setEnabled(True)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)

        hub = getattr(self, "_joint_hub", None)
        self._btn_run.setEnabled(hub is not None and hub.has_selection())

        self._joint_report = report
        self._results["joint"] = report
        self._save_joint_hub_artifacts(report)
        self._display_joint_report(report)
        self._populate_plots()
        self._tabs.setCurrentIndex(2)
        self._btn_replot.setEnabled(False)
        self._persist_analysis_run(report)
        self._update_workspace_context()
        self.log(tr("LOG_JOINT_OVERVIEW_DONE", report.get("summary", "")))

        interesting = [
            item
            for item in report.get("validations", [])
            if item.get("severity") in {"WARN", "ERROR"}
        ]
        for item in interesting[:8]:
            severity = str(item.get("severity") or "")
            message = str(item.get("message") or "")
            if severity == "ERROR":
                self.log(tr("LOG_JOINT_VALIDATION_ERROR", message))
            else:
                self.log(tr("LOG_JOINT_VALIDATION_WARN", message))
        if len(interesting) > 8:
            self.log(tr("LOG_JOINT_VALIDATION_MORE", len(interesting) - 8))

    def _analysis_worker_kwargs(self, *, config, submodule_id, mask_edit_candidate=None):
        kwargs = {"config": config, "submodule_id": submodule_id}
        if mask_edit_candidate is not None:
            kwargs["mask_edit_candidate"] = mask_edit_candidate
        return kwargs

    def _run_single(self, *, mask_edit_candidate=None):
        self._start_run_lifecycle()
        self._hide_error_diagnostics()
        self._set_results_summary("")
        self._set_results_export_control_visible(False)
        self._set_results_copy_control_visible(False)
        self._clear_results_table_default_order()

        submodule_id = getattr(self, "_current_submodule_id", None)
        engine = self._get_engine_fn()(self._current_technique, submodule_id=submodule_id)
        message_box = self._message_box_class()
        logger = self._logger()

        if engine and self._current_filepath:
            try:
                self._check_file_format_fn()(self._current_technique, self._current_filepath)
            except ValueError as exc:
                logger.warning("File format validation failed: %s", exc)
                message_box.warning(
                    self,
                    tr("FILE_FORMAT_UNSUPPORTED"),
                    tr("FILE_FORMAT_UNSUPPORTED_DETAIL", exc),
                )
                return

        if engine and self._current_filepath:
            ok, msg = engine.check_file_compatibility(self._current_filepath)
            if not ok:
                self.log(tr("LOG_WARNING_DETAIL", msg))
                reply = message_box.warning(
                    self,
                    tr("DIALOG_MISMATCH_TITLE"),
                    tr("DIALOG_MISMATCH_MSG", msg),
                    message_box.Yes | message_box.No,
                    message_box.No,
                )
                if reply == message_box.No:
                    return

        self.log(tr("LOG_RUN_MODE_SINGLE", os.path.basename(self._current_filepath)))

        self._btn_run.setEnabled(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(True)
        self._btn_run.setText(tr("BTN_RUNNING"))
        self._progress.setVisible(True)
        self._start_progress_animation_fn()(self._progress)
        self._set_running_ui(True, tr("WORKFLOW_RUNNING_SINGLE"))

        config = self._build_run_config()
        worker_class = self._analysis_worker_class()
        self._worker = worker_class(
            self._current_technique,
            self._current_filepath,
            self._output_dir,
            **self._analysis_worker_kwargs(
                config=config,
                submodule_id=submodule_id,
                mask_edit_candidate=mask_edit_candidate,
            ),
        )
        self._worker.log_msg.connect(self.log)
        self._connect_worker_lifecycle(self._worker)
        self._worker.finished.connect(self._on_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.start()

    def _run_batch(self):
        fp = self._current_filepath
        submodule_id = getattr(self, "_current_submodule_id", None)
        self._set_results_summary("")

        native_directory_run = (
            self._current_technique in ("saxs", "waxs")
            or self._current_technique == "nmr"
            or submodule_id in ("dsc.isothermal", "dsc.nonisothermal", "ir.temperature_2d")
        )
        if native_directory_run:
            self._start_run_lifecycle()
            self._hide_error_diagnostics()
            mode_label = (
                tr("IMPORT_MODE_SEQUENCE")
                if str(getattr(self, "_current_input_mode", "") or "").strip().lower() == "sequence"
                else tr("IMPORT_MODE_DIRECTORY")
            )
            self.log(tr("LOG_RUN_MODE_NATIVE_DIRECTORY", mode_label, os.path.basename(fp.rstrip("/\\"))))
            self._batch_list.clear()
            self._batch_list.setVisible(False)
            self._update_batch_list_copy_button()
            self._btn_run.setEnabled(False)
            if hasattr(self, "_btn_cancel"):
                self._btn_cancel.setVisible(True)
            self._btn_run.setText(tr("BTN_RUNNING"))
            self._progress.setVisible(True)
            self._start_progress_animation_fn()(self._progress)
            running_label = (
                tr("WORKFLOW_RUNNING_SEQUENCE")
                if str(getattr(self, "_current_input_mode", "") or "").strip().lower() == "sequence"
                else tr("WORKFLOW_RUNNING_DIRECTORY")
            )
            self._set_running_ui(True, running_label)
            worker_class = self._analysis_worker_class()
            self._worker = worker_class(
                self._current_technique,
                fp,
                self._output_dir,
                config=self._build_run_config(),
                submodule_id=submodule_id,
            )
            self._worker.log_msg.connect(self.log)
            self._connect_worker_lifecycle(self._worker)
            self._worker.finished.connect(self._on_finished)
            self._worker.error_msg.connect(self._on_error)
            self._worker.start()
            return

        exts = {".edf", ".csv", ".txt", ".dat", ".xlsx", ".xls", ".001", ".raw", ".spa", ".jdf", ".bin"}
        file_list = sorted(
            [
                os.path.join(fp, filename)
                for filename in os.listdir(fp)
                if os.path.isfile(os.path.join(fp, filename))
                and os.path.splitext(filename)[1].lower() in exts
            ]
        )

        if not file_list:
            self.log(tr("LOG_NO_SUPPORTED_FILES"))
            return

        self.log(tr("LOG_RUN_MODE_BATCH", len(file_list), os.path.basename(fp.rstrip("/\\"))))

        self._btn_run.setEnabled(False)
        self._start_run_lifecycle()
        self._hide_error_diagnostics()
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(True)
        self._btn_run.setText(tr("BTN_BATCH"))
        self._progress.setVisible(True)
        self._progress.setRange(0, len(file_list))
        self._progress.setValue(0)
        self._set_running_ui(True, tr("WORKFLOW_RUNNING_BATCH"))

        self._batch_list.clear()
        self._batch_list.setVisible(True)
        self._update_batch_list_copy_button()
        for filename in file_list:
            self._batch_list.addItem(os.path.basename(filename))

        worker_class = self._batch_worker_class()
        self._batch_worker = worker_class(
            self._current_technique,
            file_list,
            self._output_dir,
            config=self._build_run_config(),
            submodule_id=submodule_id,
        )
        self._batch_worker.log_msg.connect(self.log)
        self._connect_worker_lifecycle(self._batch_worker)
        self._batch_worker.progress.connect(lambda current, total: self._progress.setValue(current))
        self._batch_worker.file_done.connect(self._on_batch_file_done)
        self._batch_worker.batch_finished.connect(self._on_batch_finished)
        self._batch_worker.error_msg.connect(self._on_error)
        self._batch_worker.start()

    def _replot(self):
        if not self._current_technique:
            self.log(tr("LOG_NO_TECHNIQUE"))
            return

        if not self._current_filepath:
            self.log(tr("LOG_NO_DATA_FILE"))
            return

        if not self._output_dir:
            self.log(tr("LOG_NO_OUTPUT_DIR"))
            return

        self._hide_error_diagnostics()
        self._start_run_lifecycle()
        self._btn_replot.setEnabled(False)
        self._btn_replot.setText(tr("BTN_REPLOTTING"))
        if hasattr(self, "_workflow_metric_state"):
            self._workflow_metric_state.setText(tr("BTN_REPLOTTING"))

        config = self._build_run_config()
        submodule_id = getattr(self, "_current_submodule_id", None)
        cached_engine = self._engine_cache.get(self._current_technique)

        if cached_engine is None:
            self.log(tr("LOG_REPLOT_CACHE_MISS"))

        worker_class = self._analysis_worker_class()
        self._worker = worker_class(
            self._current_technique,
            self._current_filepath,
            self._output_dir,
            config=config,
            submodule_id=submodule_id,
            engine=cached_engine,
        )
        self._worker.log_msg.connect(self.log)
        self._connect_worker_lifecycle(self._worker)
        self._worker.finished.connect(self._on_replot_finished)
        self._worker.error_msg.connect(self._on_error)
        self._worker.skip_to = "plot" if cached_engine is not None else None
        self._worker.start()

        if cached_engine is not None:
            self.log(tr("LOG_REPLOT_START_CACHED"))
        else:
            self.log(tr("LOG_REPLOT_START_FALLBACK"))

    def _on_replot_finished(self, result):
        self._transition_run_state("complete")
        if not should_publish_result(self._run_state):
            return self._on_worker_cancelled()
        self._hide_error_diagnostics()
        self._btn_replot.setEnabled(True)
        self._btn_replot.setText(tr("BTN_REPLOT"))
        self._set_running_ui(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)

        self._results[self._current_technique] = result
        record_context = getattr(self, "_record_result_context", None)
        if callable(record_context):
            record_context(
                self._current_technique,
                status="complete",
                run_id=getattr(self, "_last_persisted_run_id", ""),
            )
        if self._worker is not None and getattr(self._worker, "engine", None) is not None:
            self._engine_cache[self._current_technique] = self._worker.engine

        self._populate_plots()
        self._update_results_compare_panel()
        self._update_results_confirm_panel()
        self._tabs.setCurrentIndex(3)
        self.log(tr("LOG_REPLOT_DONE"))

    def _log_analysis_diagnostics(self, result):
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        validation_summary = str(getattr(result, "validation_summary", "") or "").strip()
        if validation_summary and validation_summary != "All checks passed":
            self.log(tr("LOG_ANALYSIS_VALIDATION_SUMMARY", validation_summary))

        if technique != "saxs":
            return

        if bool(getattr(result, "mask_truncated", False)):
            eff_q = getattr(result, "effective_q_min", 0.0)
            try:
                eff_q_text = f"{float(eff_q):.3f}"
            except Exception:
                eff_q_text = "0.000"
            self.log(tr("LOG_SAXS_MASK_TRUNCATED", eff_q_text))

        if bool(getattr(result, "beam_stop_contaminated", False)):
            eff_q = getattr(result, "effective_q_min", 0.0)
            try:
                eff_q_text = f"{float(eff_q):.3f}"
            except Exception:
                eff_q_text = "0.000"
            self.log(tr("LOG_SAXS_BEAMSTOP_WARNING", eff_q_text))

    def _log_run_completion_summary(self, result):
        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        if mode not in {"sequence", "directory"}:
            return

        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        params = getattr(result, "parameters", None)
        batch_frames = 0
        if isinstance(params, dict):
            try:
                batch_frames = int(params.get("batch_frames", 0) or 0)
            except Exception:
                batch_frames = 0

        if mode == "sequence":
            if batch_frames > 1:
                self.log(tr("LOG_SEQUENCE_RUN_DONE", batch_frames, source_name))
            else:
                self.log(tr("LOG_SEQUENCE_RUN_DONE_FALLBACK", source_name))
            return

        if batch_frames > 1:
            self.log(tr("LOG_DIRECTORY_RUN_DONE", batch_frames, source_name))
        else:
            self.log(tr("LOG_DIRECTORY_RUN_DONE_FALLBACK", source_name))

    def _on_finished(self, result):
        self._transition_run_state("complete")
        if not should_publish_result(self._run_state):
            return self._on_worker_cancelled()
        self._hide_error_diagnostics()
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("BTN_RUN"))
        self._stop_progress_animation_fn()(self._progress)
        self._progress.setVisible(False)
        self._set_running_ui(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)

        transaction = getattr(self, "_preprocess_transaction", None)
        finalize_preprocess = getattr(self, "_finalize_preprocess_apply_success", None)
        transaction_pending = transaction is not None and getattr(
            transaction.state, "phase", ""
        ) in {"apply_pending", "undo_pending"}
        if transaction_pending and callable(finalize_preprocess):
            if not finalize_preprocess(result):
                # The transaction restored the original result/config. Do not
                # publish or persist the rejected candidate result.
                self._populate_plots()
                self._update_workspace_context()
                self._update_results_compare_panel()
                self._last_ai_tuned_run = False
                return

        self._results[self._current_technique] = result
        if self._worker is not None and getattr(self._worker, "engine", None) is not None:
            self._engine_cache[self._current_technique] = self._worker.engine

        self.log(tr("LOG_ANALYSIS_DONE"))
        self._append_analysis_warning_summary()
        self._log_analysis_diagnostics(result)
        self._log_run_completion_summary(result)

        self._btn_replot.setEnabled(bool(self._output_dir))
        if hasattr(result, "parameters") and result.parameters:
            self._display_results(result.parameters, result)

        self._populate_plots()
        self._tabs.setCurrentIndex(2)
        self._persist_analysis_run(result)
        # Persistence assigns the stable run id; keep the in-memory result tied
        # to that exact workspace identity before any view is refreshed.
        record_context = getattr(self, "_record_result_context", None)
        if callable(record_context):
            record_context(
                self._current_technique,
                status="complete",
                run_id=getattr(self, "_last_persisted_run_id", ""),
            )
        self._update_workspace_context()
        self._update_results_compare_panel()
        if (
            transaction_pending
            and getattr(transaction.state, "phase", "") == "applied"
            and bool(getattr(self, "_preprocess_undo_requested", False))
        ):
            self._preprocess_undo_requested = False
            undo = getattr(self, "_undo_last_preprocess_apply", None)
            if callable(undo):
                undo()
        if transaction_pending:
            record_audit = getattr(self, "_record_preprocess_transaction_audit", None)
            if callable(record_audit):
                record_audit(getattr(transaction.state, "audit", {}))
        self._last_ai_tuned_run = False

    def _on_joint_hub_error(self, msg):
        if self._run_cancellation_requested():
            return self._on_worker_cancelled()
        self._transition_run_state("fail")
        self._record_error_diagnostic(msg, operation="joint analysis")
        self._stop_progress_animation_fn()(self._progress)
        self._progress.setVisible(False)
        self._set_running_ui(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("BTN_GENERATE_OVERVIEW"))
        hub = getattr(self, "_joint_hub", None)
        if hub is not None:
            self._btn_run.setEnabled(hub.has_selection())
        if hasattr(self, "_btn_retry"):
            self._btn_retry.setVisible(True)
        if hasattr(self, "_btn_copy_diagnostics"):
            self._btn_copy_diagnostics.setVisible(True)
        self.log(tr("LOG_ERROR_DETAIL", msg))

    def _on_error(self, msg):
        if self._run_cancellation_requested():
            return self._on_worker_cancelled()
        self._transition_run_state("fail")
        self._record_error_diagnostic(msg)
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("BTN_RUN"))
        self._stop_progress_animation_fn()(self._progress)
        self._progress.setVisible(False)
        self._set_running_ui(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)
        if hasattr(self, "_btn_retry"):
            self._btn_retry.setVisible(True)
        if hasattr(self, "_btn_copy_diagnostics"):
            self._btn_copy_diagnostics.setVisible(True)
        self.log(tr("LOG_ERROR_DETAIL", msg))
        self._append_analysis_warning_summary()
        rollback_preprocess = getattr(self, "_rollback_preprocess_apply_failure", None)
        if callable(rollback_preprocess):
            rollback_preprocess()

    def _on_batch_file_done(self, filename, params):
        self._batch_results.append({"file": filename, "params": params})

    def _on_batch_finished(self, all_results):
        self._transition_run_state("complete")
        if not should_publish_result(self._run_state):
            return self._on_worker_cancelled()
        self._hide_error_diagnostics()
        self._btn_run.setEnabled(True)
        self._btn_run.setText(tr("BTN_RUN"))
        self._stop_progress_animation_fn()(self._progress)
        self._progress.setVisible(False)
        self._batch_list.setVisible(False)
        self._update_batch_list_copy_button()
        self._set_running_ui(False)
        if hasattr(self, "_btn_cancel"):
            self._btn_cancel.setVisible(False)

        self.log(tr("LOG_BATCH_DONE").format(len(all_results)))
        self._hide_joint_diagnostics()
        self._set_results_summary("")
        self._results_table.setSortingEnabled(False)
        self._set_results_export_control_visible(False)
        self._set_results_copy_control_visible(False)
        self._clear_results_table_default_order()

        if all_results:
            self._show_batch_results(all_results)
            self._populate_plots()
            self._tabs.setCurrentIndex(2)
