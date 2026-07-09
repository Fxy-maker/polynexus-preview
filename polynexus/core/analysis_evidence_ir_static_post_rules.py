from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float

_IR_STATIC_CONSTRAINT_NAMES = {
    "key_band_support_insufficient",
    "assignment_without_characteristic_bands",
    "baseline_sensitive_assignment",
    "baseline_drift_low_wn",
    "baseline_drift_high_wn",
    "key_band_mismatch",
    "crowded_band_underfit",
    "over_smoothed_weak_bands",
    "normalization_bias",
    "noise_dominant",
    "weak_peak_only_support",
    "overcrowded_band_separation_unstable",
    "polymer_score_without_assignment_support",
    "crystallinity_index_without_band_support",
    "ir_xc_uncalibrated",
}


def _evaluate_ir_static_constraint(
    item_name: str,
    ir_support: dict[str, Any],
    residual_key: str,
    residual: dict[str, Any],
) -> tuple[bool, Any]:
    peak_count = _clean_float(ir_support.get("peak_count"))
    assigned_peak_count = _clean_float(ir_support.get("assigned_peak_count"))
    peak_width_spread = _clean_float(ir_support.get("peak_width_spread"))
    baseline_method = str(ir_support.get("baseline_method", "") or "").strip().lower()
    normalization_method = str(ir_support.get("normalization_method", "") or "").strip().lower()
    peak_distance = _clean_float(ir_support.get("peak_distance"))
    peak_fit_window = _clean_float(ir_support.get("peak_fit_window_cm1"))
    assignment_confidence = _clean_float(ir_support.get("assignment_confidence"))
    polymer_score = _clean_float(ir_support.get("polymer_score"))
    reference_band_count = int(ir_support.get("reference_band_count") or 0)
    reference_band_hit_count = int(ir_support.get("reference_band_hit_count") or 0)
    reference_band_missing_count = int(ir_support.get("reference_band_missing_count") or 0)
    x_pct = _clean_float(ir_support.get("Xc_pct"))
    x_method = str(ir_support.get("Xc_method") or "").strip()
    x_calibration_status = str(ir_support.get("Xc_calibration_status") or "").strip()

    if item_name == "key_band_support_insufficient":
        observed = {
            "reference_band_count": reference_band_count,
            "reference_band_hit_count": reference_band_hit_count,
            "reference_band_missing_count": reference_band_missing_count,
        }
        triggered = reference_band_count > 0 and (
            reference_band_hit_count < 3 or reference_band_missing_count > 0
        )
    elif item_name == "assignment_without_characteristic_bands":
        observed = {
            "assignment_confidence": assignment_confidence,
            "reference_band_hit_count": reference_band_hit_count,
            "reference_band_missing_count": reference_band_missing_count,
        }
        triggered = assignment_confidence is not None and assignment_confidence < 0.8 and (
            reference_band_hit_count < 3 or reference_band_missing_count > 0
        )
    elif item_name == "baseline_sensitive_assignment":
        observed = {
            "baseline_method": baseline_method or None,
            "normalization_method": normalization_method or None,
            "peak_width_spread": peak_width_spread,
        }
        triggered = (
            baseline_method in {"als", "mute_zone", "none"}
            or normalization_method in {"none", "peak"}
            or (peak_width_spread is not None and peak_width_spread > 0.4)
        )
    elif item_name == "baseline_drift_low_wn":
        observed = {
            "residual_type": residual_key or None,
            "max_residual_region": residual.get("max_residual_region", "unknown"),
        }
        triggered = residual_key == "baseline_drift_low_wn"
    elif item_name == "baseline_drift_high_wn":
        observed = {
            "residual_type": residual_key or None,
            "max_residual_region": residual.get("max_residual_region", "unknown"),
        }
        triggered = residual_key == "baseline_drift_high_wn"
    elif item_name == "key_band_mismatch":
        observed = {
            "residual_type": residual_key or None,
            "reference_band_hit_count": reference_band_hit_count,
            "reference_band_missing_count": reference_band_missing_count,
            "max_residual_region": residual.get("max_residual_region", "unknown"),
        }
        triggered = residual_key in {"key_band_mismatch", "peak_mismatch"} and (
            assignment_confidence is None
            or assignment_confidence < 0.9
            or reference_band_hit_count < 3
            or reference_band_missing_count > 0
        )
    elif item_name == "crowded_band_underfit":
        observed = {
            "residual_type": residual_key or None,
            "peak_count": peak_count,
            "peak_distance": peak_distance,
            "peak_fit_window_cm1": peak_fit_window,
            "peak_width_spread": peak_width_spread,
        }
        triggered = residual_key == "crowded_band_underfit" or (
            residual_key == "peak_mismatch"
            and (
                (peak_count is not None and peak_count >= 8)
                or (peak_distance is not None and peak_distance < 10.0)
                or (peak_fit_window is not None and peak_fit_window > 50.0)
                or (peak_width_spread is not None and peak_width_spread > 0.45)
            )
        )
    elif item_name == "over_smoothed_weak_bands":
        observed = {
            "residual_type": residual_key or None,
            "peak_count": peak_count,
            "peak_width_spread": peak_width_spread,
        }
        triggered = residual_key == "over_smoothed_weak_bands"
    elif item_name == "normalization_bias":
        observed = {
            "residual_type": residual_key or None,
            "baseline_method": baseline_method or None,
            "normalization_method": normalization_method or None,
        }
        triggered = residual_key == "normalization_bias"
    elif item_name == "noise_dominant":
        observed = {
            "residual_type": residual_key or None,
            "peak_count": peak_count,
            "peak_width_spread": peak_width_spread,
        }
        triggered = residual_key in {"noise_dominant", "noise"}
    elif item_name == "weak_peak_only_support":
        observed = {
            "peak_count": peak_count,
            "assigned_peak_count": assigned_peak_count,
            "reference_band_hit_count": reference_band_hit_count,
        }
        triggered = (
            peak_count is not None
            and peak_count > 0
            and reference_band_hit_count < 2
            and (assignment_confidence is None or assignment_confidence < 0.85)
        )
    elif item_name == "overcrowded_band_separation_unstable":
        observed = {
            "peak_count": peak_count,
            "peak_distance": peak_distance,
            "peak_fit_window_cm1": peak_fit_window,
            "peak_width_spread": peak_width_spread,
        }
        triggered = (
            (peak_distance is not None and peak_distance < 10.0)
            or (peak_fit_window is not None and peak_fit_window > 50.0)
            or (peak_count is not None and peak_count >= 8)
            or (peak_width_spread is not None and peak_width_spread > 0.45)
        )
    elif item_name == "polymer_score_without_assignment_support":
        observed = {
            "polymer_score": polymer_score,
            "reference_band_hit_count": reference_band_hit_count,
            "assigned_peak_count": assigned_peak_count,
        }
        triggered = polymer_score is not None and polymer_score < 0.85 and (
            reference_band_hit_count < 3 or assigned_peak_count < 4
        )
    elif item_name == "crystallinity_index_without_band_support":
        observed = {
            "Xc_pct": x_pct,
            "reference_band_hit_count": reference_band_hit_count,
            "reference_band_missing_count": reference_band_missing_count,
        }
        triggered = x_pct is not None and x_pct > 0 and (
            reference_band_hit_count < 2 or reference_band_missing_count > 0
        )
    elif item_name == "ir_xc_uncalibrated":
        observed = {
            "Xc_pct": x_pct,
            "Xc_method": x_method or None,
            "Xc_calibration_status": x_calibration_status or None,
        }
        triggered = (
            x_calibration_status == "uncalibrated_index"
            or x_method.lower().endswith("_uncalibrated")
        )
    else:
        observed = None
        triggered = False

    return triggered, observed


__all__ = [
    "_IR_STATIC_CONSTRAINT_NAMES",
    "_evaluate_ir_static_constraint",
]
