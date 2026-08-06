from __future__ import annotations

import json
import math
from typing import Iterable

from .i18n import tr


PREFERRED_RESULT_COLUMNS: tuple[str, ...] = (
    "file",
    "sample",
    "batch",
    "condition",
    "stage",
    "frame",
    "index",
    "temperature_C",
    "temp_C",
    "T_C",
    "time_min",
    "t_min",
    "L_nm",
    "lc_nm",
    "melting_window_status",
    "lc_reliability_status",
    "lc_reliability_reason",
    "lc_nm_raw",
    "lc_nm_calibrated",
    "Xc",
    "Xc_raw",
    "Xc_calibrated",
    "calibration_skipped_reason",
    "Xc_pct",
    "D_Scherrer_nm",
    "Tm_C",
    "Tm_peak_C",
    "Tc_C",
    "Tc_peak_C",
    "Tg_C",
    "effective_q_min",
    "q_min",
)

DEFAULT_TECHNIQUE_FILTERS: tuple[str, ...] = ("saxs", "waxs", "dsc", "ir", "nmr")

DEFAULT_COMPARISON_KEYS: tuple[str, ...] = (
    "r_squared",
    "L_nm",
    "Xc_pct",
    "Tm_peak_C",
    "Tc_peak_C",
    "quality_score",
)

SAXS_COMPARISON_KEYS: tuple[str, ...] = (
    "lc_nm",
    "lc_method",
    "calibrated_fallback_active",
    "calibration_skipped_reason",
    "lc_reliability_status",
    "melting_window_status",
    "Tm_onset_C",
    "Tm_peak_C",
    "Tm_end_C",
)

SAXS_STRAIN_COMPARISON_KEYS: tuple[str, ...] = (
    "invariant_Q_rel_mean",
    "invariant_Q_rel_span",
    "phi_void_mean",
    "phi_void_span",
    "f_Herman_mean",
    "f_Herman_span",
    "porod_slope_mean",
    "void_detected_frames",
)

STRAIN_REVIEW_METRIC_KEYS: tuple[str, ...] = (
    "invariant_Q_rel_mean",
    "phi_void_mean",
    "f_Herman_mean",
    "porod_slope_mean",
    "void_detected_frames",
)

DEFAULT_REVIEW_METRIC_KEYS: tuple[str, ...] = (
    "r_squared",
    "L_nm",
    "Xc_pct",
    "Tm_peak_C",
    "Tc_peak_C",
    "quality_score",
)


def gui_display_text_value(value, *, empty_text: str) -> str:
    if value is None:
        return str(empty_text or "")
    text = str(value).strip()
    return text or str(empty_text or "")


def gui_display_text(value, *, empty_text: str) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    elif value is None:
        text = ""
    else:
        text = str(value)
    text = text.strip()
    return text or str(empty_text or "")


