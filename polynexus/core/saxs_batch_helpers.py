"""Pure batch-parameter payload helpers for the SAXS wrapper."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Dict, List, Optional

import numpy as np

from .saxs_engine.saxs_quality_helpers import classify_single_frame_lc_reliability
from .saxs_engine.saxs_quality_contracts import (
    build_series_detector_quality_report,
    build_series_metric_evidence,
    build_series_orientation_evidence,
)


_QUALITY_EVIDENCE_FIELDS = (
    "data_quality_report",
    "guinier_evidence",
    "metric_evidence",
    "detector_quality_report",
    "raw_detector_quality_report",
    "orientation_evidence",
    "guinier_sequence_evidence",
    "sequence_rescue_candidates",
)

_AI_RESCUE_EVIDENCE_FIELDS = (
    "saxs_ai_rescue_plan",
    "saxs_ai_rescue_decision",
    "saxs_ai_rescue_replay",
    "saxs_confirmed_rerun_audit",
    "saxs_candidate_reference_resolution",
)


def batch_metric_evidence_scope(mode_or_experiment_type: Any) -> str:
    """Avoid relabeling a missing condition series as a static batch."""

    normalized = str(mode_or_experiment_type or "").strip().lower()
    if normalized in {
        "temperature",
        "cooling",
        "heating",
        "isothermal",
        "strain",
    }:
        return "aligned_batch"
    return "static_batch"


def copy_saxs_quality_evidence(value: Any) -> Dict[str, Any]:
    """Copy existing static 1D quality DTOs without interpreting them."""

    if value is None:
        return {}
    payload: Dict[str, Any] = {}
    for field in _QUALITY_EVIDENCE_FIELDS:
        item = getattr(value, field, None)
        if item is not None:
            payload[field] = deepcopy(item)
    return payload


def copy_saxs_ai_rescue_evidence(*sources: Any) -> Dict[str, Any]:
    """Copy existing AI rescue audit fields without interpreting them."""

    payload: Dict[str, Any] = {}
    for field in _AI_RESCUE_EVIDENCE_FIELDS:
        for source in sources:
            if source is None:
                continue
            item = getattr(source, field, None)
            if item is not None:
                if field == "saxs_candidate_reference_resolution" and not isinstance(item, Mapping):
                    continue
                payload[field] = deepcopy(item)
                break
    return payload


def copy_saxs_series_quality_evidence(
    rows: Any,
    points: Any,
    *,
    source_index_attr: str | None = None,
) -> List[Dict[str, Any]]:
    """Attach point evidence to copied parameter rows without reordering them."""

    copied_rows = [dict(row) for row in rows or () if isinstance(row, dict)]
    point_list = list(points or ())
    point_by_source: Dict[int, Any] = {}
    if source_index_attr:
        for point in point_list:
            try:
                source_index = int(getattr(point, source_index_attr))
            except (AttributeError, TypeError, ValueError):
                continue
            point_by_source[source_index] = point

    output: List[Dict[str, Any]] = []
    for index, row in enumerate(copied_rows):
        point = (
            point_by_source.get(index)
            if source_index_attr
            else (point_list[index] if index < len(point_list) else None)
        )
        row.update(copy_saxs_quality_evidence(point))
        output.append(row)
    return output


def build_static_batch_metric_evidence(analyses: Any) -> Dict[str, Dict[str, Any]]:
    """Aggregate aligned static frame evidence without introducing an axis."""

    frame_evidence = []
    for analysis in analyses or ():
        copied = copy_saxs_quality_evidence(analysis)
        frame_evidence.append(copied.get("metric_evidence"))
    return build_series_metric_evidence(
        frame_evidence,
        source_ref="saxs_static_batch.metric_evidence",
    )


def build_static_batch_2d_quality_evidence(analyses: Any) -> Dict[str, Dict[str, Any]]:
    """Aggregate existing static-frame 2D evidence without adding an axis."""

    copied_frames = [copy_saxs_quality_evidence(analysis) for analysis in analyses or ()]
    payload: Dict[str, Dict[str, Any]] = {}
    detector = build_series_detector_quality_report(
        [frame.get("detector_quality_report") for frame in copied_frames],
        source_ref="saxs_static_batch.detector_quality_report",
    )
    orientation = build_series_orientation_evidence(
        [frame.get("orientation_evidence") for frame in copied_frames],
        source_ref="saxs_static_batch.orientation_evidence",
    )
    raw_detector = build_series_detector_quality_report(
        [frame.get("raw_detector_quality_report") for frame in copied_frames],
        source_ref="saxs_static_batch.raw_detector_quality_report",
    )
    if detector is not None:
        payload["detector_quality_report"] = detector
    if orientation is not None:
        payload["orientation_evidence"] = orientation
    if raw_detector is not None:
        payload["raw_detector_quality_report"] = raw_detector
    return payload


def _build_batch_parameters_payload(batch_params, base_params: Optional[Dict[str, Any]] = None, *, experiment_type: str = "") -> Dict[str, Any]:
        """Return a batch-aware parameters payload for the GUI and persistence.

        The GUI already knows how to render ``batch_frames`` + ``_batch_data`` as
        a multi-row table. Keeping this logic here avoids forcing the UI to guess
        whether the engine ran a single frame or a whole directory/series.
        """

        payload: Dict[str, Any] = dict(base_params or {})
        batch_rows = [dict(row) for row in batch_params if isinstance(row, dict)]
        if not batch_rows:
            return payload
        if len(batch_rows) == 1:
            return payload or batch_rows[0]

        payload["batch_frames"] = len(batch_rows)
        payload["_batch_data"] = batch_rows

        condition_label = ""
        for row in batch_rows:
            label = str(row.get("condition_label") or "").strip()
            if label:
                condition_label = label
                break
        if condition_label:
            payload.setdefault("condition_label", condition_label)

        condition_values: List[float] = []
        for key in ("condition_value", "temperature_C", "strain_pct"):
            for row in batch_rows:
                value = row.get(key)
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    continue
                if np.isfinite(value):
                    condition_values.append(value)
            if condition_values:
                break
        if condition_values:
            payload["condition_range"] = f"{min(condition_values):.1f}-{max(condition_values):.1f}"

        source_counts: Dict[str, int] = {}
        source_key_counts: Dict[str, int] = {}
        source_text_counts: Dict[str, int] = {}
        confidences: List[float] = []
        missing_frames = 0
        continuity_values: List[float] = []
        fallback_rows = 0
        raw_snapshot_rows = 0
        fallback_reason_counts: Dict[str, int] = {}
        fallback_fields: set[str] = set()
        calibration_skip_counts: Dict[str, int] = {}
        melting_status_counts: Dict[str, int] = {}
        melting_reason_counts: Dict[str, int] = {}
        lc_reliability_counts: Dict[str, int] = {}
        lc_reliability_reason_counts: Dict[str, int] = {}
        raw_lc_values: List[float] = []
        calibrated_lc_values: List[float] = []
        raw_L_values: List[float] = []
        calibrated_L_values: List[float] = []
        raw_phi_values: List[float] = []
        calibrated_phi_values: List[float] = []
        lc_gap_values: List[float] = []
        L_gap_values: List[float] = []
        phi_gap_values: List[float] = []
        q_star_rel_values: List[float] = []
        porod_slope_values: List[float] = []
        strain_reliability_counts: Dict[str, int] = {}
        strain_reliability_reason_counts: Dict[str, int] = {}
        phase_counts: Dict[str, int] = {}
        phase_support_values: List[float] = []
        frame_low_conf_count = 0
        void_dominant_frame_count = 0
        phase_ambiguous_frame_count = 0
        effective_param_count = 0
        paper_figure_candidate_count = 0
        paper_conclusion_candidate_count = 0

        def _float_or_none(value: Any) -> float | None:
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None
            return number if np.isfinite(number) else None

        def _range_text(values: List[float], decimals: int = 2) -> str | None:
            finite = [float(value) for value in values if value is not None and np.isfinite(value)]
            if not finite:
                return None
            return f"{min(finite):.{decimals}f}-{max(finite):.{decimals}f}"

        for row in batch_rows:
            source = str(row.get("condition_source") or "").strip()
            if source:
                source_counts[source] = source_counts.get(source, 0) + 1
            source_key = str(row.get("condition_source_key") or "").strip()
            if source_key:
                source_key_counts[source_key] = source_key_counts.get(source_key, 0) + 1
            source_text = str(row.get("condition_source_text") or "").strip()
            if source_text:
                source_text_counts[source_text] = source_text_counts.get(source_text, 0) + 1
            conf = row.get("condition_confidence")
            try:
                conf = float(conf)
            except (TypeError, ValueError):
                conf = np.nan
            if np.isfinite(conf):
                confidences.append(conf)

            raw_snapshot = row.get("raw_snapshot")
            if isinstance(raw_snapshot, dict) and raw_snapshot:
                raw_snapshot_rows += 1

            if not str(row.get("lc_reliability_status") or "").strip():
                status, reason = classify_single_frame_lc_reliability(row)
                row["lc_reliability_status"] = status
                if not str(row.get("lc_reliability_reason") or "").strip():
                    row["lc_reliability_reason"] = reason

            method_key = str(row.get("lc_method") or "").strip().lower()
            fallback_active = bool(row.get("calibrated_fallback_active")) or method_key in {"calibrated", "qstar_calibrated"}
            if fallback_active:
                fallback_rows += 1
                reason = str(row.get("calibrated_fallback_reason") or "").strip()
                if reason:
                    fallback_reason_counts[reason] = fallback_reason_counts.get(reason, 0) + 1
                applied_fields = row.get("fallback_applied_fields")
                if isinstance(applied_fields, list):
                    for field in applied_fields:
                        field_name = str(field or "").strip()
                        if field_name:
                            fallback_fields.add(field_name)

            skip_reason = str(row.get("calibration_skipped_reason") or "").strip()
            if skip_reason:
                calibration_skip_counts[skip_reason] = calibration_skip_counts.get(skip_reason, 0) + 1

            melting_status = str(row.get("melting_window_status") or "").strip()
            if melting_status:
                melting_status_counts[melting_status] = melting_status_counts.get(melting_status, 0) + 1
            melting_reason = str(row.get("melting_window_reason") or "").strip()
            if melting_reason:
                melting_reason_counts[melting_reason] = melting_reason_counts.get(melting_reason, 0) + 1

            lc_status = str(row.get("lc_reliability_status") or "").strip()
            if lc_status:
                lc_reliability_counts[lc_status] = lc_reliability_counts.get(lc_status, 0) + 1
            lc_reason = str(row.get("lc_reliability_reason") or "").strip()
            if lc_reason:
                lc_reliability_reason_counts[lc_reason] = lc_reliability_reason_counts.get(lc_reason, 0) + 1

            strain_status = str(row.get("strain_reliability_status") or "").strip()
            if strain_status:
                strain_reliability_counts[strain_status] = strain_reliability_counts.get(strain_status, 0) + 1
            strain_reason = str(row.get("strain_reliability_reason") or "").strip()
            if strain_reason:
                strain_reliability_reason_counts[strain_reason] = strain_reliability_reason_counts.get(strain_reason, 0) + 1
            phase_name = str(row.get("phase_name") or row.get("strain_phase") or "").strip().lower()
            if phase_name:
                phase_counts[phase_name] = phase_counts.get(phase_name, 0) + 1
            phase_score = _float_or_none(row.get("phase_support_score"))
            if phase_score is not None:
                phase_support_values.append(phase_score)
            if strain_status and strain_status != "usable":
                frame_low_conf_count += 1
            if "low_q_void_dominant" in strain_reason or "strain_void_lamellar_conflict" in strain_reason:
                void_dominant_frame_count += 1
            if bool(row.get("phase_ambiguous")) or (phase_score is not None and phase_score < 0.55):
                phase_ambiguous_frame_count += 1
            if str(row.get("lc_method") or "").strip().lower() != "raw" or str(row.get("lamellar_interpretation_mode") or "").strip().lower() != "raw_measurement":
                effective_param_count += 1
            if bool(row.get("paper_figure_candidate")):
                paper_figure_candidate_count += 1
            if bool(row.get("paper_conclusion_candidate")):
                paper_conclusion_candidate_count += 1

            raw_lc = _float_or_none(row.get("lc_nm_raw"))
            cal_lc = _float_or_none(row.get("lc_nm_calibrated"))
            if raw_lc is not None:
                raw_lc_values.append(raw_lc)
            if cal_lc is not None:
                calibrated_lc_values.append(cal_lc)
            if raw_lc is not None and cal_lc is not None:
                lc_gap_values.append(abs(cal_lc - raw_lc) / max(abs(cal_lc), abs(raw_lc), 1e-9))

            raw_L = _float_or_none(row.get("L_nm_raw"))
            cal_L = _float_or_none(row.get("L_nm"))
            if raw_L is not None:
                raw_L_values.append(raw_L)
            if cal_L is not None:
                calibrated_L_values.append(cal_L)
            if raw_L is not None and cal_L is not None:
                L_gap_values.append(abs(cal_L - raw_L) / max(abs(cal_L), abs(raw_L), 1e-9))

            current_value = None
            for key in ("condition_value", "temperature_C", "strain_pct"):
                try:
                    current_value = float(row.get(key))
                except (TypeError, ValueError):
                    continue
                if np.isfinite(current_value):
                    break
                current_value = None
            if current_value is None:
                missing_frames += 1
            else:
                continuity_values.append(float(current_value))

            raw_phi = _float_or_none(row.get("Xc_raw"))
            cal_phi = _float_or_none(row.get("Xc_calibrated"))
            if raw_phi is not None:
                raw_phi_values.append(raw_phi)
            if cal_phi is not None:
                calibrated_phi_values.append(cal_phi)
            if raw_phi is not None and cal_phi is not None:
                phi_gap_values.append(abs(cal_phi - raw_phi) / max(abs(cal_phi), abs(raw_phi), 1e-9))

            q_star_rel = _float_or_none(row.get("Q_star_rel"))
            if q_star_rel is None:
                q_star_rel = _float_or_none(row.get("Q_rel"))
            if q_star_rel is not None:
                q_star_rel_values.append(q_star_rel)

            porod_slope = _float_or_none(row.get("porod_slope"))
            if porod_slope is not None:
                porod_slope_values.append(porod_slope)

        if source_counts:
            payload["condition_source"] = max(source_counts.items(), key=lambda item: item[1])[0]
        if source_key_counts:
            payload["condition_source_key"] = max(source_key_counts.items(), key=lambda item: item[1])[0]
        if source_text_counts:
            payload["condition_source_text"] = max(source_text_counts.items(), key=lambda item: item[1])[0]
        if confidences:
            payload["condition_confidence"] = round(float(np.mean(confidences)), 2)
        if missing_frames:
            payload["condition_missing_frames"] = missing_frames
        if len(continuity_values) >= 2:
            diffs = np.diff(np.asarray(continuity_values, dtype=float))
            non_zero = np.abs(diffs) > 1e-9
            score = 1.0 if np.all(non_zero) else max(0.0, 1.0 - (np.count_nonzero(~non_zero) / max(len(diffs), 1)))
            payload["condition_continuity_score"] = round(float(score), 2)
        elif continuity_values:
            payload["condition_continuity_score"] = 1.0

        fallback_ratio = round(float(fallback_rows / len(batch_rows)), 3) if batch_rows else 0.0
        fallback_reason = ""
        if fallback_reason_counts:
            if len(fallback_reason_counts) == 1:
                fallback_reason = next(iter(fallback_reason_counts.keys()))
            else:
                fallback_reason = "mixed"
        calibration_skip_reason = ""
        if calibration_skip_counts:
            calibration_skip_reason = (
                next(iter(calibration_skip_counts.keys()))
                if len(calibration_skip_counts) == 1
                else "mixed"
            )

        dominant_melting_status = ""
        if melting_status_counts:
            dominant_melting_status = max(melting_status_counts.items(), key=lambda item: item[1])[0]
        dominant_melting_reason = ""
        if melting_reason_counts:
            dominant_melting_reason = max(melting_reason_counts.items(), key=lambda item: item[1])[0]
        dominant_lc_reliability = ""
        if lc_reliability_counts:
            dominant_lc_reliability = max(lc_reliability_counts.items(), key=lambda item: item[1])[0]
        dominant_lc_reason = ""
        if lc_reliability_reason_counts:
            dominant_lc_reason = max(lc_reliability_reason_counts.items(), key=lambda item: item[1])[0]

        batch_calibration_summary = {
            "batch_rows": len(batch_rows),
            "fallback_rows": fallback_rows,
            "calibration_skipped_rows": sum(calibration_skip_counts.values()),
            "calibration_skipped_reason": calibration_skip_reason,
            "raw_snapshot_rows": raw_snapshot_rows,
            "fallback_ratio": fallback_ratio,
            "raw_structure_available": raw_snapshot_rows > 0,
            "calibrated_fallback_active": fallback_rows > 0,
            "calibrated_fallback_reason": fallback_reason,
            "fallback_applied_fields": sorted(fallback_fields),
            "raw_lc_range_nm": _range_text(raw_lc_values, 2),
            "calibrated_lc_range_nm": _range_text(calibrated_lc_values, 2),
            "raw_L_range_nm": _range_text(raw_L_values, 2),
            "calibrated_L_range_nm": _range_text(calibrated_L_values, 2),
            "raw_Xc_range": _range_text(raw_phi_values, 3),
            "calibrated_Xc_range": _range_text(calibrated_phi_values, 3),
            "lc_gap_mean": round(float(np.mean(lc_gap_values)), 3) if lc_gap_values else None,
            "L_gap_mean": round(float(np.mean(L_gap_values)), 3) if L_gap_values else None,
            "Xc_gap_mean": round(float(np.mean(phi_gap_values)), 3) if phi_gap_values else None,
        }
        batch_structure_summary = {
            "batch_rows": len(batch_rows),
            "melting_window_status_counts": dict(sorted(melting_status_counts.items())),
            "lc_reliability_status_counts": dict(sorted(lc_reliability_counts.items())),
            "diagnostic_only_rows": int(lc_reliability_counts.get("diagnostic_only", 0)),
            "low_confidence_rows": int(lc_reliability_counts.get("low_confidence", 0)),
            "usable_rows": int(lc_reliability_counts.get("usable", 0)),
            "within_window_rows": int(melting_status_counts.get("within_window", 0)),
            "near_onset_rows": int(melting_status_counts.get("near_onset", 0)),
            "post_end_rows": int(melting_status_counts.get("post_end", 0)),
            "dominant_melting_window_status": dominant_melting_status or None,
            "dominant_melting_window_reason": dominant_melting_reason or None,
            "dominant_lc_reliability_status": dominant_lc_reliability or None,
            "dominant_lc_reliability_reason": dominant_lc_reason or None,
        }
        q_star_rel_mean = round(float(np.mean(q_star_rel_values)), 4) if q_star_rel_values else None
        q_star_rel_span = round(float(max(q_star_rel_values) - min(q_star_rel_values)), 4) if len(q_star_rel_values) >= 2 else None
        porod_slope_mean = round(float(np.mean(porod_slope_values)), 4) if porod_slope_values else None
        porod_slope_span = round(float(max(porod_slope_values) - min(porod_slope_values)), 4) if len(porod_slope_values) >= 2 else None
        payload["batch_calibration_summary"] = {
            key: value
            for key, value in batch_calibration_summary.items()
            if value not in (None, "", [], {})
        }
        payload["batch_structure_summary"] = {
            key: value
            for key, value in batch_structure_summary.items()
            if value not in (None, "", [], {})
        }
        if batch_calibration_summary["raw_structure_available"]:
            payload["raw_structure_available"] = True
        if batch_calibration_summary["calibrated_fallback_active"]:
            payload["calibrated_fallback_active"] = True
            if batch_calibration_summary["calibrated_fallback_reason"]:
                payload["calibrated_fallback_reason"] = batch_calibration_summary["calibrated_fallback_reason"]
        if batch_calibration_summary["fallback_applied_fields"]:
            payload["fallback_applied_fields"] = batch_calibration_summary["fallback_applied_fields"]
        if dominant_melting_status:
            payload["melting_window_status"] = dominant_melting_status
        if dominant_melting_reason:
            payload["melting_window_reason"] = dominant_melting_reason
        if dominant_lc_reliability:
            payload["lc_reliability_status"] = dominant_lc_reliability
        if dominant_lc_reason:
            payload["lc_reliability_reason"] = dominant_lc_reason
        if q_star_rel_values:
            payload["Q_star_rel_mean"] = q_star_rel_mean
            payload["Q_star_rel_span"] = q_star_rel_span
        if porod_slope_values:
            payload["porod_slope_mean"] = porod_slope_mean
            payload["porod_slope_span"] = porod_slope_span
        if strain_reliability_counts:
            payload["strain_reliability_status"] = max(strain_reliability_counts.items(), key=lambda item: item[1])[0]
            payload["strain_reliability_status_counts"] = dict(sorted(strain_reliability_counts.items()))
        if strain_reliability_reason_counts:
            payload["strain_reliability_reason"] = max(strain_reliability_reason_counts.items(), key=lambda item: item[1])[0]
            payload["strain_reliability_reason_counts"] = dict(sorted(strain_reliability_reason_counts.items()))
        if phase_counts:
            payload["phase_distribution"] = dict(sorted(phase_counts.items()))
            payload["dominant_phase"] = max(phase_counts.items(), key=lambda item: item[1])[0]
        if phase_support_values:
            payload["phase_support_mean"] = round(float(np.mean(phase_support_values)), 3)
            payload["phase_support_span"] = round(float(np.max(phase_support_values) - np.min(phase_support_values)), 3) if len(phase_support_values) >= 2 else 0.0
        payload["frame_low_conf_count"] = frame_low_conf_count
        payload["void_dominant_frame_count"] = void_dominant_frame_count
        payload["phase_ambiguous_frame_count"] = phase_ambiguous_frame_count
        payload["effective_param_ratio"] = round(float(effective_param_count / len(batch_rows)), 3) if batch_rows else 0.0
        payload["paper_figure_candidate"] = bool(paper_figure_candidate_count and paper_figure_candidate_count >= max(1, len(batch_rows) // 2))
        payload["paper_conclusion_candidate"] = bool(paper_conclusion_candidate_count and paper_conclusion_candidate_count >= max(1, len(batch_rows) // 2))
        if payload["paper_conclusion_candidate"]:
            payload["paper_conclusion_ready"] = True

        return payload
