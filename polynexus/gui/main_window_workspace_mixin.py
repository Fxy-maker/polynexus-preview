from __future__ import annotations

import os

from .context_suggestion_service import (
    context_suggestion_spec,
    workflow_task_context_spec,
    workflow_task_tech_label as build_workflow_task_tech_label,
)
from .i18n import tr
from .main_window_history_mixin import resolve_joint_history_project_label
from .theme import TECHNIQUE_LABELS
from .window_text_helpers import import_mode_text as _import_mode_text
from .workspace_mode import WorkspaceMode, normalize_workspace_mode
from .workspace_context import WorkspaceContext, WorkspaceResultStatus


class MainWindowWorkspaceMixin:
    def _workspace_context_snapshot(self, *, result_status=None, run_id=None):
        resolved_run_id = (
            str(run_id)
            if run_id is not None
            else str(getattr(self, "_last_persisted_run_id", "") or "")
        )
        if result_status is None:
            result_status = (
                WorkspaceResultStatus.COMPLETE
                if resolved_run_id
                else WorkspaceResultStatus.EMPTY
            )
        if not isinstance(result_status, WorkspaceResultStatus):
            result_status = WorkspaceResultStatus(str(result_status).strip().lower())
        return WorkspaceContext(
            technique=str(getattr(self, "_current_technique", "") or ""),
            submodule=str(getattr(self, "_current_submodule_id", "") or ""),
            source_path=str(getattr(self, "_current_filepath", "") or ""),
            input_mode=str(getattr(self, "_current_input_mode", "") or ""),
            output_dir=str(getattr(self, "_output_dir", "") or ""),
            run_id=resolved_run_id,
            run_root=str(getattr(self, "_output_dir", "") or ""),
            result_status=result_status,
            result_origin=str(self._current_result_origin() or "")
            if callable(getattr(self, "_current_result_origin", None))
            else "",
        )

    def _record_result_context(self, technique=None, *, status="complete", run_id=None):
        if not hasattr(self, "_result_contexts"):
            self._result_contexts = {}
        context_status = status
        if not isinstance(context_status, WorkspaceResultStatus):
            context_status = WorkspaceResultStatus(str(context_status).strip().lower())
        context = self._workspace_context_snapshot(
            result_status=context_status,
            run_id=run_id,
        )
        key = str(technique or context.technique or "").strip().lower()
        if key and not (
            context_status is WorkspaceResultStatus.COMPLETE and not context.run_id
        ):
            self._result_contexts[key] = context
        self._workspace_context = context
        return context

    def _result_context_is_current(self, technique=None) -> bool:
        if not hasattr(self, "_result_contexts"):
            return False
        current = getattr(self, "_workspace_context", WorkspaceContext.empty())
        key = str(technique or current.technique or "").strip().lower()
        stored = self._result_contexts.get(key)
        return bool(stored and current.result_matches(stored))

    def _workspace_context_summary_text(self, context) -> str:
        source = os.path.basename(context.source_path.rstrip("/\\")) if context.source_path else tr("WORKFLOW_NO_DATA")
        run_id = context.run_id or tr("WORKSPACE_RUN_NOT_PERSISTED")
        return tr(
            "WORKSPACE_CONTEXT_SUMMARY",
            context.technique or "-",
            context.submodule or tr("WORKSPACE_SUBMODULE_NONE"),
            source,
            run_id,
        )

    def _invalidate_context_bound_views(self):
        self._last_persisted_run_id = ""
        self._current_result_confirmed_flag = False
        self._current_figure_path = ""
        preview = getattr(self, "_figure_preview", None)
        if preview is not None:
            clear = getattr(preview, "clear", None)
            if callable(clear):
                clear()
            preview.setVisible(False)
        self._workspace_context = self._workspace_context_snapshot(
            result_status=WorkspaceResultStatus.EMPTY,
            run_id="",
        )

    def _update_workspace_context(self):
        if not hasattr(self, "_workspace_title"):
            return

        self._workspace_context = self._workspace_context_snapshot()

        tech = self._current_technique or "saxs"
        mode_getter = getattr(self, "_workspace_mode_value", None)
        if callable(mode_getter):
            workspace_mode = mode_getter()
        else:
            try:
                workspace_mode = normalize_workspace_mode(
                    getattr(self, "_workspace_mode", "") or tech
                )
            except ValueError:
                workspace_mode = WorkspaceMode.ANALYSIS
        is_samples = workspace_mode is WorkspaceMode.SAMPLES
        is_joint = workspace_mode is WorkspaceMode.JOINT
        label = TECHNIQUE_LABELS.get(tech, tech.upper())
        title_key = "WORKSPACE_TITLE_ANALYSIS"

        if is_samples:
            label = tr("WORKFLOW_TECH_SAMPLES")
            title_key = "WORKSPACE_TITLE_SAMPLES"

        if is_joint:
            label = tr("WORKFLOW_TECH_JOINT")
            title_key = "WORKSPACE_TITLE_JOINT"

        submodule = getattr(self, "_current_submodule_id", "")

        if is_joint:
            count = 0
            hub = getattr(self, "_joint_hub", None)
            if hub is not None:
                count = len(hub.selected_rows())
            filename = tr("WORKFLOW_SELECTED_BATCHES", count) if count else tr("WORKFLOW_EXISTING_RUNS")
        else:
            filename = (
                os.path.basename(self._current_filepath.rstrip("/\\"))
                if self._current_filepath
                else tr("WORKFLOW_NO_DATA")
            )
            mode_text = self._workspace_input_mode_text()
            if mode_text and self._current_filepath:
                filename = f"{mode_text} | {filename}"

        if title_key == "WORKSPACE_TITLE_ANALYSIS":
            self._workspace_title.setText(tr(title_key, label))
        else:
            self._workspace_title.setText(tr(title_key))

        detail = (
            self._history_submodule_text(submodule) or submodule.replace(".", " / ")
            if submodule
            else tr("WORKSPACE_SUBTITLE_DEFAULT")
        )
        if is_joint:
            detail = tr("WORKSPACE_DETAIL_JOINT")

        self._workspace_subtitle.setText(f"{detail}  |  {filename}")

        context_summary = getattr(self, "_workspace_context_summary_label", None)
        if context_summary is None:
            legacy_context_summary = getattr(self, "_workspace_context_summary", None)
            if not callable(legacy_context_summary):
                context_summary = legacy_context_summary
        if context_summary is not None:
            context_summary.setText(self._workspace_context_summary_text(self._workspace_context))

        if hasattr(self, "_workflow_metric_tech"):
            self._workflow_metric_tech.setText(label)

        if hasattr(self, "_status_tech_label"):
            self._status_tech_label.setText(f" {label} ")

        if hasattr(self, "_workflow_metric_data"):
            self._workflow_metric_data.setText(filename)

        if hasattr(self, "_workflow_metric_state"):
            current_state = self._workflow_metric_state.text()
            if current_state in (
                "Ready",
                "就绪",
                tr("WORKFLOW_READY"),
                tr("WORKFLOW_SEQUENCE_READY"),
                tr("WORKFLOW_DIRECTORY_READY"),
                tr("WORKFLOW_BATCH_READY"),
            ):
                self._workflow_metric_state.setText(self._idle_workflow_state_text())

        self._update_workflow_task_card()
        self._update_context_suggestions()
        self._update_work_memory_panel()
        self._update_results_compare_panel()

    def _set_workflow_task_default(self):
        if not hasattr(self, "_workflow_task_box"):
            return
        self._workflow_task_label.setText(tr("WORKFLOW_TASK_LABEL"))
        self._workflow_task_title.setText(tr("WORKFLOW_TASK_DEFAULT_TITLE"))
        self._workflow_task_detail.setText(tr("WORKFLOW_TASK_DEFAULT_DETAIL"))

    def _workspace_input_mode_text(self):
        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        if mode not in {"sequence", "directory"}:
            return ""
        return _import_mode_text(mode)

    def _workflow_task_tech_label(self, tech: str) -> str:
        labels = dict(TECHNIQUE_LABELS)
        labels.update({
            "samples": tr("WORKFLOW_TECH_SAMPLES"),
            "joint": tr("WORKFLOW_TECH_JOINT"),
        })
        return build_workflow_task_tech_label(
            tech,
            technique_labels=labels,
            no_tech_text=tr("WORKFLOW_TASK_NO_TECH"),
        )

    def _workflow_task_context(self):
        tech = str(getattr(self, "_current_technique", "") or "").strip().lower()
        submodule = str(getattr(self, "_current_submodule_id", "") or "").strip()
        input_mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        filepath = str(getattr(self, "_current_filepath", "") or "").strip()
        running = bool(self._btn_run.property("busy")) if hasattr(self, "_btn_run") else False
        is_dir = bool(filepath and os.path.isdir(filepath))
        source_name = os.path.basename(filepath.rstrip("/\\")) if filepath else ""
        if tech == "joint":
            source_name = resolve_joint_history_project_label(
                "",
                getattr(self, "_joint_report", None),
            )
        mode_text = _import_mode_text(input_mode) if input_mode in {"sequence", "directory"} else ""
        is_native_directory_context = self._is_native_directory_run_context()
        spec = workflow_task_context_spec(
            tech=tech,
            input_mode=input_mode,
            filepath=filepath,
            is_dir=is_dir,
            is_native_directory_context=is_native_directory_context,
            ai_tuning_active=bool(getattr(self, "_ai_tuning_active", False)),
            running=running,
            source_name=source_name,
            mode_text=mode_text,
            no_data_text=tr("WORKFLOW_NO_DATA"),
        )

        if submodule:
            submodule_text = self._history_submodule_text(submodule) or submodule.replace(".", " / ")
        else:
            submodule_text = tr("WORKFLOW_SUBMODULE_NONE")

        return {
            "title": tr(spec["title_key"]),
            "detail": tr(spec["detail_key"]),
            "status": tr(spec["status_key"]),
            "technique": self._workflow_task_tech_label(tech),
            "submodule": submodule_text,
            "source": spec["source"],
        }

    def _update_workflow_task_card(self):
        if not hasattr(self, "_workflow_task_box"):
            return

        task = self._workflow_task_context()
        self._workflow_task_label.setText(tr("WORKFLOW_TASK_LABEL"))
        self._workflow_task_title.setText(task["title"])
        self._workflow_task_detail.setText(
            tr(
                "WORKFLOW_TASK_DETAIL_TEMPLATE",
                task["status"],
                task["technique"],
                task["submodule"],
                task["source"],
                task["detail"],
            )
        )

    def _context_suggestion_payload(self, slot: str):
        tech = str(getattr(self, "_current_technique", "") or "").strip().lower()
        filepath = str(getattr(self, "_current_filepath", "") or "").strip()
        has_file = bool(filepath)
        has_results = bool(self._results or self._batch_results or self._joint_report)
        has_config = bool(getattr(self, "_config_form", None) is not None and self._config_form.rowCount() > 0)
        spec = context_suggestion_spec(
            slot,
            has_file=has_file,
            source_name=os.path.basename(filepath.rstrip("/\\")) or filepath,
            has_results=has_results,
            has_config=has_config,
            technique=tech,
            current_origin=self._current_result_origin(),
            has_recent_calibration=bool(self._load_recent_calibration()) if tech in {"saxs", "waxs"} and has_config else False,
            calibration_scope_label=self._current_calibration_scope_label() or tr("WORKFLOW_SUBMODULE_NONE"),
        )
        return self._materialize_context_suggestion_spec(spec)

    def _materialize_context_suggestion_spec(self, spec):
        if not isinstance(spec, dict):
            return None
        return {
            "title": tr(str(spec.get("title_key") or "")),
            "detail": tr(str(spec.get("detail_key") or ""), *tuple(spec.get("detail_args") or ())),
            "items": [
                {
                    "text": tr(str(item.get("text_key") or "")),
                    "action_key": str(item.get("action_key") or ""),
                    "callback": self._context_suggestion_callback(
                        str(item.get("callback_key") or item.get("action_key") or "")
                    ),
                }
                for item in spec.get("items") or []
                if isinstance(item, dict)
            ],
        }

    def _context_suggestion_callback(self, callback_key: str):
        mapping = {
            "browse_file": self._browse_file,
            "browse_folder": self._browse_folder,
            "open_config": lambda: self._jump_to_tab(1),
            "open_results": lambda: self._jump_to_tab(2),
            "open_history": lambda: self._jump_to_tab(4),
            "back_to_data": lambda: self._jump_to_tab(0),
            "review_ai_result": lambda: self._jump_to_tab(2),
            "run_controlled_optimization": self.on_ai_tune_clicked,
            "apply_recent_calibration": self._on_apply_recent_calibration,
            "save_recent_calibration": self._on_save_recent_calibration,
        }
        return mapping.get(callback_key)

    def _update_context_suggestion_panel(self, slot: str, payload):
        panel = self._context_suggestion_panels.get(slot)
        if panel is None:
            return

        panel["widget"].setVisible(bool(payload))
        if not payload:
            return

        panel["title"].setText(payload["title"])
        panel["detail"].setText(payload["detail"])

        items = list(payload.get("items") or [])
        for idx, button in enumerate(panel["buttons"]):
            if idx < len(items):
                item = items[idx]
                action_key = str(item.get("action_key") or f"{slot}_{idx}").strip()
                button.setText(str(item.get("text") or ""))
                button.setVisible(True)
                button.setEnabled(True)
                button.setProperty("context_action_key", action_key)
                self._context_suggestion_action_map[action_key] = item.get("callback")
            else:
                button.setVisible(False)
                button.setProperty("context_action_key", "")

    def _update_context_suggestions(self):
        self._context_suggestion_action_map = {}
        self._update_context_suggestion_panel("data", self._context_suggestion_payload("data"))
        self._update_context_suggestion_panel("config", self._context_suggestion_payload("config"))
