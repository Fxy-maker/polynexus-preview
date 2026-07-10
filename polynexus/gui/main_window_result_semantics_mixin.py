from __future__ import annotations

from typing import Any

from .analysis_history_service import (
    batch_fallback_summary_parts,
    gui_format_score_value,
    has_condition_axis_risk as build_has_condition_axis_risk,
    has_fallback_conflict_risk as build_has_fallback_conflict_risk,
    history_record_analysis_evidence,
    measured_result_metric_parts,
    result_source_summary_text as build_result_source_summary_text,
    saxs_lc_status_summary_parts,
    saxs_lc_status_text as build_saxs_lc_status_text,
    saxs_strain_evidence_snapshot as build_saxs_strain_evidence_snapshot,
    saxs_strain_next_step_text as build_saxs_strain_next_step_text,
    saxs_strain_risk_summary_text as build_saxs_strain_risk_summary_text,
    saxs_strain_summary_text as build_saxs_strain_summary_text,
)
from .i18n import get_language, tr
from .results_review_service import (
    result_review_constraint_summary_text as build_result_review_constraint_summary_text,
    result_review_dsc_support_block_text as build_result_review_dsc_support_block_text,
    result_review_stability_summary_text as build_result_review_stability_summary_text,
)


class MainWindowResultSemanticsMixin:
    def _waxs_support_snapshot(self, analysis_evidence=None) -> dict[str, float | None]:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict):
            analysis_evidence = {}
        snapshot = {}
        for key in (
            "peak_support_score",
            "background_stability_score",
            "phase_support_score",
            "size_support_score",
            "D_trend_support_score",
            "waxs_support_score",
        ):
            try:
                value = float(analysis_evidence.get(key))
            except (TypeError, ValueError):
                value = None
            snapshot[key] = value
        return snapshot

    def _waxs_structure_evidence(self, analysis_evidence=None) -> dict:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict):
            return {}
        structure = analysis_evidence.get("structure_evidence")
        return structure if isinstance(structure, dict) else {}

    def _waxs_temperature_trend_evidence(self, analysis_evidence=None) -> dict:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict):
            return {}
        feature = analysis_evidence.get("feature_evidence", {})
        if not isinstance(feature, dict):
            return {}
        trend = feature.get("scherrer_trend_evidence")
        return trend if isinstance(trend, dict) else {}

    def _waxs_temperature_trend_text(self, analysis_evidence=None) -> str:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        if not isinstance(analysis_evidence, dict) or not analysis_evidence:
            return ""
        feature = analysis_evidence.get("feature_evidence", {})
        if not isinstance(feature, dict):
            feature = {}
        seq = feature.get("sequence_evidence", {})
        if not isinstance(seq, dict):
            seq = {}
        family = feature.get("peak_family_evidence", {})
        if not isinstance(family, dict):
            family = {}
        trend = feature.get("scherrer_trend_evidence", {})
        if not isinstance(trend, dict):
            trend = {}
        xc_trend = feature.get("crystallinity_trend_evidence", feature.get("trend_evidence", {}))
        if not isinstance(xc_trend, dict):
            xc_trend = {}
        transition = feature.get("transition_evidence", {})
        if not isinstance(transition, dict):
            transition = {}
        parts = []
        axis = seq.get("temperature_axis_confidence")
        if axis is not None:
            parts.append(f"axis={self._format_score_value(axis)}")
        family_score = family.get("peak_family_continuity_score")
        if family_score is not None:
            parts.append(f"family={self._format_score_value(family_score)}")
        xc_score = xc_trend.get("Xc_trend_support_score")
        if xc_score is not None:
            parts.append(f"Xc={self._format_score_value(xc_score)}")
        score = trend.get("D_trend_support_score")
        if score is not None:
            parts.append(f"score={self._format_score_value(score)}")
            parts.append(f"D={self._format_score_value(score)}")
        transition_score = transition.get("transition_support_score")
        if transition_score is not None:
            parts.append(f"transition={self._format_score_value(transition_score)}")
        mode = str(trend.get("D_trend_monotonicity", "") or "").strip()
        if mode:
            parts.append(f"mode={mode}")
        support = trend.get("D_support_peak_count")
        if support is not None:
            parts.append(f"support={self._display_text(support)}")
        candidate_count = transition.get("transition_candidate_count")
        if candidate_count is not None:
            parts.append(f"candidates={self._display_text(candidate_count)}")
        if trend.get("instrument_broadening_present") is not None:
            parts.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
        return ", ".join(parts)

    def _waxs_result_semantic_lines(self, current_metrics=None, analysis_evidence=None) -> list[str]:
        current_metrics = current_metrics if isinstance(current_metrics, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        support = self._waxs_support_snapshot(analysis_evidence)
        structure = self._waxs_structure_evidence(analysis_evidence)
        trend = self._waxs_temperature_trend_evidence(analysis_evidence)

        peak_count = current_metrics.get("n_peaks", "")
        xc_pct = current_metrics.get("Xc_pct", "")
        size_nm = current_metrics.get("D_Scherrer_nm", "")
        peak_score = support.get("peak_support_score")
        phase_score = support.get("phase_support_score")
        size_score = support.get("size_support_score")
        overall_score = support.get("waxs_support_score")

        lines = []
        peak_text = f"n_peaks={peak_count}" if peak_count != "" else tr("AI_TUNING_EMPTY_VALUE")
        if peak_score is not None:
            peak_text += f", score={self._format_score_value(peak_score)}"
        lines.append(tr("WAXS_REVIEW_PEAK_SUPPORT", peak_text))

        crystallinity_text = f"Xc_pct={xc_pct}" if xc_pct != "" else tr("AI_TUNING_EMPTY_VALUE")
        if phase_score is not None:
            crystallinity_text += f", score={self._format_score_value(phase_score)}"
        lines.append(tr("WAXS_REVIEW_CRYSTALLINITY_ESTIMATE", crystallinity_text))

        size_text = f"D_Scherrer_nm={size_nm}" if size_nm != "" else tr("AI_TUNING_EMPTY_VALUE")
        if size_score is not None:
            size_text += f", score={self._format_score_value(size_score)}"
        lines.append(tr("WAXS_REVIEW_SIZE_ESTIMATE", size_text))

        if trend:
            trend_bits = []
            for label, value in (
                ("score", trend.get("D_trend_support_score")),
                ("mode", trend.get("D_trend_monotonicity")),
                ("support", trend.get("D_support_peak_count")),
            ):
                text = self._display_text(value)
                if text != tr("AI_TUNING_EMPTY_VALUE"):
                    trend_bits.append(f"{label}={text}")
            if trend.get("instrument_broadening_present") is not None:
                trend_bits.append(f"instrument_broadening={bool(trend.get('instrument_broadening_present'))}")
            if trend_bits:
                lines.append(tr("WAXS_REVIEW_D_TREND", ", ".join(trend_bits)))
        sequence_text = self._waxs_temperature_trend_text(analysis_evidence)
        if sequence_text:
            lines.append(tr("WAXS_REVIEW_TEMPERATURE_SEQUENCE", sequence_text))

        if structure.get("paper_ready_candidate"):
            lines.append(tr("WAXS_REVIEW_PAPER_READY"))
        else:
            if structure.get("physical_support_pass") is False or (overall_score is not None and overall_score < 0.72):
                lines.append(tr("WAXS_REVIEW_PHYSICAL_SUPPORT_LIMITED"))
            if structure.get("fit_only_pass") and not structure.get("physical_support_pass"):
                lines.append(tr("WAXS_REVIEW_FIGURE_USABLE_PENDING"))
            if peak_score is not None and peak_score < 0.75:
                lines.append(tr("WAXS_REVIEW_PEAK_FAMILY_NEEDS_REVIEW"))

        return [str(item).strip() for item in lines if str(item).strip()]

    def _format_score_value(self, value, signed=False):
        return gui_format_score_value(value, empty_text=tr("AI_TUNING_EMPTY_VALUE"), signed=signed)

    def _stability_summary_text(self, analysis_evidence):
        return build_result_review_stability_summary_text(analysis_evidence)

    def _constraint_summary_text(self, analysis_evidence):
        return build_result_review_constraint_summary_text(analysis_evidence)

    def _result_source_summary_text(self, record: dict[str, Any] | None = None) -> str:
        record = record if isinstance(record, dict) else self._current_results_record()
        if not isinstance(record, dict) or not record:
            return tr("AI_TUNING_EMPTY_VALUE")

        evidence = history_record_analysis_evidence(record)
        if not evidence and str(record.get("id") or "").strip() == "current":
            evidence = self._current_analysis_evidence()

        current_metrics = self._history_result_metrics(record)
        origin = self._history_result_origin_label(record) or self._current_result_origin_label()
        technique = str(record.get("technique") or self._current_technique or "").strip().lower()
        empty_text = tr("AI_TUNING_EMPTY_VALUE")
        dsc_support = ""
        if technique == "dsc":
            dsc_support = build_result_review_dsc_support_block_text(
                evidence,
                include_measurement=False,
            )
        return build_result_source_summary_text(
            record,
            current_metrics=current_metrics,
            evidence=evidence,
            origin_label=origin,
            technique=technique,
            trend_evidence=self._waxs_temperature_trend_evidence(evidence) if technique == "waxs" else {},
            empty_text=empty_text,
            format_score_value_fn=self._format_score_value,
            display_text_fn=self._display_text,
            constraint_text=self._constraint_summary_text(evidence),
            dsc_support_text=dsc_support,
            ir_support_text=self._ir_support_block_text(evidence) if technique == "ir" else "",
        )

    def _evidence_symptom_names(self, analysis_evidence) -> set[str]:
        symptoms = analysis_evidence.get("symptoms", []) if isinstance(analysis_evidence, dict) else []
        names: set[str] = set()
        if not isinstance(symptoms, list):
            return names
        for item in symptoms:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            if name:
                names.add(name)
        return names

    def _batch_fallback_summary_text(self, analysis_evidence):
        parts = batch_fallback_summary_parts(
            analysis_evidence,
            symptom_names=self._evidence_symptom_names(analysis_evidence),
        )
        return " | ".join(tr(part.translation_key, *part.args) for part in parts)

    def _saxs_lc_status_summary_text(self, params, analysis_evidence=None) -> str:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        parts = saxs_lc_status_summary_parts(params, analysis_evidence)
        if parts is None:
            return ""
        status, diagnostic_rows_int, within_window_rows_int, reason = parts

        return tr(
            "RESULTS_SUMMARY_RISK_SAXS_LC_STATUS",
            self._saxs_lc_status_text(status) or tr("AI_TUNING_EMPTY_VALUE"),
            diagnostic_rows_int,
            within_window_rows_int,
            reason or tr("AI_TUNING_EMPTY_VALUE"),
        )

    def _saxs_lc_status_text(self, status: Any) -> str:
        return build_saxs_lc_status_text(status, language=get_language())

    def _saxs_calibration_method_text(self, method: Any) -> str:
        text = str(method or "").strip().lower()
        if not text:
            return ""
        zh = get_language() == "zh"
        mapping = {
            "raw": "原始" if zh else "raw",
            "calibrated": "已校准" if zh else "calibrated",
            "qstar_calibrated": "已校准" if zh else "calibrated",
        }
        return mapping.get(text, text.replace("_", "-"))

    def _saxs_strain_evidence_snapshot(self, params=None, analysis_evidence=None) -> dict[str, Any]:
        params = params if isinstance(params, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        return build_saxs_strain_evidence_snapshot(
            params,
            analysis_evidence,
            symptom_names=self._evidence_symptom_names(analysis_evidence),
        )

    def _saxs_strain_summary_text(self, params=None, analysis_evidence=None) -> str:
        params = params if isinstance(params, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        return build_saxs_strain_summary_text(
            params,
            analysis_evidence,
            symptom_names=self._evidence_symptom_names(analysis_evidence),
            language=get_language(),
        )

    def _saxs_strain_risk_summary_text(self, params=None, analysis_evidence=None) -> str:
        params = params if isinstance(params, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        return build_saxs_strain_risk_summary_text(
            params,
            analysis_evidence,
            symptom_names=self._evidence_symptom_names(analysis_evidence),
            language=get_language(),
        )

    def _saxs_strain_next_step_text(self, params=None, analysis_evidence=None) -> str:
        params = params if isinstance(params, dict) else {}
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else self._current_analysis_evidence()
        return build_saxs_strain_next_step_text(
            params,
            analysis_evidence,
            symptom_names=self._evidence_symptom_names(analysis_evidence),
            language=get_language(),
        )

    def _measured_result_summary_text(self, record: dict[str, Any] | None = None) -> str:
        record = record if isinstance(record, dict) else self._current_results_record()
        if not isinstance(record, dict) or not record:
            return ""
        summary = record.get("results_summary") if isinstance(record.get("results_summary"), dict) else {}
        if not isinstance(summary, dict):
            summary = {}

        current_metrics = self._history_result_metrics(record)
        technique = str(self._current_technique or "").strip().lower()
        params = record.get("parameters") if isinstance(record.get("parameters"), dict) else {}
        strain_snapshot = (
            self._saxs_strain_evidence_snapshot(
                params,
                record.get("analysis_evidence") if isinstance(record, dict) else {},
            )
            if technique == "saxs"
            else {}
        )
        metric_parts = measured_result_metric_parts(
            current_metrics,
            technique=technique,
            params=params,
            strain_snapshot=strain_snapshot,
        )

        label = self._current_result_label_for_confirmation()
        parts = [part for part in [label, ", ".join(metric_parts[:4])] if part]
        if summary.get("result_origin") == "controlled_optimization_rerun" or bool(summary.get("ai_tuned")):
            parts.insert(0, tr("RESULT_ORIGIN_AI_TUNED"))
        elif get_language() == "zh":
            parts.insert(0, "原始结果")
        else:
            parts.insert(0, "Measured result")
        return " | ".join(part for part in parts if part)

    def _fallback_evidence_summary_text(self, analysis_evidence) -> str:
        fallback_text = self._batch_fallback_summary_text(analysis_evidence)
        if not fallback_text:
            return ""
        return tr("RESULTS_REVIEW_FALLBACK", fallback_text)

    def _has_condition_axis_risk(self, params, analysis_evidence=None) -> bool:
        analysis_evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
        return build_has_condition_axis_risk(
            params,
            analysis_evidence=analysis_evidence,
            symptom_names=self._evidence_symptom_names(analysis_evidence) if analysis_evidence else (),
        )

    def _has_fallback_conflict_risk(self, analysis_evidence=None) -> bool:
        if not isinstance(analysis_evidence, dict) or not analysis_evidence:
            return False
        return build_has_fallback_conflict_risk(self._evidence_symptom_names(analysis_evidence))