def gui_format_score_value(value, *, empty_text: str, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(empty_text or "")
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{number:.3f}"


def gui_coerce_summary_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(number):
        return number
    return None


def results_has_critical_risk(
    params,
    *,
    technique: str,
    result=None,
    analysis_evidence: dict | None = None,
    condition_axis_risk: bool = False,
    fallback_conflict_risk: bool = False,
    waxs_structure: dict | None = None,
    waxs_support: dict | None = None,
) -> bool:
    if condition_axis_risk or fallback_conflict_risk:
        return True

    technique_key = str(technique or "").strip().lower()
    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    if technique_key == "waxs":
        structure = waxs_structure if isinstance(waxs_structure, dict) else {}
        support = waxs_support if isinstance(waxs_support, dict) else {}
        if structure.get("physical_support_pass") is False:
            return True
        overall = support.get("waxs_support_score")
        if overall is not None and overall < 0.72:
            return True

    if technique_key == "dsc":
        feature = evidence.get("feature_evidence", {}) if isinstance(evidence, dict) else {}
        structure = feature.get("structure_evidence", {}) if isinstance(feature.get("structure_evidence"), dict) else {}
        event_support = feature.get("event_support_evidence", {}) if isinstance(feature.get("event_support_evidence"), dict) else {}
        support_values = [
            gui_coerce_summary_float(event_support.get("event_support_score")),
            gui_coerce_summary_float(event_support.get("baseline_stability_score")),
            gui_coerce_summary_float(event_support.get("thermodynamic_consistency_score")),
        ]
        if structure.get("paper_conclusion_ready") is False and any(value is not None and value < 0.72 for value in support_values):
            return True

    if result is not None:
        validation_summary = str(getattr(result, "validation_summary", "") or "").strip()
        if validation_summary and validation_summary != "All checks passed":
            return True
        if bool(getattr(result, "mask_truncated", False)) or bool(getattr(result, "beam_stop_contaminated", False)):
            return True

    if isinstance(params, dict):
        validation_summary = str(params.get("validation_summary") or "").strip()
        if validation_summary and validation_summary != "All checks passed":
            return True
    return False


def has_condition_axis_risk(
    params,
    *,
    analysis_evidence: dict | None = None,
    symptom_names: Iterable[str] = (),
) -> bool:
    symptoms = {str(item or "").strip() for item in symptom_names if str(item or "").strip()}
    if "condition_axis_missing" in symptoms or "condition_axis_unstable" in symptoms:
        return True

    evidence = analysis_evidence if isinstance(analysis_evidence, dict) else {}
    if evidence:
        condition = evidence.get("condition_evidence", {}) if isinstance(evidence.get("condition_evidence"), dict) else {}
        missing_frames = condition.get("condition_missing_frames")
        continuity = gui_coerce_summary_float(condition.get("condition_continuity_score"))
        confidence = gui_coerce_summary_float(condition.get("condition_confidence"))
        try:
            if int(missing_frames or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass
        if continuity is not None and continuity < 0.85:
            return True
        if confidence is not None and confidence < 0.75:
            return True

    if not isinstance(params, dict):
        return False
    batch_frames = 0
    try:
        batch_frames = int(params.get("batch_frames", 0) or 0)
    except Exception:
        batch_frames = 0
    if batch_frames <= 1:
        return False
    missing_frames = params.get("condition_missing_frames")
    continuity = gui_coerce_summary_float(params.get("condition_continuity_score"))
    confidence = gui_coerce_summary_float(params.get("condition_confidence"))
    try:
        if int(missing_frames or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    if continuity is not None and continuity < 0.85:
        return True
    if confidence is not None and confidence < 0.75:
        return True
    return False


def has_fallback_conflict_risk(symptom_names: Iterable[str]) -> bool:
    symptoms = {str(item or "").strip() for item in symptom_names if str(item or "").strip()}
    return bool(
        "temperature_calibration_fallback_active" in symptoms
        and (
            "batch_summary_conflicts_with_frame_evidence" in symptoms
            or "thickness_chain_unreliable" in symptoms
        )
    )


def results_next_step_translation_key(
    params,
    *,
    mode: str,
    technique: str,
    has_risk: bool = False,
    has_result: bool = False,
) -> str:
    mode_key = str(mode or "").strip().lower()
    technique_key = str(technique or "").strip().lower()
    if mode_key == "sequence":
        return "RESULTS_SUMMARY_NEXT_SEQUENCE"
    if mode_key == "directory":
        return "RESULTS_SUMMARY_NEXT_DIRECTORY"
    if isinstance(params, dict) and len(params) > 1 and all(isinstance(v, dict) for v in params.values()) and not any(
        str(k).startswith("_") for k in params
    ):
        return "RESULTS_SUMMARY_NEXT_MULTI_SAMPLE"

    batch_frames = 0
    if isinstance(params, dict):
        try:
            batch_frames = int(params.get("batch_frames", 0) or 0)
        except Exception:
            batch_frames = 0
    if batch_frames > 1:
        return "RESULTS_SUMMARY_NEXT_BATCH"
    if technique_key == "saxs" and has_risk:
        return "RESULTS_SUMMARY_NEXT_SAXS_RISK"
    if technique_key == "waxs" and has_risk:
        return "RESULTS_SUMMARY_NEXT_WAXS_RISK"
    if technique_key == "dsc" and has_risk:
        return "RESULTS_SUMMARY_NEXT_DSC_RISK"
    if has_result:
        return "RESULTS_SUMMARY_NEXT_SINGLE"
    return ""


def result_mask_summary_text(result, *, current_technique: str, language: str = "en") -> str:
    if str(current_technique or "").strip().lower() != "saxs":
        return ""

    mask_truncated = bool(getattr(result, "mask_truncated", False))
    beamstop_warning = bool(getattr(result, "beam_stop_contaminated", False))

    if not mask_truncated and not beamstop_warning:
        return ""

    eff_q = getattr(result, "effective_q_min", 0.0)
    try:
        eff_q_text = f"{float(eff_q):.3f}"
    except Exception:
        eff_q_text = "0.000"

    if mask_truncated and beamstop_warning:
        return tr("RESULTS_SUMMARY_MASK_TRUNCATED_AND_BEAMSTOP", eff_q_text)
    if mask_truncated:
        return tr("RESULTS_SUMMARY_MASK_TRUNCATED_ONLY", eff_q_text)
    return tr("RESULTS_SUMMARY_MASK_BEAMSTOP_ONLY", eff_q_text)


def ordered_results_columns(columns, preferred: Iterable[str] = PREFERRED_RESULT_COLUMNS) -> list[str]:
    preferred_items = list(preferred)
    rank = {str(name).lower(): idx for idx, name in enumerate(preferred_items)}
    seen = set()
    unique_columns = []
    for col in columns:
        key = str(col)
        normalized = key.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique_columns.append(key)

    def sort_key(name):
        normalized = name.lower()
        return (rank.get(normalized, len(rank)), unique_columns.index(name))

    return sorted(unique_columns, key=sort_key)


def measured_result_metric_parts(
    current_metrics,
    *,
    technique: str,
    params: dict | None = None,
    strain_snapshot: dict | None = None,
) -> list[str]:
    metrics = current_metrics if isinstance(current_metrics, dict) else {}
    param_values = params if isinstance(params, dict) else {}
    strain = strain_snapshot if isinstance(strain_snapshot, dict) else {}
    metric_parts = []
    technique_key = str(technique or "").strip().lower()
    if technique_key == "dsc":
        for key in ("Tg_C", "Tm_peak_C", "Tcc_peak_C", "DHm_Jg", "DHc_Jg", "DHcc_Jg", "Xc_pct"):
            value = metrics.get(key, "")
            if value:
                metric_parts.append(f"{key}={value}")
    elif technique_key == "saxs":
        if strain.get("active"):
            status = str(strain.get("strain_reliability_status") or "").strip()
            if status:
                metric_parts.append(f"strain_reliability_status={status}")
            dominant_phase = str(strain.get("dominant_phase") or "").strip()
            if dominant_phase:
                metric_parts.append(f"dominant_phase={dominant_phase}")
            if strain.get("paper_figure_candidate") is not None:
                metric_parts.append(f"paper_figure_candidate={str(bool(strain.get('paper_figure_candidate'))).lower()}")
            if strain.get("paper_conclusion_candidate") is not None:
                metric_parts.append(f"paper_conclusion_candidate={str(bool(strain.get('paper_conclusion_candidate'))).lower()}")
            for key in ("invariant_Q_rel_mean", "phi_void_mean", "f_Herman_mean", "porod_slope_mean", "void_detected_frames"):
                value = metrics.get(key, "")
                if not value and key == "invariant_Q_rel_mean":
                    value = metrics.get("Q_star_rel_mean", "")
                if value:
                    metric_parts.append(f"{key}={value}")
        else:
            lc_method = str(param_values.get("lc_method") or metrics.get("lc_method") or "").strip()
            if lc_method:
                metric_parts.append(f"lc_method={lc_method}")
            skip_reason = str(param_values.get("calibration_skipped_reason") or metrics.get("calibration_skipped_reason") or "").strip()
            if skip_reason:
                metric_parts.append(f"calibration_skipped_reason={skip_reason}")
            fallback_active = param_values.get("calibrated_fallback_active")
            if fallback_active is not None:
                metric_parts.append(f"calibrated_fallback_active={bool(fallback_active)}")
            for key in ("lc_nm", "lc_reliability_status", "melting_window_status", "Tm_onset_C", "Tm_peak_C", "Tm_end_C"):
                value = metrics.get(key, "")
                if value:
                    metric_parts.append(f"{key}={value}")
    else:
        for key in ("r_squared", "L_nm", "Xc_pct", "Tm_peak_C", "Tc_peak_C", "quality_score"):
            value = metrics.get(key, "")
            if value:
                metric_parts.append(f"{key}={value}")
    return metric_parts
