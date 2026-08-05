from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QLineEdit, QSpinBox

from ..core.saxs_engine.saxs_ai_rescue import (
    assess_saxs_confirmed_rerun,
    validate_saxs_confirmation_report,
)
from .analysis_history_service import (
    ai_tuning_benchmark_delta_text,
    ai_tuning_benchmark_rate_text,
    ai_tuning_chain_stats,
    ai_tuning_chain_summary,
    ai_tuning_previous_round_summary_text,
    ai_tuning_report_context as build_ai_tuning_report_context,
    ai_tuning_tunable_summary_text,
)
from .i18n import get_language, tr
from .preprocess_decision_service import build_preprocess_ui_decision
from .preprocess_transaction_service import PreprocessTransactionService


class MainWindowAITuningMixin:
    @staticmethod
    def _main_window_module():
        from . import main_window as main_window_module

        return main_window_module

    @classmethod
    def _ai_tuning_goal_dialog_class(cls):
        return cls._main_window_module().AITuningGoalDialog

    @classmethod
    def _message_box_class(cls):
        return cls._main_window_module().QMessageBox

    @classmethod
    def _progress_dialog_class(cls):
        return cls._main_window_module().QProgressDialog

    @classmethod
    def _ai_tune_worker_class(cls):
        return cls._main_window_module().AITuneWorker

    @classmethod
    def _thread_pool_class(cls):
        return cls._main_window_module().QThreadPool

    @classmethod
    def _side_tuning_report_dialog_class(cls):
        return cls._main_window_module().SideTuningReportDialog

    @classmethod
    def _detect_polymer_type_fn(cls):
        return cls._main_window_module().detect_polymer_type

    @classmethod
    def _load_defaults_fn(cls):
        return cls._main_window_module().load_defaults

    @classmethod
    def _load_ai_settings_fn(cls):
        return cls._main_window_module().load_ai_settings

    @classmethod
    def _logger(cls):
        return cls._main_window_module().logger

    def on_ai_tune_clicked(self):
        message_box = self._message_box_class()
        if not self._current_technique or self._current_technique in {"joint", "samples"}:
            message_box.warning(self, tr("AI_TUNING_TITLE"), tr("AI_TUNING_REQUIRE_TECH"))
            return
        if not self._current_filepath:
            message_box.warning(self, tr("AI_TUNING_TITLE"), tr("AI_TUNING_REQUIRE_FILE"))
            return

        current_goal = self._current_tuning_goal()
        goal_dialog = self._ai_tuning_goal_dialog_class()(self, current_goal=current_goal)
        if goal_dialog.exec() != QDialog.Accepted:
            return

        current_goal = goal_dialog.selected_goal()
        self._current_ai_tuning_goal = current_goal
        context_summary = self._ai_tuning_context_summary()
        answer = message_box.question(
            self,
            tr("AI_TUNING_TITLE"),
            tr("AI_TUNING_CONFIRM_MESSAGE", context_summary),
            message_box.Yes | message_box.No,
            message_box.Yes,
        )
        if answer != message_box.Yes:
            return

        sample_name = self._infer_sample_name()
        polymer = self._detect_polymer_type_fn()(sample_name or "")
        defaults = self._load_defaults_fn()(polymer)
        self._current_polymer_type = polymer
        self._current_polymer_defaults = defaults
        self._logger().info(
            "AI tuning started: technique=%s sample=%s polymer_type=%s goal=%s",
            self._current_technique,
            sample_name,
            polymer,
            current_goal,
        )
        self._ai_tuning_active = True
        self._update_workflow_task_card()
        submodule_id = getattr(self, "_current_submodule_id", None)
        self._ai_progress = self._progress_dialog_class()(
            tr("AI_TUNING_PROGRESS"),
            tr("COMMON_CANCEL"),
            0,
            0,
            self,
        )
        self._ai_progress.setWindowTitle(tr("AI_TUNING_TITLE"))
        self._ai_progress.setMinimumDuration(0)
        self._ai_progress.setAutoClose(False)
        workspace_context = self._ai_tuning_workspace_context()
        workspace_context["tuning_goal"] = current_goal
        workspace_context["tuning_goal_label"] = self._ai_tuning_goal_label(current_goal)
        # SAXS AI tuning always performs the bounded stability study. The
        # report remains candidate-only until the existing confirmation
        # transaction accepts it.
        if str(self._current_technique or "").strip().lower() == "saxs":
            workspace_context["stability_mode"] = "strict"
        ai_settings = self._current_ai_settings()
        worker_class = self._ai_tune_worker_class()
        self._ai_worker = worker_class(
            self._current_technique,
            self._current_filepath,
            polymer,
            rounds=5,
            submodule_id=submodule_id,
            workspace_context=workspace_context,
            ai_settings=ai_settings,
        )
        self._ai_progress.canceled.connect(self._ai_worker.cancel)
        self._ai_worker.signals.progress_msg.connect(self._on_ai_tune_progress)
        self._ai_worker.signals.finished.connect(self._on_ai_tune_finished)
        self._ai_worker.signals.error_msg.connect(self._on_ai_tune_error)
        self._ai_progress.show()
        self._thread_pool_class().globalInstance().start(self._ai_worker)

    def _current_ai_settings(self):
        return self._load_ai_settings_fn()(self._settings)

    def _ai_tuning_workspace_context(self):
        current_key = str(self._current_technique or "").strip().lower()
        joint_report = self._joint_report if isinstance(self._joint_report, dict) else {}
        workspace_context = {
            "summary": self._workspace_context_summary(),
            "joint_report": joint_report,
            "current_result": self._results.get(current_key, {}) if isinstance(self._results, dict) else {},
            "work_memory": self._work_memory_payload(),
            "tuning_goal": self._current_tuning_goal(),
            "tuning_goal_label": self._ai_tuning_goal_label(self._current_tuning_goal()),
        }
        joint_ai_context = self._joint_ai_context()
        if joint_ai_context:
            workspace_context["joint_ai_context"] = joint_ai_context
        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict) and tuning_context:
            workspace_context["tuning_context"] = tuning_context
        return workspace_context

    def _current_tuning_goal(self) -> str:
        goal = getattr(self, "_current_ai_tuning_goal", "")
        goal = str(goal or "").strip().lower()
        return goal if goal in {"symptom", "risk", "joint", "stability"} else "symptom"

    def _ai_tuning_goal_label(self, goal: str) -> str:
        goal = str(goal or "").strip().lower()
        return {
            "symptom": tr("AI_TUNING_GOAL_SYMPTOM"),
            "risk": tr("AI_TUNING_GOAL_RISK"),
            "joint": tr("AI_TUNING_GOAL_JOINT"),
            "stability": tr("AI_TUNING_GOAL_STABILITY"),
        }.get(goal, tr("AI_TUNING_GOAL_SYMPTOM"))

    def _ai_tuning_context_summary(self):
        technique = self._history_technique_text(str(self._current_technique or ""))
        submodule = self._history_submodule_text(str(getattr(self, "_current_submodule_id", "") or ""))
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        mode_text = {
            "sequence": tr("AI_TUNING_CONTEXT_SEQUENCE"),
            "directory": tr("AI_TUNING_CONTEXT_DIRECTORY"),
        }.get(mode, tr("AI_TUNING_CONTEXT_SINGLE"))
        result_summary = ""
        if hasattr(self, "_results_summary_risk_label"):
            result_summary = str(self._results_summary_risk_label.text() or "").strip()
        if not result_summary and hasattr(self, "_results_summary_label"):
            result_summary = str(self._results_summary_label.text() or "").strip()
        if not result_summary:
            result_summary = tr("AI_TUNING_CONTEXT_NO_RISK")
        goal_text = self._ai_tuning_goal_label(self._current_tuning_goal())
        previous_round = self._ai_tuning_previous_round_summary()
        tunable_summary = self._ai_tuning_tunable_summary()
        template = (
            "Technique: {}\nSub-module: {}\nInput mode: {}\nData source: {}\nCurrent result note: {}\nCurrent focus: {}\nPrevious round context:\n{}\nPlanned tuning parameters:\n{}"
            if get_language() != "zh"
            else "技术：{}\n子模块：{}\n输入模式：{}\n数据来源：{}\n当前结果提示：{}\n当前关注点：{}\n上一轮上下文：\n{}\n预定优化参数：\n{}"
        )
        return template.format(
            technique or tr("WORKFLOW_TASK_NO_TECH"),
            submodule or tr("WORKFLOW_SUBMODULE_NONE"),
            mode_text,
            source_name,
            result_summary,
            goal_text,
            previous_round,
            tunable_summary,
        )

    def _ai_tuning_previous_round_summary(self):
        return ai_tuning_previous_round_summary_text(
            getattr(self, "_last_ai_tuning_context", {}),
            label_text=self._ai_tuning_previous_round_label(),
            empty_text=self._ai_tuning_previous_round_empty_text(),
            stop_text_fn=self._ai_tuning_previous_round_stop_text,
            risks_text_fn=self._ai_tuning_previous_round_risks_text,
            goal_text_fn=self._ai_tuning_previous_round_goal_text,
        )

    def _benchmark_delta_text(self, value) -> str:
        return ai_tuning_benchmark_delta_text(value)

    def _benchmark_rate_text(self, value) -> str:
        return ai_tuning_benchmark_rate_text(value)

    def _benchmark_summary_text(self, benchmark_summary) -> str:
        if not isinstance(benchmark_summary, dict) or not benchmark_summary:
            return ""
        return tr(
            "AI_TUNING_REPORT_BENCHMARK",
            self._benchmark_delta_text(benchmark_summary.get("average_objective_delta")),
            self._benchmark_rate_text(benchmark_summary.get("acceptance_rate")),
            self._benchmark_rate_text(benchmark_summary.get("rejection_rate")),
            self._benchmark_rate_text(benchmark_summary.get("constraint_hit_rate")),
            self._benchmark_rate_text(benchmark_summary.get("symptom_fix_rate")),
        )

    def _ai_tuning_report_context(self, report):
        return build_ai_tuning_report_context(
            report,
            benchmark_summary_text_fn=self._benchmark_summary_text,
            accepted_summary_text_fn=self._ai_tuning_previous_round_accepted_text,
            empty_text_fn=self._ai_tuning_previous_round_empty_text,
            stop_text_fn=self._ai_tuning_previous_round_stop_text,
            risks_text_fn=self._ai_tuning_previous_round_risks_text,
            goal_body_fn=self._ai_tuning_previous_round_goal_body,
            goal_text_fn=self._ai_tuning_previous_round_goal_text,
        )

    def _ai_tuning_previous_round_label(self):
        return "上一轮上下文：" if get_language() == "zh" else "Previous round context:"

    def _ai_tuning_previous_round_empty_text(self):
        return "当前还没有可用的上一轮调优上下文" if get_language() == "zh" else "No previous tuning context is available yet"

    def _ai_tuning_previous_round_stop_text(self, stop_reason: str) -> str:
        return f"停止原因：{stop_reason}" if get_language() == "zh" else f"Stop reason: {stop_reason}"

    def _ai_tuning_previous_round_risks_text(self, risks: str) -> str:
        return f"未消除风险：{risks}" if get_language() == "zh" else f"Remaining risks: {risks}"

    def _ai_tuning_previous_round_goal_text(self, goal: str) -> str:
        return f"下一轮目标：{goal}" if get_language() == "zh" else f"Next goal: {goal}"

    def _ai_tuning_previous_round_accepted_text(self, accepted_rounds, best_r2, delta, rounds) -> str:
        if get_language() == "zh":
            return f"上一轮摘要：接受了 {accepted_rounds} 轮；最佳 R2 = {best_r2}；提升 = {delta}；总轮数 = {rounds}"
        return f"Previous round summary: accepted {accepted_rounds} rounds; best R2 = {best_r2}; improvement = {delta}; total rounds = {rounds}"

    def _ai_tuning_previous_round_goal_body(self, focus: str, watch: str) -> str:
        if get_language() == "zh":
            return f"下一轮应尽量保留现有收益，并优先处理 {focus}。同时仍需关注 {watch}"
        return f"The next round should keep the current gains and focus on {focus} while still watching {watch}"

    def _ai_tuning_chain_summary(self, report: dict | None = None) -> str:
        report = report if isinstance(report, dict) else {}
        stats = ai_tuning_chain_stats(
            report,
            benchmark_delta_text_fn=self._benchmark_delta_text,
        )
        if get_language() == "zh":
            parts = [
                f"基线变化：{stats.baseline_hint or 'N/A'}",
                f"接受 {stats.accepted_rounds} 轮，回滚 {stats.rolled_back_rounds} 轮",
            ]
            if stats.best_round is not None:
                parts.append(f"当前最佳：第 {stats.best_round} 轮")
            if stats.last_accepted_round is not None:
                parts.append(f"最新接受：第 {stats.last_accepted_round} 轮")
            if stats.rollback_reasons:
                parts.append(f"保留风险：{'; '.join(stats.rollback_reasons[:2])}")
            return " | ".join(parts)

        parts = [
            f"baseline delta {stats.baseline_hint or 'N/A'}",
            f"accepted {stats.accepted_rounds} rounds, rolled back {stats.rolled_back_rounds} rounds",
        ]
        if stats.best_round is not None:
            parts.append(f"best candidate round {stats.best_round}")
        if stats.last_accepted_round is not None:
            parts.append(f"latest accepted round {stats.last_accepted_round}")
        if stats.rollback_reasons:
            parts.append(f"remaining risks: {'; '.join(stats.rollback_reasons[:2])}")
        return " | ".join(parts)

    def _ai_tuning_tunable_summary(self):
        from polynexus.config_bridge import DSC_PARAM_MAP, IR_PARAM_MAP, NMR_PARAM_MAP, SAXS_PARAM_MAP, WAXS_PARAM_MAP

        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        param_map = {
            "dsc": DSC_PARAM_MAP,
            "ir": IR_PARAM_MAP,
            "nmr": NMR_PARAM_MAP,
            "saxs": SAXS_PARAM_MAP,
            "waxs": WAXS_PARAM_MAP,
        }.get(technique, {})
        return ai_tuning_tunable_summary_text(
            param_map,
            current_value_fn=self._config_value_by_key,
            none_text=tr("AI_TUNING_CONTEXT_TUNABLE_NONE"),
            row_text_fn=lambda name, current, constraint: tr("AI_TUNING_CONTEXT_TUNABLE_ROW", name, current, constraint),
            more_text_fn=lambda remaining: tr("AI_TUNING_CONTEXT_TUNABLE_MORE", remaining),
        )

    def _config_value_by_key(self, key):
        widget = self._config_widget_by_key(key)
        if widget is None:
            return "-"
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QCheckBox):
            return tr("COMMON_ON") if widget.isChecked() else tr("COMMON_OFF")
        if isinstance(widget, QLineEdit):
            return widget.text()
        if hasattr(widget, "text"):
            try:
                return widget.text()
            except Exception:
                return "-"
        return "-"

    def _on_ai_tune_progress(self, message):
        if hasattr(self, "_ai_progress") and self._ai_progress is not None:
            self._ai_progress.setLabelText(message)
        self.log(message)

    def _on_ai_tune_finished(self, report):
        if hasattr(self, "_ai_progress") and self._ai_progress is not None:
            self._ai_progress.close()
        self._ai_tuning_active = False
        self._update_workflow_task_card()
        tuning_context = self._ai_tuning_report_context(report)
        tuning_context["tuning_goal"] = self._current_tuning_goal()
        tuning_context["tuning_goal_label"] = self._ai_tuning_goal_label(self._current_tuning_goal())
        self._last_ai_tuning_context = tuning_context
        self._update_workspace_context()
        self._update_work_memory_panel()
        self._update_results_review_panel()
        dialog = self._side_tuning_report_dialog_class()(report, self)
        dialog_result = dialog.exec()
        if "preprocess_decision" in report:
            view = build_preprocess_ui_decision(report)
            if view.mode == "confirm" and dialog_result == QDialog.Accepted:
                self._begin_preprocess_confirmation(report, accepted_by="user_confirmed")
            elif view.mode == "auto_apply":
                self._register_preprocess_auto_accept(report)
                if dialog_result == QDialog.Accepted:
                    transaction = getattr(self, "_preprocess_transaction", None)
                    if transaction is not None and getattr(transaction.state, "phase", "") == "apply_pending":
                        # The auto-accept rerun is asynchronous; defer Undo
                        # until its result has passed finalize_success().
                        self._preprocess_undo_requested = True
                    else:
                        self._undo_last_preprocess_apply()
        elif dialog_result == QDialog.Accepted:
            self._apply_best_config(dialog.best_config())
            self._last_ai_tuned_run = True
            if hasattr(self, "_tabs"):
                self._tabs.setCurrentIndex(1)
            if hasattr(self, "log"):
                self.log(tr("LOG_AI_TUNING_APPLY_AND_RERUN"))
            self._run_analysis()
        self.log(tr("LOG_AI_TUNING_DONE"))
        try:
            from polynexus.gui.convergence_viewer import load_ai_tune_runs

            load_ai_tune_runs()
        except Exception:
            self._logger().warning("Failed to refresh AI tuning convergence runs.", exc_info=True)

    def _on_ai_tune_error(self, message):
        if hasattr(self, "_ai_progress") and self._ai_progress is not None:
            self._ai_progress.close()
        self._ai_tuning_active = False
        self._update_workflow_task_card()
        self.log(tr("LOG_ERROR_DETAIL", message))
        self._message_box_class().critical(self, tr("AI_TUNING_TITLE"), message)

    def _capture_preprocess_config(self, selected_config):
        snapshot = {}
        for key in selected_config:
            widget_lookup = getattr(self, "_config_widget_by_key", None)
            if callable(widget_lookup) and widget_lookup(key) is None:
                engine = getattr(getattr(self, "_worker", None), "engine", None)
                if engine is None:
                    cache = getattr(self, "_engine_cache", {})
                    engine = cache.get("saxs") if isinstance(cache, dict) else None
                config = getattr(engine, "cfg", None)
                if config is not None and hasattr(config, key):
                    snapshot[key] = deepcopy(getattr(config, key))
                continue
            snapshot[key] = deepcopy(self._config_value_by_key(key))
        return snapshot

    def _saxs_preprocess_mode(self):
        try:
            value = self._config_value_by_key("experiment_type")
        except Exception:
            value = ""
        value = str(value or "").strip().lower()
        if value in {"temperature", "strain"}:
            return value
        cache = getattr(self, "_engine_cache", {})
        cached_engine = cache.get("saxs") if isinstance(cache, dict) else None
        for owner in (getattr(self, "_worker", None), cached_engine):
            engine = getattr(owner, "engine", owner)
            config = getattr(engine, "cfg", None)
            candidate = str(getattr(config, "experiment_type", "") or "").strip().lower()
            if candidate in {"temperature", "strain"}:
                return candidate
            candidate = str(getattr(engine, "_condition_type", "") or "").strip().lower()
            if candidate in {"temperature", "strain"}:
                return candidate
        return "static"

    def _record_preprocess_transaction_audit(self, audit):
        if not isinstance(audit, dict):
            return
        self._last_preprocess_transaction_audit = deepcopy(audit)
        technique = str(getattr(self, "_current_technique", "") or "").lower()
        results = getattr(self, "_results", {})
        result = results.get(technique) if isinstance(results, dict) else None
        engine_cache = getattr(self, "_engine_cache", {})
        engine = engine_cache.get(technique) if isinstance(engine_cache, dict) else None
        for target in (result, engine):
            if target is not None:
                try:
                    setattr(target, "saxs_confirmed_rerun_audit", deepcopy(audit))
                except Exception:
                    pass

    def _assess_saxs_confirmed_rerun(self, result, *, mode):
        """Resolve the mode DTO behind the generic worker result."""

        engine = getattr(getattr(self, "_worker", None), "engine", None)
        if engine is None:
            cache = getattr(self, "_engine_cache", {})
            technique = str(getattr(self, "_current_technique", "") or "").lower()
            engine = cache.get(technique) if isinstance(cache, dict) else None
        if engine is not None:
            if mode == "temperature":
                result = getattr(engine, "_temperature_result", None) or result
            elif mode == "strain":
                result = getattr(engine, "_strain_result", None) or result
            else:
                result = getattr(engine, "_analysis", None) or result
        return assess_saxs_confirmed_rerun(result, mode=mode)

    def _preprocess_transaction_service(self, technique=None):
        service = getattr(self, "_preprocess_transaction", None)
        if service is not None:
            return service
        current_technique = str(
            technique or getattr(self, "_current_technique", "") or ""
        ).strip().lower()

        def get_result():
            results = getattr(self, "_results", {})
            return results.get(current_technique) if isinstance(results, dict) else None

        def set_result(result):
            results = getattr(self, "_results", None)
            if isinstance(results, dict):
                results[current_technique] = result

        service = PreprocessTransactionService(
            capture_config=self._capture_preprocess_config,
            apply_config=self._apply_best_config,
            get_result=get_result,
            set_result=set_result,
            rerun=self._run_analysis,
            persist_experience=self._persist_preprocess_experience_proposal,
            revoke_experience=self._revoke_preprocess_experience,
            technique=current_technique.upper(),
            mode_provider=self._saxs_preprocess_mode if current_technique == "saxs" else None,
            validate_confirmation=(
                validate_saxs_confirmation_report if current_technique == "saxs" else None
            ),
            validate_rerun=(
                self._assess_saxs_confirmed_rerun if current_technique == "saxs" else None
            ),
            record_audit=(
                self._record_preprocess_transaction_audit if current_technique == "saxs" else None
            ),
        )
        self._preprocess_transaction = service
        return service

    def _begin_preprocess_confirmation(self, report, *, accepted_by):
        if not isinstance(report, dict):
            return False
        started = self._preprocess_transaction_service().begin_confirmation(
            report,
            accepted_by=accepted_by,
        )
        if started:
            self._last_ai_tuned_run = True
            if hasattr(self, "_tabs"):
                self._tabs.setCurrentIndex(1)
            if hasattr(self, "log"):
                self.log(tr("LOG_AI_TUNING_APPLY_AND_RERUN"))
        return started

    def _register_preprocess_auto_accept(self, report):
        if not isinstance(report, dict):
            return False
        results = getattr(self, "_results", {})
        current_result = results.get(self._current_technique) if isinstance(results, dict) else None
        return self._preprocess_transaction_service().register_auto_accept(
            report,
            previous_config=report.get("original_preprocess_config"),
            previous_result=current_result,
        )

    def _persist_preprocess_experience_proposal(self, proposal, *, accepted_by):
        if not isinstance(proposal, dict) or not proposal:
            return ""
        from polynexus.core.preprocess_optimization import (
            ExperienceKey,
            ExperienceRecord,
            ExperienceStore,
        )

        key_payload = proposal.get("key", {})
        if not isinstance(key_payload, dict) or not key_payload:
            return ""
        key = ExperienceKey(**key_payload)
        experience_id = str(proposal.get("experience_id", "") or "")
        if not experience_id:
            return ""
        record = ExperienceRecord(
            experience_id=experience_id,
            key=key,
            config_delta=dict(proposal.get("config_delta", {})),
            accepted_by=accepted_by,
            evidence_summary=dict(proposal.get("evidence_summary", {})),
            intent_summary=dict(proposal.get("intent_summary", {})),
            symptom_names=tuple(str(item) for item in proposal.get("symptom_names", [])),
        )
        store = getattr(self, "preprocess_experience_store", None)
        if store is None:
            store = ExperienceStore(
                Path.cwd() / "results" / "audit" / "preprocess_experience.json"
            )
            self.preprocess_experience_store = store
        store.accept(record)
        return experience_id

    def _revoke_preprocess_experience(self, experience_id):
        if not experience_id:
            return False
        store = getattr(self, "preprocess_experience_store", None)
        return bool(store is not None and store.revoke(experience_id))

    def _finalize_preprocess_apply_success(self, result=None):
        service = getattr(self, "_preprocess_transaction", None)
        if service is not None:
            return service.finalize_success(result)
        return True

    def _rollback_preprocess_apply_failure(self):
        service = getattr(self, "_preprocess_transaction", None)
        if service is not None:
            service.rollback_failure()

    def _undo_last_preprocess_apply(self):
        service = getattr(self, "_preprocess_transaction", None)
        if service is None:
            return False
        started = service.undo()
        if started:
            if hasattr(self, "log"):
                self.log(tr("LOG_AI_TUNING_APPLY_AND_RERUN"))
        return started

    def _apply_best_config(self, best_config):
        if not isinstance(best_config, dict):
            return
        for row in range(self._config_form.rowCount()):
            item = self._config_form.itemAt(row, QFormLayout.FieldRole)
            if item is None:
                item = self._config_form.itemAt(row, QFormLayout.SpanningRole)
            widget = item.widget() if item is not None else None
            if widget is None:
                continue
            set_values = getattr(widget, "set_config_values", None)
            if callable(set_values):
                config_keys = getattr(widget, "config_keys", None)
                if callable(config_keys) and not set(config_keys()).intersection(best_config):
                    continue
                set_values(best_config)
                continue
            key = widget.property("config_key")
            if not key or key not in best_config:
                continue
            value = best_config[key]
            if isinstance(widget, QComboBox):
                idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif isinstance(widget, QDoubleSpinBox):
                try:
                    widget.setValue(float(value))
                except Exception:
                    self._logger().warning("Failed to apply floating-point config value.", exc_info=True)
            elif isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(value))
                except Exception:
                    self._logger().warning("Failed to apply integer config value.", exc_info=True)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))

    def _ai_tuning_chain_snapshot(self, tuning_context: dict | None = None) -> str:
        return ai_tuning_chain_summary(
            tuning_context,
            current_origin=self._current_result_origin(),
            language=get_language(),
            benchmark_delta_text_fn=self._benchmark_delta_text,
        )
