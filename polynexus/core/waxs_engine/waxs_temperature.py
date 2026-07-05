"""WAXS in-situ temperature analysis (W4C).

Temperature-dependent WAXS: tracks crystal evolution during
heating/cooling (polymorph transitions, melting, recrystallisation).
Follows the same architecture as saxs_engine/saxs_temperature.py.
"""

import logging
logger = logging.getLogger(__name__)

import sys
import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from .core import analyze_scan, WAXSResult
from .config import WAXSConfig
from ..plot_edits import savefig_with_edits


@dataclass
class WAXSTempResult:
    label: str = ""
    temperatures: List[float] = field(default_factory=list)
    results: List[WAXSResult] = field(default_factory=list)
    config_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Tracked parameters
    Xc_vs_T: List[float] = field(default_factory=list)
    D_Scherrer_vs_T: List[float] = field(default_factory=list)
    peak_positions_vs_T: Dict[int, List[float]] = field(default_factory=dict)
    peak_family_tracks: List[Dict] = field(default_factory=list)
    peak_family_summary: Dict[str, Any] = field(default_factory=dict)
    xc_trend_summary: Dict[str, Any] = field(default_factory=dict)
    d_trend_summary: Dict[str, Any] = field(default_factory=dict)

    # Phase transitions detected
    transitions: List[Dict] = field(default_factory=list)

    @property
    def parameters(self):
        axis = _temperature_axis_metrics(self.temperatures)
        frame = _frame_evidence_metrics(self.temperatures, self.results)
        family = self.peak_family_summary or _peak_family_metrics(self.temperatures, self.results)
        x_values = self.Xc_vs_T
        if not x_values and self.results:
            x_values = [float(getattr(r, "Xc_pct", np.nan)) for r in self.results]
        xc_trend = self.xc_trend_summary or _crystallinity_trend_metrics(
            self.temperatures, x_values, self.results, frame, family
        )
        d_values = self.D_Scherrer_vs_T
        if not d_values and self.results:
            d_values = [float(getattr(r, "D_Scherrer_nm", np.nan)) for r in self.results]
        d_trend = self.d_trend_summary or _scherrer_trend_metrics(
            self.temperatures, d_values, self.results, frame, family, self.config_snapshot
        )
        return {
            'n_temperatures': axis["n_temperatures"],
            'n_transitions': len(self.transitions),
            'Xc_range': (min(self.Xc_vs_T), max(self.Xc_vs_T)) if self.Xc_vs_T else (np.nan, np.nan),
            'Xc_initial_pct': round(float(self.Xc_vs_T[0]), 3) if self.Xc_vs_T else np.nan,
            'Xc_final_pct': round(float(self.Xc_vs_T[-1]), 3) if self.Xc_vs_T else np.nan,
            'condition_label': 'Temperature',
            'condition_unit': 'C',
            'condition_source': 'filename',
            'condition_source_key': 'filename_parser',
            'condition_source_text': 'directory frame names',
            'condition_confidence': axis["temperature_axis_confidence"],
            'condition_missing_frames': axis["temperature_missing_count"],
            'condition_continuity_score': axis["temperature_continuity_score"],
            'temperature_values': axis["temperature_values"],
            'temperature_min_C': axis["temperature_min_C"],
            'temperature_max_C': axis["temperature_max_C"],
            'temperature_missing_count': axis["temperature_missing_count"],
            'temperature_duplicate_count': axis["temperature_duplicate_count"],
            'temperature_monotonic': axis["temperature_monotonic"],
            'temperature_step_median_C': axis["temperature_step_median_C"],
            'temperature_step_spread': axis["temperature_step_spread"],
            'sequence_order_source': axis["sequence_order_source"],
            'sequence_direction': axis["sequence_direction"],
            'heating_monotonic': axis["heating_monotonic"],
            'cooling_monotonic': axis["cooling_monotonic"],
            'hold_monotonic': axis["hold_monotonic"],
            'temperature_axis_confidence': axis["temperature_axis_confidence"],
            'temperature_axis_ready': axis["temperature_axis_ready"],
            'frame_count': frame["frame_count"],
            'frame_pass_count': frame["frame_pass_count"],
            'frame_low_conf_count': frame["frame_low_conf_count"],
            'valid_frame_count': frame["valid_frame_count"],
            'failed_frame_count': frame["failed_frame_count"],
            'frame_evidence': frame["frame_evidence"],
            'frame_quality_distribution': frame["frame_quality_distribution"],
            'frame_constraint_summary': frame["frame_constraint_summary"],
            'low_conf_frame_indices': frame["low_conf_frame_indices"],
            'low_conf_temperature_values': frame["low_conf_temperature_values"],
            'dominant_frame_failure_type': frame["dominant_frame_failure_type"],
            'median_r_squared': frame["median_r_squared"],
            'median_peak_count': frame["median_peak_count"],
            'median_structure_support_score': frame["median_structure_support_score"],
            'physical_support_pass_ratio': frame["physical_support_pass_ratio"],
            'D_values_nm': d_trend["D_values_nm"],
            'D_range_nm': d_trend["D_range_nm"],
            'D_slope_distribution': d_trend["D_slope_distribution"],
            'D_trend_monotonicity': d_trend["D_trend_monotonicity"],
            'D_support_peak_count': d_trend["D_support_peak_count"],
            'D_support_family_count': d_trend["D_support_family_count"],
            'FWHM_values_by_family': d_trend["FWHM_values_by_family"],
            'instrument_broadening_present': d_trend["instrument_broadening_present"],
            'D_trend_support_score': d_trend["D_trend_support_score"],
            'D_confidence_by_frame': d_trend["D_confidence_by_frame"],
            'D_jump_single_frame_count': d_trend["D_jump_single_frame_count"],
            'D_jump_single_frame_indices': d_trend["D_jump_single_frame_indices"],
            'peak_family_count': family["peak_family_count"],
            'peak_family_tracks': family["peak_family_tracks"],
            'peak_family_assignment_method': family["peak_family_assignment_method"],
            'peak_family_continuity_score': family["peak_family_continuity_score"],
            'peak_family_missing_frame_count': family["peak_family_missing_frame_count"],
            'peak_family_identity_swap_count': family["peak_family_identity_swap_count"],
            'peak_position_drift_per_family': family["peak_position_drift_per_family"],
            'peak_width_drift_per_family': family["peak_width_drift_per_family"],
            'peak_area_drift_per_family': family["peak_area_drift_per_family"],
            'new_peak_birth_temperatures': family["new_peak_birth_temperatures"],
            'peak_disappearance_temperatures': family["peak_disappearance_temperatures"],
            'peak_family_fragmented_count': family["peak_family_fragmented_count"],
            'peak_family_missing_ratio': family["peak_family_missing_ratio"],
            'Xc_values': xc_trend["Xc_values"],
            'Xc_range_pct': xc_trend["Xc_range_pct"],
            'Xc_slope_distribution': xc_trend["Xc_slope_distribution"],
            'Xc_trend_monotonicity': xc_trend["Xc_trend_monotonicity"],
            'Xc_background_sensitivity': xc_trend["Xc_background_sensitivity"],
            'Xc_peak_support_ratio': xc_trend["Xc_peak_support_ratio"],
            'Xc_transition_candidates': xc_trend["Xc_transition_candidates"],
            'transition_candidate_count': xc_trend["transition_candidate_count"],
            'transition_support_score': xc_trend["transition_support_score"],
            'Xc_trend_support_score': xc_trend["Xc_trend_support_score"],
            'crystallinity_jump_single_frame_count': xc_trend["crystallinity_jump_single_frame_count"],
            'crystallinity_jump_single_frame_indices': xc_trend["crystallinity_jump_single_frame_indices"],
        }


