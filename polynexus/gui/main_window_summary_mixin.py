from __future__ import annotations

import os
from typing import Any

from .analysis_history_service import (
    gui_coerce_summary_float,
    gui_display_text,
    gui_display_text_value,
    gui_format_score_value,
    flatten_params,
    joint_ai_context as build_joint_ai_context,
    joint_ai_reminder_parts,
    joint_compare_hint_parts,
    measured_result_metric_parts,
    ordered_results_columns as build_ordered_results_columns,
    quality_flag_summary_text,
    results_has_critical_risk as build_results_has_critical_risk,
)
from .i18n import get_language, tr
from .results_review_service import (
    results_next_step_text as build_results_next_step_text,
    results_risk_summary_text as build_results_risk_summary_text,
    result_review_ir_support_block_text as build_result_review_ir_support_block_text,
)
from .work_memory_service import build_work_memory_payload, work_memory_summary_text
from .workspace_context_service import workspace_context_summary_text
from .window_text_helpers import ir_conclusion_state_display as _ir_conclusion_state_display


class MainWindowSummaryMixin:
    def _series_scope_summary_text(self, frame_count):
        try:
            frame_count = int(frame_count)
        except Exception:
            frame_count = 0
        if frame_count <= 0:
            return ""
        if frame_count == 1:
            return tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAME")
        return tr("RESULTS_SUMMARY_SCOPE_SINGLE_SAMPLE_FRAMES", frame_count)

    def _frame_results_summary_text(self, frame_count):
        mode = str(getattr(self, "_current_input_mode", "") or "").strip().lower()
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        scope_text = self._series_scope_summary_text(frame_count)
        if mode == "sequence":
            return tr("RESULTS_SUMMARY_SEQUENCE", scope_text, source_name)
        return tr("RESULTS_SUMMARY_DIRECTORY", scope_text, source_name)

    def _batch_results_summary_text(self, file_count):
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        return tr("RESULTS_SUMMARY_BATCH", file_count, source_name)

    def _single_results_summary_text(self, params):
        metric_count = 0
        if isinstance(params, dict):
            metric_count = len(flatten_params(params))
        source_name = os.path.basename(str(self._current_filepath or "").rstrip("/\\")) or str(self._current_filepath or "")
        if self._current_result_origin() == "controlled_optimization_rerun":
            if source_name:
                return tr("RESULTS_SUMMARY_SINGLE_AI_TUNED", metric_count, source_name)
            return tr("RESULTS_SUMMARY_SINGLE_AI_TUNED_NO_SOURCE", metric_count)
        if source_name:
            return tr("RESULTS_SUMMARY_SINGLE", metric_count, source_name)
        return tr("RESULTS_SUMMARY_SINGLE_NO_SOURCE", metric_count)

    def _results_risk_summary_text(self, params, result=None):
        params = params if isinstance(params, dict) else {}
        analysis_evidence = self._current_analysis_evidence()
        return build_results_risk_summary_text(
            params,
            result,
            technique=str(getattr(self, "_current_technique", "") or "").strip().lower(),
            analysis_evidence=analysis_evidence,
            language=get_language(),
        )

    def _quality_flag_summary_text(self, result) -> str:
        return quality_flag_summary_text(result, language=get_language())

    def _display_text_value(self, value):
        return gui_display_text_value(value, empty_text=tr("AI_TUNING_EMPTY_VALUE"))

    def _display_text(self, value):
        return gui_display_text(value, empty_text=tr("AI_TUNING_EMPTY_VALUE"))

    def _ir_label_text(self, value: str) -> str:
        key = str(value or "").strip().lower()
        mapping = {
            "peak_assignment": tr("IR_BASIS_PEAK_ASSIGNMENT"),
            "peak_detection": tr("IR_BASIS_PEAK_DETECTION"),
        }
        return mapping.get(key, tr("IR_BASIS_UNKNOWN"))

    def _ir_bool_text(self, value: Any) -> str:
        if value is True:
            return tr("COMMON_YES")
        if value is False:
            return tr("COMMON_NO")
        return tr("AI_TUNING_EMPTY_VALUE")

    def _ir_conclusion_state_text(self, value: Any) -> str:
        return _ir_conclusion_state_display(value)

    def _ir_support_block_text(self, analysis_evidence: dict[str, Any] | None = None) -> str:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        return build_result_review_ir_support_block_text(
            analysis_evidence,
            include_reference_summary=True,
        )

    def _coerce_summary_float(self, value):
        return gui_coerce_summary_float(value)

    def _results_has_critical_risk(self, params, result=None):
        analysis_evidence = self._current_analysis_evidence()
        technique = str(getattr(self, "_current_technique", "") or "").strip().lower()
        return build_results_has_critical_risk(
            params,
            technique=technique,
            result=result,
            analysis_evidence=analysis_evidence,
            condition_axis_risk=self._has_condition_axis_risk(params, analysis_evidence),
            fallback_conflict_risk=self._has_fallback_conflict_risk(analysis_evidence),
            waxs_structure=self._waxs_structure_evidence(analysis_evidence) if technique == "waxs" else {},
            waxs_support=self._waxs_support_snapshot(analysis_evidence) if technique == "waxs" else {},
        )

    def _results_next_step_text(self, params, result=None):
        params = params if isinstance(params, dict) else {}
        analysis_evidence = self._current_analysis_evidence()
        return build_results_next_step_text(
            params,
            result,
            mode=str(getattr(self, "_current_input_mode", "") or "").strip().lower(),
            technique=str(getattr(self, "_current_technique", "") or "").strip().lower(),
            analysis_evidence=analysis_evidence,
            language=get_language(),
        )

    def _ordered_results_columns(self, columns):
        return build_ordered_results_columns(columns)

    def _work_memory_payload(self):
        return build_work_memory_payload(self)

    def _work_memory_summary(self) -> str:
        payload = self._work_memory_payload()
        slices = payload.get("slices") if isinstance(payload.get("slices"), list) else []
        extra_lines = []
        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        if isinstance(tuning_context, dict) and tuning_context:
            benchmark_text = str(tuning_context.get("benchmark_text") or "").strip()
            if benchmark_text:
                extra_lines.append(tr("RESULTS_REVIEW_BENCHMARK", benchmark_text))
            chain_text = self._ai_tuning_chain_snapshot(tuning_context)
            if chain_text:
                extra_lines.append(tr("RESULTS_REVIEW_CHAIN", chain_text))
        joint_context = self._joint_ai_context()
        if isinstance(joint_context, dict) and joint_context:
            joint_summary = str(joint_context.get("summary") or "").strip()
            joint_reminder = self._joint_ai_reminder_text(joint_context)
            joint_compare_hint = self._joint_compare_hint_text(joint_context)
            joint_parts = [part for part in [joint_summary, joint_reminder, joint_compare_hint] if part]
            if joint_parts:
                extra_lines.append(tr("WORK_MEMORY_JOINT") + ": " + " | ".join(joint_parts))
        return work_memory_summary_text(slices, extra_lines=extra_lines)

    def _update_work_memory_panel(self):
        panel = getattr(self, "_work_memory_panels", None)
        if not panel or "widget" not in panel:
            return

        payload = self._work_memory_payload()
        panel["widget"].setVisible(True)
        panel["title"].setText(payload["title"])
        panel["detail"].setText(payload["detail"])

        self._work_memory_action_map = {}
        slices = list(payload.get("slices") or [])
        for idx, button in enumerate(panel["buttons"]):
            if idx < len(slices):
                item = slices[idx]
                action_key = str(item.get("action_key") or f"memory_{idx}").strip()
                button.setText(f"{item.get('label', '')}")
                button.setToolTip(str(item.get("detail") or item.get("label") or "").strip())
                button.setVisible(True)
                button.setEnabled(True)
                button.setProperty("work_memory_action_key", action_key)
                self._work_memory_action_map[action_key] = item.get("callback")
            else:
                button.setVisible(False)
                button.setToolTip("")
                button.setProperty("work_memory_action_key", "")

    def _workspace_context_summary(self):
        current_result = self._current_results_record()
        current_note = ""
        if hasattr(self, "_results_summary_risk_label"):
            current_note = str(self._results_summary_risk_label.text() or "").strip()
        if not current_note and hasattr(self, "_results_summary_label"):
            current_note = str(self._results_summary_label.text() or "").strip()

        return workspace_context_summary_text(
            current_result,
            confirm_state_text=self._results_confirm_state_text(),
            origin_label=self._current_result_origin_label(),
            current_note=current_note,
            joint_report=getattr(self, "_joint_report", None),
            joint_context=self._joint_ai_context(),
            joint_label=tr("WORK_MEMORY_JOINT"),
            joint_count_text_fn=(
                (lambda rows, validations: f"{rows} 行，{validations} 项校验")
                if get_language() == "zh"
                else (lambda rows, validations: f"{rows} rows, {validations} validations")
            ),
            work_memory=self._work_memory_payload(),
            empty_text=tr("WORK_MEMORY_EMPTY_DETAIL"),
        )

    def _joint_ai_context(self):
        report = self._joint_report if isinstance(self._joint_report, dict) else {}
        tuning_context = getattr(self, "_last_ai_tuning_context", {})
        history_context = self._current_result_history_context()
        return build_joint_ai_context(
            report,
            tuning_context=tuning_context,
            history_context=history_context,
            no_issue_summary=tr("JOINT_DIAG_NONE"),
            joint_scope_label=tr("WORKFLOW_TECH_JOINT"),
        )

    def _joint_issue_family_label(self, family) -> str:
        key = str(family or "").strip().lower()
        mapping = {
            "phi_c inconsistency": tr("JOINT_ISSUE_FAMILY_PHI_C"),
            "tm bidirectional gap": tr("JOINT_ISSUE_FAMILY_TM_GAP"),
            "l consistency unstable": tr("JOINT_ISSUE_FAMILY_L_UNSTABLE"),
            "cross-tech issue": tr("JOINT_ISSUE_FAMILY_CROSS_TECH"),
        }
        return mapping.get(key, str(family or "").strip())

    def _joint_ai_reminder_text(self, joint_context=None) -> str:
        joint_context = joint_context if isinstance(joint_context, dict) else self._joint_ai_context()
        separator = "、" if get_language() == "zh" else ", "
        parts = joint_ai_reminder_parts(
            joint_context,
            family_label_fn=self._joint_issue_family_label,
            separator=separator,
        )
        if parts is None:
            return ""
        return tr(parts.translation_key, *parts.args)

    def _joint_compare_hint_text(self, joint_context=None) -> str:
        joint_context = joint_context if isinstance(joint_context, dict) else self._joint_ai_context()
        separator = "、" if get_language() == "zh" else ", "
        parts = joint_compare_hint_parts(
            joint_context,
            family_label_fn=self._joint_issue_family_label,
            separator=separator,
        )
        if parts is None:
            return ""
        return tr(parts.translation_key, *parts.args)