def _temperature_axis_metrics(temperatures):
    values = np.asarray(temperatures, dtype=float).ravel()
    if values.size == 0:
        return {
            "n_temperatures": 0,
            "temperature_values": [],
            "temperature_min_C": np.nan,
            "temperature_max_C": np.nan,
            "temperature_missing_count": 0,
            "temperature_duplicate_count": 0,
            "temperature_monotonic": False,
            "temperature_step_median_C": np.nan,
            "temperature_step_spread": np.nan,
            "temperature_continuity_score": 0.0,
            "temperature_axis_confidence": 0.0,
            "temperature_axis_ready": False,
            "sequence_order_source": "",
            "sequence_direction": "unknown",
            "heating_monotonic": False,
            "cooling_monotonic": False,
            "hold_monotonic": False,
        }

    finite = values[np.isfinite(values)]
    missing_count = int(values.size - finite.size)
    duplicates = int(finite.size - np.unique(finite).size) if finite.size else 0
    diffs = np.diff(finite) if finite.size >= 2 else np.array([], dtype=float)
    monotonic = bool(finite.size >= 2 and np.all(diffs > 0))
    step_median = float(np.median(diffs)) if diffs.size else np.nan
    step_spread = float(np.std(diffs) / max(abs(step_median), 1e-9)) if diffs.size >= 2 else 0.0
    continuity_score = 0.25
    if finite.size >= 2:
        continuity_score += 0.30
    if missing_count == 0:
        continuity_score += 0.18
    if duplicates == 0:
        continuity_score += 0.12
    if monotonic:
        continuity_score += 0.12
    if np.isfinite(step_spread):
        continuity_score += 0.03 * max(0.0, 1.0 - min(step_spread, 1.0))
    continuity_score = float(max(0.0, min(1.0, continuity_score)))
    temperature_axis_confidence = continuity_score
    ready = bool(finite.size >= 3 and missing_count == 0 and duplicates == 0 and monotonic)
    if ready and finite[-1] >= finite[0]:
        direction = "heating"
    elif ready and finite[-1] < finite[0]:
        direction = "cooling"
    elif finite.size >= 2:
        direction = "mixed"
    else:
        direction = "unknown"

    return {
        "n_temperatures": int(values.size),
        "temperature_values": [float(v) for v in values],
        "temperature_min_C": float(np.min(finite)) if finite.size else np.nan,
        "temperature_max_C": float(np.max(finite)) if finite.size else np.nan,
        "temperature_missing_count": missing_count,
        "temperature_duplicate_count": duplicates,
        "temperature_monotonic": monotonic,
        "temperature_step_median_C": step_median,
        "temperature_step_spread": step_spread,
        "temperature_continuity_score": continuity_score,
        "temperature_axis_confidence": temperature_axis_confidence,
        "temperature_axis_ready": ready,
        "sequence_order_source": "filename_parser",
        "sequence_direction": direction,
        "heating_monotonic": direction == "heating",
        "cooling_monotonic": direction == "cooling",
        "hold_monotonic": False,
    }


def _frame_evidence_metrics(temperatures, results):
    temps = np.asarray(temperatures, dtype=float).ravel()
    frame_records: list[dict] = []
    quality_scores: list[float] = []
    peak_counts: list[int] = []
    r_squared_values: list[float] = []
    support_scores: list[float] = []
    low_conf_indices: list[int] = []
    low_conf_temps: list[float] = []
    failure_counter: Counter[str] = Counter()

    def _clean_float(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return np.nan
        return number if np.isfinite(number) else np.nan

    def _clamp01(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return float(max(0.0, min(1.0, number)))

    def _frame_quality(r_squared, peak_count, xc_pct, d_scherrer):
        r2_score = 0.0
        if np.isfinite(r_squared):
            r2_score = _clamp01((r_squared - 0.60) / 0.40)
        peak_score = 0.0 if peak_count <= 0 else (0.55 if peak_count == 1 else 1.0)
        xc_score = 1.0 if np.isfinite(xc_pct) and xc_pct >= 0 else 0.0
        d_score = 1.0 if np.isfinite(d_scherrer) and d_scherrer > 0 else 0.0
        return _clamp01(0.34 * r2_score + 0.30 * peak_score + 0.18 * xc_score + 0.18 * d_score)

    def _failure_types(r_squared, peak_count, xc_pct, d_scherrer):
        failures: list[str] = []
        if peak_count < 2:
            failures.append("peak_count_underfit")
        if not np.isfinite(r_squared) or r_squared < 0.85:
            failures.append("fit_quality_low")
        if not np.isfinite(xc_pct) or xc_pct < 0:
            failures.append("crystallinity_unresolved")
        if not np.isfinite(d_scherrer) or d_scherrer <= 0:
            failures.append("scherrer_unresolved")
        return failures

    for idx, r in enumerate(results):
        temp = float(temps[idx]) if idx < len(temps) and np.isfinite(temps[idx]) else np.nan
        r_squared = _clean_float(getattr(r, "r_squared", np.nan))
        peak_count = int(getattr(r, "n_peaks", 0) or len(getattr(r, "peaks", []) or []))
        xc_pct = _clean_float(getattr(r, "Xc_pct", np.nan))
        d_scherrer = _clean_float(getattr(r, "D_Scherrer_nm", np.nan))
        peak_positions = [float(pk.get("two_theta", np.nan)) for pk in getattr(r, "peaks", []) if isinstance(pk, dict)]
        peak_widths = [float(pk.get("fwhm_deg", np.nan)) for pk in getattr(r, "peaks", []) if isinstance(pk, dict)]
        peak_areas = [float(pk.get("area", np.nan)) for pk in getattr(r, "peaks", []) if isinstance(pk, dict)]
        peak_area_sum = float(np.nansum([value for value in peak_areas if np.isfinite(value)])) if peak_areas else np.nan

        quality_score = _frame_quality(r_squared, peak_count, xc_pct, d_scherrer)
        failures = _failure_types(r_squared, peak_count, xc_pct, d_scherrer)
        physical_support_pass = bool(
            quality_score >= 0.70
            and peak_count >= 2
            and np.isfinite(r_squared) and r_squared >= 0.85
            and np.isfinite(xc_pct) and xc_pct >= 0
            and np.isfinite(d_scherrer) and d_scherrer > 0
        )
        paper_ready_candidate = bool(
            quality_score >= 0.82
            and peak_count >= 2
            and np.isfinite(r_squared) and r_squared >= 0.90
            and np.isfinite(xc_pct) and xc_pct >= 0
            and np.isfinite(d_scherrer) and d_scherrer > 0
            and not failures
        )
        frame_status = "pass" if physical_support_pass else "fail"
        primary_failure_type = failures[0] if failures else "stable"
        for failure in failures:
            failure_counter[failure] += 1

        if not physical_support_pass:
            low_conf_indices.append(idx)
            low_conf_temps.append(temp)

        frame_records.append(
            {
                "frame_index": idx,
                "temperature_C": temp,
                "label": str(getattr(r, "label", "") or "").strip() or None,
                "r_squared": float(r_squared) if np.isfinite(r_squared) else np.nan,
                "quality_score": round(float(quality_score), 6),
                "structure_support_score": round(float(quality_score), 6),
                "n_peaks": int(peak_count),
                "Xc_pct": float(xc_pct) if np.isfinite(xc_pct) else np.nan,
                "D_Scherrer_nm": float(d_scherrer) if np.isfinite(d_scherrer) else np.nan,
                "peak_positions": peak_positions if peak_positions else None,
                "peak_widths": peak_widths if peak_widths else None,
                "peak_area_sum": float(peak_area_sum) if np.isfinite(peak_area_sum) else np.nan,
                "physical_support_pass": physical_support_pass,
                "paper_ready_candidate": paper_ready_candidate,
                "frame_status": frame_status,
                "primary_failure_type": primary_failure_type,
                "failure_types": failures,
            }
        )
        quality_scores.append(float(quality_score))
        peak_counts.append(int(peak_count))
        if np.isfinite(r_squared):
            r_squared_values.append(float(r_squared))
        support_scores.append(float(quality_score))

    frame_count = len(frame_records)
    valid_frame_count = sum(1 for item in frame_records if item["physical_support_pass"])
    failed_frame_count = frame_count - valid_frame_count
    frame_pass_count = valid_frame_count
    frame_low_conf_count = len(low_conf_indices)
    quality_array = np.asarray(quality_scores, dtype=float) if quality_scores else np.asarray([], dtype=float)
    r2_array = np.asarray(r_squared_values, dtype=float) if r_squared_values else np.asarray([], dtype=float)
    peak_array = np.asarray(peak_counts, dtype=float) if peak_counts else np.asarray([], dtype=float)
    support_array = np.asarray(support_scores, dtype=float) if support_scores else np.asarray([], dtype=float)

    def _distribution(values):
        if values.size == 0:
            return {
                "min": np.nan,
                "q25": np.nan,
                "median": np.nan,
                "mean": np.nan,
                "q75": np.nan,
                "max": np.nan,
                "std": np.nan,
            }
        return {
            "min": float(np.nanmin(values)),
            "q25": float(np.nanpercentile(values, 25)),
            "median": float(np.nanmedian(values)),
            "mean": float(np.nanmean(values)),
            "q75": float(np.nanpercentile(values, 75)),
            "max": float(np.nanmax(values)),
            "std": float(np.nanstd(values)),
        }

    if failure_counter:
        dominant_frame_failure_type = sorted(
            failure_counter.items(),
            key=lambda item: (-item[1], ["peak_count_underfit", "fit_quality_low", "crystallinity_unresolved", "scherrer_unresolved"].index(item[0]) if item[0] in {"peak_count_underfit", "fit_quality_low", "crystallinity_unresolved", "scherrer_unresolved"} else 999),
        )[0][0]
    else:
        dominant_frame_failure_type = "stable"

    frame_constraint_summary = {
        "frame_count": frame_count,
        "valid_frame_count": valid_frame_count,
        "failed_frame_count": failed_frame_count,
        "frame_pass_count": frame_pass_count,
        "frame_low_conf_count": frame_low_conf_count,
        "frame_pass_ratio": float(valid_frame_count / frame_count) if frame_count else 0.0,
        "peak_count_underfit_count": int(failure_counter.get("peak_count_underfit", 0)),
        "fit_quality_low_count": int(failure_counter.get("fit_quality_low", 0)),
        "crystallinity_unresolved_count": int(failure_counter.get("crystallinity_unresolved", 0)),
        "scherrer_unresolved_count": int(failure_counter.get("scherrer_unresolved", 0)),
        "physical_support_pass_ratio": float(valid_frame_count / frame_count) if frame_count else 0.0,
    }

    return {
        "frame_count": frame_count,
        "frame_pass_count": frame_pass_count,
        "frame_low_conf_count": frame_low_conf_count,
        "valid_frame_count": valid_frame_count,
        "failed_frame_count": failed_frame_count,
        "frame_evidence": frame_records,
        "frame_quality_distribution": _distribution(quality_array),
        "frame_constraint_summary": frame_constraint_summary,
        "low_conf_frame_indices": low_conf_indices,
        "low_conf_temperature_values": [float(value) for value in low_conf_temps if np.isfinite(value)],
        "dominant_frame_failure_type": dominant_frame_failure_type,
        "median_r_squared": float(np.nanmedian(r2_array)) if r2_array.size else np.nan,
        "median_peak_count": float(np.nanmedian(peak_array)) if peak_array.size else np.nan,
        "median_structure_support_score": float(np.nanmedian(support_array)) if support_array.size else np.nan,
        "physical_support_pass_ratio": float(valid_frame_count / frame_count) if frame_count else 0.0,
    }


def _waxs_config_snapshot(config: Any) -> Dict[str, Any]:
    if config is None:
        return {}
    if isinstance(config, dict):
        raw = dict(config)
    elif hasattr(config, "to_dict") and callable(getattr(config, "to_dict")):
        try:
            raw = dict(config.to_dict())
        except Exception:
            raw = {}
    else:
        raw = {}
        for key in (
            "wavelength_A",
            "polarisation_factor",
            "background_method",
            "background_order",
            "smooth_method",
            "smooth_window",
            "smooth_order",
            "peak_function",
            "peak_height_min",
            "peak_distance",
            "max_peaks",
            "amorphous_subtraction",
            "amorphous_n_peaks",
            "scherrer_K",
            "two_theta_offset",
            "caglioti_U",
            "caglioti_V",
            "caglioti_W",
        ):
            if hasattr(config, key):
                raw[key] = getattr(config, key)

    snapshot: Dict[str, Any] = {}
    for key in (
        "wavelength_A",
        "polarisation_factor",
        "background_method",
        "background_order",
        "smooth_method",
        "smooth_window",
        "smooth_order",
        "peak_function",
        "peak_height_min",
        "peak_distance",
        "max_peaks",
        "amorphous_subtraction",
        "amorphous_n_peaks",
        "scherrer_K",
        "two_theta_offset",
        "caglioti_U",
        "caglioti_V",
        "caglioti_W",
    ):
        if key in raw:
            snapshot[key] = raw.get(key)
    return snapshot


def _peak_family_metrics(temperatures, results, tolerance_deg: float = 1.2):
    temps = np.asarray(temperatures, dtype=float).ravel()
    families: list[dict] = []
    birth_temps: list[float] = []
    disappearance_temps: list[float] = []
    position_drift: dict[str, float] = {}
    width_drift: dict[str, float] = {}
    area_drift: dict[str, float] = {}
    peak_count_missing_total = 0
    identity_swap_count = 0
    fragmented_family_count = 0
    previous_positions: dict[int, float] = {}
    next_family_id = 1

    def _clean_float(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return np.nan
        return number if np.isfinite(number) else np.nan

    def _append_family_point(family: dict, temp, peak: dict | None):
        family["temperatures_C"].append(float(temp) if np.isfinite(temp) else np.nan)
        if peak is None:
            family["peak_positions"].append(np.nan)
            family["peak_widths"].append(np.nan)
            family["peak_areas"].append(np.nan)
            family["missing_frame_count"] += 1
            family["frame_gap_count"] += 1
            return
        family["peak_positions"].append(_clean_float(peak.get("two_theta")))
        family["peak_widths"].append(_clean_float(peak.get("fwhm_deg")))
        family["peak_areas"].append(_clean_float(peak.get("area")))
        family["match_count"] += 1
        family["last_seen_temperature_C"] = float(temp) if np.isfinite(temp) else family.get("last_seen_temperature_C", np.nan)
        family["last_seen_frame_index"] = int(peak.get("_frame_index", family.get("last_seen_frame_index", -1)))

    for frame_index, r in enumerate(results):
        temp = float(temps[frame_index]) if frame_index < len(temps) and np.isfinite(temps[frame_index]) else np.nan
        peaks = []
        for pk in getattr(r, "peaks", []) or []:
            if not isinstance(pk, dict):
                continue
            center = _clean_float(pk.get("two_theta", pk.get("center")))
            if not np.isfinite(center):
                continue
            peaks.append(
                {
                    "two_theta": float(center),
                    "fwhm_deg": _clean_float(pk.get("fwhm_deg", pk.get("fwhm"))),
                    "area": _clean_float(pk.get("area")),
                    "_frame_index": frame_index,
                }
            )
        peaks.sort(key=lambda item: item["two_theta"])

        if not families:
            for peak in peaks:
                family = {
                    "family_id": next_family_id,
                    "temperatures_C": [],
                    "peak_positions": [],
                    "peak_widths": [],
                    "peak_areas": [],
                    "match_count": 0,
                    "missing_frame_count": 0,
                    "frame_gap_count": 0,
                    "birth_temperature_C": float(temp) if np.isfinite(temp) else np.nan,
                    "last_seen_temperature_C": float(temp) if np.isfinite(temp) else np.nan,
                    "last_seen_frame_index": frame_index,
                }
                next_family_id += 1
                _append_family_point(family, temp, peak)
                families.append(family)
                birth_temps.append(float(temp) if np.isfinite(temp) else np.nan)
            continue

        candidate_pairs: list[tuple[float, int, int]] = []
        for fi, family in enumerate(families):
            last_positions = [value for value in family["peak_positions"] if np.isfinite(value)]
            if not last_positions:
                continue
            anchor = float(last_positions[-1])
            for pi, peak in enumerate(peaks):
                dist = abs(float(peak["two_theta"]) - anchor)
                if dist <= tolerance_deg:
                    candidate_pairs.append((dist, fi, pi))
        candidate_pairs.sort(key=lambda item: item[0])

        matched_families: set[int] = set()
        matched_peaks: set[int] = set()
        assignments: dict[int, int] = {}
        for _, fi, pi in candidate_pairs:
            if fi in matched_families or pi in matched_peaks:
                continue
            matched_families.add(fi)
            matched_peaks.add(pi)
            assignments[fi] = pi

        for fi, family in enumerate(families):
            peak = peaks[assignments[fi]] if fi in assignments else None
            _append_family_point(family, temp, peak)
            if peak is not None:
                family["last_seen_temperature_C"] = float(temp) if np.isfinite(temp) else family.get("last_seen_temperature_C", np.nan)
                family["last_seen_frame_index"] = frame_index

        for pi, peak in enumerate(peaks):
            if pi in matched_peaks:
                continue
            family = {
                "family_id": next_family_id,
                "temperatures_C": [np.nan] * frame_index,
                "peak_positions": [np.nan] * frame_index,
                "peak_widths": [np.nan] * frame_index,
                "peak_areas": [np.nan] * frame_index,
                "match_count": 0,
                "missing_frame_count": frame_index,
                "frame_gap_count": 0,
                "birth_temperature_C": float(temp) if np.isfinite(temp) else np.nan,
                "last_seen_temperature_C": float(temp) if np.isfinite(temp) else np.nan,
                "last_seen_frame_index": frame_index,
            }
            next_family_id += 1
            _append_family_point(family, temp, peak)
            families.append(family)
            birth_temps.append(float(temp) if np.isfinite(temp) else np.nan)

        current_positions = {
            fam["family_id"]: float(fam["peak_positions"][-1])
            for fam in families
            if fam["peak_positions"] and np.isfinite(fam["peak_positions"][-1])
        }
        if previous_positions and current_positions:
            shared = sorted(set(previous_positions).intersection(current_positions))
            if len(shared) >= 2:
                prev_order = sorted(shared, key=lambda fid: previous_positions[fid])
                curr_order = sorted(shared, key=lambda fid: current_positions[fid])
                prev_rank = {fid: idx for idx, fid in enumerate(prev_order)}
                curr_rank = {fid: idx for idx, fid in enumerate(curr_order)}
                for i in range(len(shared)):
                    for j in range(i + 1, len(shared)):
                        a = shared[i]
                        b = shared[j]
                        if (prev_rank[a] - prev_rank[b]) * (curr_rank[a] - curr_rank[b]) < 0:
                            identity_swap_count += 1
        previous_positions = current_positions

    if families:
        for family in families:
            positions = np.asarray(family["peak_positions"], dtype=float)
            widths = np.asarray(family["peak_widths"], dtype=float)
            areas = np.asarray(family["peak_areas"], dtype=float)
            valid_positions = positions[np.isfinite(positions)]
            valid_widths = widths[np.isfinite(widths)]
            valid_areas = areas[np.isfinite(areas)]
            family["peak_position_drift_deg"] = float(np.nanstd(valid_positions)) if valid_positions.size >= 2 else 0.0
            family["peak_width_drift_deg"] = float(np.nanstd(valid_widths)) if valid_widths.size >= 2 else 0.0
            if valid_areas.size >= 2 and np.nanmean(valid_areas) > 0:
                family["peak_area_drift_rel"] = float(np.nanstd(valid_areas) / max(abs(np.nanmean(valid_areas)), 1e-9))
            else:
                family["peak_area_drift_rel"] = 0.0
            family["peak_positions"] = [float(v) if np.isfinite(v) else np.nan for v in family["peak_positions"]]
            family["peak_widths"] = [float(v) if np.isfinite(v) else np.nan for v in family["peak_widths"]]
            family["peak_areas"] = [float(v) if np.isfinite(v) else np.nan for v in family["peak_areas"]]
            family["temperature_points_C"] = [float(v) if np.isfinite(v) else np.nan for v in family["temperatures_C"]]
            family["family_label"] = f"family_{family['family_id']}"
            family["continuity_score"] = float(
                max(
                    0.0,
                    min(
                        1.0,
                        0.45 * (family["match_count"] / max(len(results), 1))
                        + 0.20 * max(0.0, 1.0 - min(family["peak_position_drift_deg"] / max(tolerance_deg, 1e-9), 1.0))
                        + 0.20 * max(0.0, 1.0 - min(family["peak_width_drift_deg"] / 1.0, 1.0))
                        + 0.15 * max(0.0, 1.0 - min(family["peak_area_drift_rel"], 1.0))
                    ),
                )
            )
            family["fragmented"] = bool(family["missing_frame_count"] > 0 and family["match_count"] >= 2)
            if family["fragmented"]:
                fragmented_family_count += 1
            if family["match_count"] <= 1 and np.isfinite(family["birth_temperature_C"]):
                disappearance_temps.append(float(family["birth_temperature_C"]))
            elif family["match_count"] > 0 and family["last_seen_temperature_C"] is not None and np.isfinite(family["last_seen_temperature_C"]) and family["last_seen_frame_index"] < len(results) - 1:
                disappearance_temps.append(float(family["last_seen_temperature_C"]))

            position_drift[f"family_{family['family_id']}"] = round(float(family["peak_position_drift_deg"]), 6)
            width_drift[f"family_{family['family_id']}"] = round(float(family["peak_width_drift_deg"]), 6)
            area_drift[f"family_{family['family_id']}"] = round(float(family["peak_area_drift_rel"]), 6)
            peak_count_missing_total += int(family["missing_frame_count"])

    family_scores = [float(item.get("continuity_score", 0.0)) for item in families]
    match_weights = [max(int(item.get("match_count", 0)), 1) for item in families]
    if family_scores:
        continuity_score = float(np.average(np.asarray(family_scores, dtype=float), weights=np.asarray(match_weights, dtype=float)))
    else:
        continuity_score = 0.0

    missing_ratio_den = max(len(results) * max(len(families), 1), 1)
    missing_ratio = float(peak_count_missing_total / missing_ratio_den)

    return {
        "peak_family_count": len(families),
        "peak_family_tracks": families,
        "peak_family_assignment_method": "nearest_position_continuity",
        "peak_family_continuity_score": continuity_score,
        "peak_family_missing_frame_count": peak_count_missing_total,
        "peak_family_identity_swap_count": int(identity_swap_count),
        "peak_position_drift_per_family": position_drift,
        "peak_width_drift_per_family": width_drift,
        "peak_area_drift_per_family": area_drift,
        "new_peak_birth_temperatures": [float(v) for v in birth_temps if np.isfinite(v)],
        "peak_disappearance_temperatures": [float(v) for v in disappearance_temps if np.isfinite(v)],
        "peak_family_fragmented_count": int(fragmented_family_count),
        "peak_family_missing_ratio": missing_ratio,
    }


def _scherrer_trend_metrics(temperatures, d_values, results, frame_summary, family_summary, config_snapshot=None):
    temps = np.asarray(temperatures, dtype=float).ravel()
    d = np.asarray(d_values, dtype=float).ravel()
    n = min(len(temps), len(d), len(results))
    config_snapshot = config_snapshot if isinstance(config_snapshot, dict) else {}
    if n <= 0:
        return {
            "D_values_nm": [],
            "D_range_nm": (np.nan, np.nan),
            "D_slope_distribution": {},
            "D_trend_monotonicity": "unknown",
            "D_support_peak_count": 0,
            "D_support_family_count": 0,
            "FWHM_values_by_family": {},
            "instrument_broadening_present": False,
            "D_trend_support_score": 0.0,
            "D_confidence_by_frame": [],
            "D_jump_single_frame_count": 0,
            "D_jump_single_frame_indices": [],
        }

    temps = temps[:n]
    d = d[:n]
    frame_records = frame_summary.get("frame_evidence", []) if isinstance(frame_summary, dict) else []
    if not isinstance(frame_records, list):
        frame_records = []
    family_tracks = family_summary.get("peak_family_tracks", []) if isinstance(family_summary, dict) else []
    if not isinstance(family_tracks, list):
        family_tracks = []

    def _clean_float(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return np.nan
        return number if np.isfinite(number) else np.nan

    def _distribution(values):
        values = np.asarray([_clean_float(v) for v in values], dtype=float)
        values = values[np.isfinite(values)]
        if values.size == 0:
            return {}
        return {
            "min": float(np.min(values)),
            "q25": float(np.percentile(values, 25)),
            "median": float(np.median(values)),
            "mean": float(np.mean(values)),
            "q75": float(np.percentile(values, 75)),
            "max": float(np.max(values)),
            "std": float(np.std(values)),
        }

    def _clamp01(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return float(max(0.0, min(1.0, number)))

    def _instrument_broadening_present(snapshot):
        for key in ("instrument_broadening_present", "instrument_broadening"):
            value = snapshot.get(key)
            if isinstance(value, bool):
                return value
        for key in ("caglioti_U", "caglioti_V", "caglioti_W"):
            value = _clean_float(snapshot.get(key))
            if value is not None and abs(value) > 1e-12:
                return True
        return False

    finite_mask = np.isfinite(temps) & np.isfinite(d)
    temps_f = temps[finite_mask]
    d_f = d[finite_mask]
    if temps_f.size == 0:
        return {
            "D_values_nm": [float(v) if np.isfinite(v) else np.nan for v in d],
            "D_range_nm": (np.nan, np.nan),
            "D_slope_distribution": {},
            "D_trend_monotonicity": "unknown",
            "D_support_peak_count": 0,
            "D_support_family_count": 0,
            "FWHM_values_by_family": {},
            "instrument_broadening_present": _instrument_broadening_present(config_snapshot),
            "D_trend_support_score": 0.0,
            "D_confidence_by_frame": [],
            "D_jump_single_frame_count": 0,
            "D_jump_single_frame_indices": [],
        }

    diffs_d = np.diff(d_f)
    diffs_t = np.diff(temps_f)
    valid_dt = np.abs(diffs_t) > 1e-9
    slopes = diffs_d[valid_dt] / diffs_t[valid_dt] if np.any(valid_dt) else np.array([], dtype=float)
    d_range = (float(np.nanmin(d_f)), float(np.nanmax(d_f)))
    delta_abs = np.abs(diffs_d) if diffs_d.size else np.array([], dtype=float)
    jump_threshold = max(0.12, float(np.nanmedian(delta_abs) + np.nanstd(delta_abs) * 1.5) if delta_abs.size else 0.12)
    jump_indices = [int(i + 1) for i, delta in enumerate(diffs_d) if np.isfinite(delta) and abs(delta) > jump_threshold]

    if slopes.size == 0:
        monotonicity = "unknown"
    elif np.all(slopes >= 0):
        monotonicity = "increasing"
    elif np.all(slopes <= 0):
        monotonicity = "decreasing"
    else:
        monotonicity = "mixed"

    support_peak_count = 0
    confidence_by_frame: list[dict[str, Any]] = []
    for idx in range(n):
        record = frame_records[idx] if idx < len(frame_records) and isinstance(frame_records[idx], dict) else {}
        peak_count = _clean_float(record.get("n_peaks"))
        r_squared = _clean_float(record.get("r_squared"))
        quality_score = _clean_float(record.get("quality_score"))
        d_value = _clean_float(record.get("D_Scherrer_nm"))
        peak_widths = [
            cleaned
            for value in (record.get("peak_widths") or [])
            for cleaned in [_clean_float(value)]
            if np.isfinite(cleaned)
        ]
        d_available = 1.0 if np.isfinite(d_value) else 0.0
        peak_ready = 1.0 if peak_count is not None and peak_count >= 2 else 0.0
        fit_score = _clamp01((r_squared - 0.70) / 0.30) if r_squared is not None and np.isfinite(r_squared) else _clamp01(quality_score)
        width_ready = 0.0
        if len(peak_widths) >= 2:
            width_ready = 1.0 if np.nanstd(peak_widths) <= 0.55 else 0.55
        elif len(peak_widths) == 1:
            width_ready = 0.45
        confidence = _clamp01(0.34 * d_available + 0.26 * peak_ready + 0.22 * fit_score + 0.18 * width_ready)
        if bool(record.get("physical_support_pass")):
            support_peak_count += 1
        else:
            confidence *= 0.72
        confidence_by_frame.append(
            {
                "frame_index": idx,
                "temperature_C": float(temps[idx]) if idx < len(temps) and np.isfinite(temps[idx]) else np.nan,
                "D_Scherrer_nm": float(d_value) if np.isfinite(d_value) else np.nan,
                "peak_count": int(peak_count) if peak_count is not None and np.isfinite(peak_count) else None,
                "confidence_score": round(float(confidence), 6),
            }
        )

    family_width_map: Dict[str, list[float]] = {}
    support_family_count = 0
    for family in family_tracks:
        if not isinstance(family, dict):
            continue
        label = str(family.get("family_label", "") or f"family_{family.get('family_id', '')}").strip()
        widths = [
            cleaned
            for value in (family.get("peak_widths") or [])
            for cleaned in [_clean_float(value)]
            if np.isfinite(cleaned)
        ]
        family_width_map[label] = [float(value) for value in widths]
        valid_widths = [value for value in widths if np.isfinite(value)]
        if len(valid_widths) >= 2 and _clean_float(family.get("continuity_score")) is not None and _clean_float(family.get("continuity_score")) >= 0.55:
            support_family_count += 1

    family_count = len(family_tracks)
    family_support_ratio = float(support_family_count / max(family_count, 1))
    support_ratio = float(support_peak_count / max(n, 1))
    slope_stability = 0.0
    if slopes.size >= 2:
        slope_scale = max(float(np.nanmean(np.abs(slopes))), 1e-9)
        slope_stability = float(max(0.0, 1.0 - min(float(np.nanstd(slopes)) / slope_scale, 1.0)))
    width_stability = 0.0
    if family_summary and isinstance(family_summary, dict):
        width_map = family_summary.get("peak_width_drift_per_family", {})
        if isinstance(width_map, dict) and width_map:
            width_values = [_clean_float(value) for value in width_map.values()]
            width_values = [value for value in width_values if value is not None]
            if width_values:
                max_width_drift = max(width_values)
                width_stability = max(0.0, 1.0 - min(max_width_drift / 0.55, 1.0))
    instrument_broadening_present = _instrument_broadening_present(config_snapshot)
    instrument_bonus = 0.08 if instrument_broadening_present else 0.0
    jump_penalty = min(len(jump_indices) * 0.14, 0.42)
    trend_support_score = float(
        max(
            0.0,
            min(
                1.0,
                0.34 * support_ratio
                + 0.22 * family_support_ratio
                + 0.18 * slope_stability
                + 0.18 * width_stability
                + instrument_bonus
                - jump_penalty
            ),
        )
    )

    return {
        "D_values_nm": [float(v) if np.isfinite(v) else np.nan for v in d],
        "D_range_nm": d_range,
        "D_slope_distribution": _distribution(slopes),
        "D_trend_monotonicity": monotonicity,
        "D_support_peak_count": int(support_peak_count),
        "D_support_family_count": int(support_family_count),
        "FWHM_values_by_family": family_width_map,
        "instrument_broadening_present": instrument_broadening_present,
        "D_trend_support_score": trend_support_score,
        "D_confidence_by_frame": confidence_by_frame,
        "D_jump_single_frame_count": int(len(jump_indices)),
        "D_jump_single_frame_indices": jump_indices,
    }


def _crystallinity_trend_metrics(temperatures, x_values, results, frame_summary, family_summary):
    temps = np.asarray(temperatures, dtype=float).ravel()
    x = np.asarray(x_values, dtype=float).ravel()
    n = min(len(temps), len(x), len(results))
    if n <= 0:
        return {
            "Xc_values": [],
            "Xc_range_pct": (np.nan, np.nan),
            "Xc_slope_distribution": {},
            "Xc_trend_monotonicity": "unknown",
            "Xc_background_sensitivity": np.nan,
            "Xc_peak_support_ratio": np.nan,
            "Xc_transition_candidates": [],
            "transition_candidate_count": 0,
            "transition_support_score": 0.0,
            "Xc_trend_support_score": 0.0,
            "crystallinity_jump_single_frame_count": 0,
            "crystallinity_jump_single_frame_indices": [],
        }

    temps = temps[:n]
    x = x[:n]
    frame_records = frame_summary.get("frame_evidence", []) if isinstance(frame_summary, dict) else []
    if not isinstance(frame_records, list):
        frame_records = []

    finite_mask = np.isfinite(temps) & np.isfinite(x)
    temps_f = temps[finite_mask]
    x_f = x[finite_mask]
    if temps_f.size == 0:
        return {
            "Xc_values": [float(v) if np.isfinite(v) else np.nan for v in x],
            "Xc_range_pct": (np.nan, np.nan),
            "Xc_slope_distribution": {},
            "Xc_trend_monotonicity": "unknown",
            "Xc_background_sensitivity": np.nan,
            "Xc_peak_support_ratio": np.nan,
            "Xc_transition_candidates": [],
            "transition_candidate_count": 0,
            "transition_support_score": 0.0,
            "Xc_trend_support_score": 0.0,
            "crystallinity_jump_single_frame_count": 0,
            "crystallinity_jump_single_frame_indices": [],
        }

    def _clean_float(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return np.nan
        return number if np.isfinite(number) else np.nan

    def _distribution(values):
        values = np.asarray([_clean_float(v) for v in values], dtype=float)
        values = values[np.isfinite(values)]
        if values.size == 0:
            return {}
        return {
            "min": float(np.min(values)),
            "q25": float(np.percentile(values, 25)),
            "median": float(np.median(values)),
            "mean": float(np.mean(values)),
            "q75": float(np.percentile(values, 75)),
            "max": float(np.max(values)),
            "std": float(np.std(values)),
        }

    diffs_x = np.diff(x_f)
    diffs_t = np.diff(temps_f)
    valid_dt = np.abs(diffs_t) > 1e-9
    slopes = diffs_x[valid_dt] / diffs_t[valid_dt] if np.any(valid_dt) else np.array([], dtype=float)
    x_range = (float(np.nanmin(x_f)), float(np.nanmax(x_f)))
    delta_abs = np.abs(diffs_x) if diffs_x.size else np.array([], dtype=float)
    jump_threshold = max(0.03, float(np.nanmedian(delta_abs) + np.nanstd(delta_abs) * 1.5) if delta_abs.size else 0.03)
    jump_indices = [int(i + 1) for i, delta in enumerate(diffs_x) if np.isfinite(delta) and abs(delta) > jump_threshold]

    if slopes.size == 0:
        monotonicity = "unknown"
    elif np.all(slopes >= 0):
        monotonicity = "increasing"
    elif np.all(slopes <= 0):
        monotonicity = "decreasing"
    else:
        monotonicity = "mixed"

    peak_support_hits = 0
    background_sensitive_hits = 0
    transition_candidates: list[dict] = []
    peak_area_sums = []
    for idx in range(n):
        record = frame_records[idx] if idx < len(frame_records) and isinstance(frame_records[idx], dict) else {}
        peak_count = _clean_float(record.get("n_peaks"))
        peak_area_sum = _clean_float(record.get("peak_area_sum"))
        peak_area_sums.append(peak_area_sum)
        supported = bool(
            record.get("physical_support_pass")
            and (peak_count is not None and peak_count >= 2)
            and np.isfinite(peak_area_sum)
        )
        if supported:
            peak_support_hits += 1
        if not supported:
            background_sensitive_hits += 1

    if len(temps_f) >= 2 and len(x_f) >= 2:
        for i in range(1, len(x_f)):
            delta = x_f[i] - x_f[i - 1]
            if abs(delta) >= jump_threshold:
                transition_candidates.append(
                    {
                        "frame_index": i,
                        "temperature_C": float(temps_f[i]),
                        "delta_Xc_pct": float(delta),
                        "kind": "jump" if abs(delta) >= jump_threshold else "trend",
                    }
                )

    peak_area_sums_f = np.asarray([_clean_float(v) for v in peak_area_sums], dtype=float)
    peak_area_sums_f = peak_area_sums_f[np.isfinite(peak_area_sums_f)]
    if peak_area_sums_f.size >= 2:
        area_slopes = np.diff(peak_area_sums_f)
    else:
        area_slopes = np.array([], dtype=float)

    x_slopes = slopes if slopes.size else np.array([], dtype=float)
    if x_slopes.size >= 1 and area_slopes.size >= 1:
        paired = min(len(x_slopes), len(area_slopes))
        if paired >= 1:
            trend_alignment = float(np.mean(np.sign(x_slopes[:paired]) == np.sign(area_slopes[:paired])))
        else:
            trend_alignment = np.nan
    else:
        trend_alignment = np.nan

    total_frames = max(n, 1)
    peak_support_ratio = float(peak_support_hits / total_frames)
    background_sensitivity = float(background_sensitive_hits / total_frames)
    monotonic_bonus = 0.18 if monotonicity in {"increasing", "decreasing"} else 0.06 if monotonicity == "mixed" else 0.0
    jump_penalty = min(len(jump_indices) * 0.12, 0.36)
    alignment_bonus = 0.12 if np.isfinite(trend_alignment) and trend_alignment >= 0.6 else 0.0
    support_score = float(
        max(
            0.0,
            min(
                1.0,
                0.34 * peak_support_ratio
                + 0.22 * max(0.0, 1.0 - background_sensitivity)
                + monotonic_bonus
                + alignment_bonus
                - jump_penalty
            ),
        )
    )
    family_continuity = 0.0
    if family_summary and isinstance(family_summary, dict):
        family_continuity = _clean_float(family_summary.get("peak_family_continuity_score"))
        if family_continuity is None:
            family_continuity = 0.0
    transition_candidate_count = len(transition_candidates)
    transition_presence_score = float(max(0.0, min(1.0, transition_candidate_count / 2.0)))
    transition_support_score = float(
        max(
            0.0,
            min(
                1.0,
                0.46 * transition_presence_score
                + 0.34 * support_score
                + 0.20 * family_continuity,
            ),
        )
    )

    return {
        "Xc_values": [float(v) if np.isfinite(v) else np.nan for v in x],
        "Xc_range_pct": x_range,
        "Xc_slope_distribution": _distribution(slopes),
        "Xc_trend_monotonicity": monotonicity,
        "Xc_background_sensitivity": background_sensitivity,
        "Xc_peak_support_ratio": peak_support_ratio,
        "Xc_transition_candidates": transition_candidates,
        "transition_candidate_count": transition_candidate_count,
        "transition_support_score": transition_support_score,
        "Xc_trend_support_score": support_score,
        "crystallinity_jump_single_frame_count": len(jump_indices),
        "crystallinity_jump_single_frame_indices": jump_indices,
    }


def analyze_temperature_series(scans, temperatures, config,
                               label="", polymer_name=""):
    result = WAXSTempResult(label=label)
    result.temperatures = temperatures
    result.config_snapshot = _waxs_config_snapshot(config)

    for scan, T in zip(scans, temperatures):
        frame_label = f"{label}_T{T:.0f}C" if label else f"{T:.0f}C"
        try:
            r = analyze_scan(scan, config, label=frame_label)
        except Exception as e:
            print(f"[temp] analyze_scan failed for {frame_label}: {e}", file=sys.stderr)
            r = WAXSResult(label=frame_label)
            logger.warning("WAXS temperature frame analysis failed.", exc_info=True)
        if r is None:
            r = WAXSResult(label=frame_label)
        result.results.append(r)
        result.Xc_vs_T.append(r.Xc_pct)
        result.D_Scherrer_vs_T.append(r.D_Scherrer_nm)

        for i, pk in enumerate(r.peaks):
            if i not in result.peak_positions_vs_T:
                result.peak_positions_vs_T[i] = []
            result.peak_positions_vs_T[i].append(pk['two_theta'])

    result.transitions = _detect_crystal_transitions(
        temperatures, result.Xc_vs_T)
    result.peak_family_summary = _peak_family_metrics(temperatures, result.results)
    result.peak_family_tracks = result.peak_family_summary.get("peak_family_tracks", [])
    frame_summary = _frame_evidence_metrics(temperatures, result.results)
    result.d_trend_summary = _scherrer_trend_metrics(
        temperatures,
        result.D_Scherrer_vs_T,
        result.results,
        frame_summary,
        result.peak_family_summary,
        result.config_snapshot,
    )
    result.xc_trend_summary = _crystallinity_trend_metrics(
        temperatures, result.Xc_vs_T, result.results, frame_summary, result.peak_family_summary
    )

    return result


def _detect_crystal_transitions(T, Xc):
    if len(T) < 3:
        return []

    Xc_arr = np.array(Xc, dtype=float)
    nan_mask = np.isnan(Xc_arr)
    if nan_mask.all():
        return []
    if nan_mask.any():
        valid_idx = np.where(~nan_mask)[0]
        Xc_filled = Xc_arr.copy()
        Xc_filled[nan_mask] = np.interp(
            np.where(nan_mask)[0], valid_idx, Xc_arr[valid_idx])
    else:
        Xc_filled = Xc_arr

    dXc = np.gradient(Xc_filled, np.asarray(T, dtype=float))
    noise = np.nanstd(dXc) if not np.all(np.isnan(dXc)) else 0.01
    if noise == 0:
        return []

    transitions = []
    neg_mask = dXc < -2 * noise
    for i in range(1, len(T) - 1):
        if neg_mask[i] and not neg_mask[i - 1]:
            transitions.append({
                'type': 'melting_onset',
                'T_C': float(T[i]),
                'Xc_before': float(Xc_arr[i - 1]),
                'Xc_after': float(Xc_arr[min(i + 1, len(T) - 1)]),
            })
            break

    pos_mask = dXc > 2 * noise
    for i in range(1, len(T) - 1):
        if pos_mask[i] and not pos_mask[i - 1]:
            transitions.append({
                'type': 'cold_crystallisation',
                'T_C': float(T[i]),
                'Xc_before': float(Xc_arr[i - 1]),
                'Xc_after': float(Xc_arr[min(i + 1, len(T) - 1)]),
            })
            break

    return transitions


# ---------------------------------------------------------------------------
#  Figure generation / export
# ---------------------------------------------------------------------------

def _temp_dirs(output_dir):
    import os, matplotlib
    matplotlib.use('Agg')
    fig_dir = os.path.join(output_dir, 'figures')
    data_dir = os.path.join(output_dir, 'data')
    os.makedirs(fig_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    return fig_dir, data_dir


def _save_temp_figure(fig, output_dir, name, config=None):
    import os
    import matplotlib.pyplot as plt
    fig_dir, _ = _temp_dirs(output_dir)
    fmt = getattr(config, 'fig_format', 'svg') if config else 'svg'
    dpi = getattr(config, 'fig_dpi', 300) if config else 300
    path = os.path.join(fig_dir, f'{name}.{fmt}')
    savefig_with_edits(fig, path, dpi=dpi, bbox_inches='tight',
                       facecolor='white')
    plt.close(fig)
    return path


def fig_temperature_2d_patterns(result, scans, output_dir, config=None):
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    if not scans:
        return ""
    indexed = [(i, s) for i, s in enumerate(scans) if s.image is not None]
    if not indexed:
        return ""

    n = len(indexed)
    n_cols = min(3, n)
    n_rows = int(np.ceil(n / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.2 * n_cols, 3.0 * n_rows))
    axes = np.atleast_1d(axes).ravel()

    for ax, (idx, scan) in zip(axes, indexed):
        img = np.asarray(scan.image, dtype=float)
        positive = img[np.isfinite(img) & (img > 0)]
        if len(positive) > 0:
            vmin = max(float(np.percentile(positive, 5)), 1e-6)
            vmax = float(np.percentile(positive, 99.5))
            norm = LogNorm(vmin=vmin, vmax=max(vmax, vmin * 1.01))
        else:
            norm = None
        ax.imshow(img, cmap='inferno', origin='lower', aspect='equal', norm=norm)
        T = result.temperatures[idx] if idx < len(result.temperatures) else np.nan
        ax.set_title(f'{T:g} deg C', fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])

    for ax in axes[len(indexed):]:
        ax.set_visible(False)

    pass  # suptitle removed for SCI
    return _save_temp_figure(fig, output_dir, 'Fig-WT1_2D_patterns', config)


def fig_temperature_waterfall(result, output_dir, config=None):
    import numpy as np
    import matplotlib.pyplot as plt

    valid = [r for r in result.results if len(r.two_theta) > 0 and len(r.I) > 0]
    if not valid:
        return ""

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    cmap = plt.cm.viridis
    temps = np.asarray(result.temperatures, dtype=float)
    norm = plt.Normalize(np.nanmin(temps), np.nanmax(temps)) if len(temps) else None
    offset = 0.0

    for idx, r in enumerate(result.results):
        if len(r.two_theta) == 0 or len(r.I) == 0:
            continue
        y = np.asarray(r.I, dtype=float)
        y = y - np.nanmin(y)
        ymax = np.nanmax(y)
        if ymax > 0:
            y = y / ymax
        T = result.temperatures[idx] if idx < len(result.temperatures) else np.nan
        color = cmap(norm(T)) if norm else '#2166AC'
        ax.plot(r.two_theta, y + offset, color=color, linewidth=1.0, label=f'{T:g} deg C')
        offset += 0.75

    ax.set_xlabel('2theta (deg)')
    ax.set_ylabel('Normalized intensity + offset')
    pass
    ax.legend(fontsize=7, ncol=2, framealpha=0.8)
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.tick_params(direction='in', top=True, right=True)
    fig.tight_layout()
    return _save_temp_figure(fig, output_dir, 'Fig-WT2_waterfall', config)


def fig_temperature_parameters(result, output_dir, config=None):
    import numpy as np
    import matplotlib.pyplot as plt

    T = np.asarray(result.temperatures, dtype=float)
    if len(T) < 2:
        print(f"[WAXS temp] figure skipped: only {len(T)} temperature points", file=sys.stderr)
        return ""

    Xc = np.asarray(result.Xc_vs_T, dtype=float)
    D = np.asarray(result.D_Scherrer_vs_T, dtype=float)
    d_trend = getattr(result, "d_trend_summary", {}) or _scherrer_trend_metrics(
        result.temperatures,
        result.D_Scherrer_vs_T,
        result.results,
        _frame_evidence_metrics(result.temperatures, result.results),
        getattr(result, "peak_family_summary", {}) or _peak_family_metrics(result.temperatures, result.results),
        getattr(result, "config_snapshot", {}),
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 3.8))

    ax1.plot(T, Xc, 'o-', color='#2166AC', markersize=5, linewidth=1.5)
    ax1.set_xlabel('Temperature (deg C)')
    ax1.set_ylabel('Crystallinity Xc (%)')
    pass  # title removed for SCI

    ax2.plot(T, D, 's-', color='#B2182B', markersize=5, linewidth=1.5)
    ax2.set_xlabel('Temperature (deg C)')
    ax2.set_ylabel('Scherrer size D (nm)')
    pass
    trend_mode = str(d_trend.get("D_trend_monotonicity", "") or "").strip()
    trend_score = d_trend.get("D_trend_support_score")
    instrument_broadening = bool(d_trend.get("instrument_broadening_present"))
    trend_lines = []
    if trend_mode:
        trend_lines.append(f"trend: {trend_mode}")
    if trend_score is not None and np.isfinite(trend_score):
        trend_lines.append(f"support: {float(trend_score):.2f}")
    trend_lines.append(f"broadening: {'yes' if instrument_broadening else 'no'}")
    ax2.text(
        0.02,
        0.98,
        "\n".join(trend_lines[:3]),
        transform=ax2.transAxes,
        va='top',
        ha='left',
        fontsize=8,
        bbox=dict(boxstyle='round,pad=0.28', facecolor='white', edgecolor='#B2182B', alpha=0.82),
    )

    for ax in (ax1, ax2):
        ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
        ax.tick_params(direction='in', top=True, right=True)

    fig.tight_layout()
    return _save_temp_figure(fig, output_dir, 'Fig-WT3_temperature_parameters', config)


def fig_temperature_peak_tracking(result, output_dir, config=None):
    import numpy as np
    import matplotlib.pyplot as plt

    T = np.asarray(result.temperatures, dtype=float)
    if len(T) < 2:
        return ""

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    family_tracks = getattr(result, "peak_family_tracks", []) or []
    if family_tracks:
        for family in family_tracks:
            family_label = str(family.get("family_label", f"family_{family.get('family_id', '?')}"))
            temps = np.asarray(family.get("temperature_points_C", []), dtype=float)
            positions = np.asarray(family.get("peak_positions", []), dtype=float)
            valid = np.isfinite(temps) & np.isfinite(positions)
            if valid.any():
                ax.plot(temps[valid], positions[valid], 'o-', linewidth=1.0, markersize=4,
                        label=family_label)
    else:
        for i, positions in sorted(result.peak_positions_vs_T.items()):
            y = np.full(len(T), np.nan)
            n = min(len(positions), len(T))
            y[:n] = positions[:n]
            valid = np.isfinite(y)
            if valid.any():
                ax.plot(T[valid], y[valid], 'o-', linewidth=1.0, markersize=4,
                        label=f'peak {i + 1}')

    ax.set_xlabel('Temperature (deg C)')
    ax.set_ylabel('Peak position 2theta (deg)')
    pass
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.legend(fontsize=7, framealpha=0.8)
    ax.tick_params(direction='in', top=True, right=True)
    fig.tight_layout()
    return _save_temp_figure(fig, output_dir, 'Fig-WT4_peak_tracking', config)


def export_temperature_csv(result, output_dir):
    import os
    import pandas as pd
    _, data_dir = _temp_dirs(output_dir)
    rows = []
    for idx, r in enumerate(result.results):
        row = {
            'Temperature(C)': result.temperatures[idx] if idx < len(result.temperatures) else None,
            'label': r.label,
            'Xc(%)': r.Xc_pct,
            'D_Scherrer(nm)': r.D_Scherrer_nm,
            'n_peaks': r.n_peaks,
            'r_squared': r.r_squared,
            'Xc_method': r.Xc_method,
        }
        for j, pk in enumerate(r.peaks):
            row[f'peak_{j + 1}_2theta'] = pk.get('two_theta', np.nan)
            row[f'peak_{j + 1}_d_A'] = pk.get('d_spacing_A', np.nan)
            row[f'peak_{j + 1}_FWHM'] = pk.get('fwhm_deg', np.nan)
            row[f'peak_{j + 1}_area'] = pk.get('area', np.nan)
        rows.append(row)
    path = os.path.join(data_dir, 'waxs_temperature_parameters.csv')
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def generate_temperature_figures(result, scans=None, output_dir="", config=None):
    figures = {}
    p = fig_temperature_2d_patterns(result, scans, output_dir, config)
    if p:
        figures['temperature_2d_patterns'] = p
    p = fig_temperature_waterfall(result, output_dir, config)
    if p:
        figures['temperature_waterfall'] = p
    p = fig_temperature_parameters(result, output_dir, config)
    if p:
        figures['temperature_parameters'] = p
    p = fig_temperature_peak_tracking(result, output_dir, config)
    if p:
        figures['temperature_peak_tracking'] = p
    csv_path = export_temperature_csv(result, output_dir)
    if csv_path:
        figures['temperature_csv'] = csv_path
    return figures


def fig_waxs_temperature(result, output_dir, config=None):
    return fig_temperature_parameters(result, output_dir, config)
