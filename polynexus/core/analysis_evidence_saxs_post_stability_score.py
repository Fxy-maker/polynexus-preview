from __future__ import annotations

from typing import Any


def _clean_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _clamp_unit(value: float | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def _mean_finite(values: list[float | None]) -> float | None:
    finite = [float(value) for value in values if value is not None]
    if not finite:
        return None
    return sum(finite) / len(finite)


def _relative_spread(values: list[Any]) -> float | None:
    finite = [float(value) for value in values if _clean_float(value) is not None]
    if len(finite) < 2:
        return None
    scale = max(max(abs(value) for value in finite), 1e-9)
    return (max(finite) - min(finite)) / scale


def _inverse_ratio_score(value: float | None, limit: float) -> float | None:
    if value is None or limit <= 0:
        return None
    return _clamp_unit(1.0 - abs(float(value)) / float(limit), default=0.0)


def _non_empty_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if value in (None, "", [], {}):
            continue
        out[key] = value
    return out


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _saxs_stability_core_scores(
    output: dict[str, Any],
    symptom_names: set[str],
) -> dict[str, Any]:
    quality_score = _clean_float(output.get("quality_score"))
    l_confidence = _clean_float(output.get("L_confidence"))
    lc_confidence = _clean_float(output.get("lc_confidence"))
    q_peak_snr = _clean_float(output.get("q_peak_snr"))
    q_peak_diff_pct = _clean_float(output.get("q_peak_diff_pct"))
    if q_peak_diff_pct is None:
        q_peak_diff_pct = _clean_float(output.get("pyfai_q_peak_diff_pct"))

    parameter_terms = [
        _clamp_unit(quality_score, default=0.0) if quality_score is not None else None,
        _clamp_unit(l_confidence, default=0.0) if l_confidence is not None else None,
        _clamp_unit(lc_confidence, default=0.0) if lc_confidence is not None else None,
        _clamp_unit(q_peak_snr / 5.0, default=0.0) if q_peak_snr is not None else None,
    ]
    parameter_stability_score = _mean_finite(parameter_terms)
    if parameter_stability_score is None:
        parameter_stability_score = 0.5
    if output.get("beam_stop_contaminated"):
        parameter_stability_score -= 0.08
    if output.get("mask_truncated"):
        parameter_stability_score -= 0.04
    if output.get("Q_star_valid") is False:
        parameter_stability_score -= 0.05
    if "beamstop_or_low_q_contamination" in symptom_names:
        parameter_stability_score -= 0.04
    if "low_q_void_dominant" in symptom_names:
        parameter_stability_score -= 0.03
    parameter_stability_score = _clamp_unit(parameter_stability_score, default=0.0)

    l_spread = _relative_spread(
        [
            _clean_float(output.get("L_bragg")),
            _clean_float(output.get("L_corr_peak", output.get("L_corr"))),
            _clean_float(output.get("L_nm", output.get("L_best"))),
        ]
    )
    lc_spread = _relative_spread(
        [
            _clean_float(output.get("lc_tangent_nm")),
            _clean_float(output.get("lc_gamma_min_nm")),
            _clean_float(output.get("lc_idf_nm")),
        ]
    )
    phi_spread = _relative_spread(
        [
            _clean_float(output.get("phi_c")),
            _clean_float(output.get("phi_c_invariant")),
        ]
    )
    agreement_terms = [
        _inverse_ratio_score(l_spread, 0.10),
        _inverse_ratio_score(lc_spread, 0.15),
        _inverse_ratio_score(phi_spread, 0.12),
        _inverse_ratio_score(abs(q_peak_diff_pct) if q_peak_diff_pct is not None else None, 5.0),
    ]
    method_agreement_score = _mean_finite(agreement_terms)
    if method_agreement_score is None:
        method_agreement_score = 0.5
    if "multi_method_disagreement" in symptom_names:
        method_agreement_score -= 0.08
    if "gamma_tangent_unstable" in symptom_names:
        method_agreement_score -= 0.05
    method_agreement_score = _clamp_unit(method_agreement_score, default=0.0)

    batch_frames_raw = output.get("batch_frames")
    try:
        batch_frames = int(batch_frames_raw) if batch_frames_raw is not None else 0
    except (TypeError, ValueError):
        batch_frames = 0
    condition_label = str(output.get("condition_label", "") or "").strip().lower()
    condition_continuity_score = _clean_float(output.get("condition_continuity_score"))
    condition_confidence = _clean_float(output.get("condition_confidence"))
    missing_frames_raw = output.get("condition_missing_frames")
    try:
        missing_frames = int(missing_frames_raw) if missing_frames_raw is not None else 0
    except (TypeError, ValueError):
        missing_frames = 0
    coverage_score = None
    if batch_frames > 0:
        coverage_score = _clamp_unit(1.0 - (missing_frames / max(batch_frames, 1)), default=0.0)
    batch_terms = [condition_continuity_score, condition_confidence, coverage_score]
    batch_continuity_score = _mean_finite(batch_terms)
    if batch_continuity_score is None:
        batch_continuity_score = 1.0 if batch_frames <= 1 else 0.5
    if "condition_axis_missing" in symptom_names:
        batch_continuity_score = min(batch_continuity_score, 0.15)
    elif "condition_axis_unstable" in symptom_names:
        batch_continuity_score = min(batch_continuity_score, 0.55)
    if "batch_mixed_samples" in symptom_names:
        batch_continuity_score -= 0.12
    if "temperature_calibration_fallback_active" in symptom_names:
        parameter_stability_score -= 0.03
        batch_continuity_score -= 0.06
    if "diagnostic_lc_frames_present" in symptom_names:
        parameter_stability_score -= 0.06
        method_agreement_score -= 0.05
    if "temperature_sequence_near_melting_window" in symptom_names:
        method_agreement_score -= 0.03
    if "lc_unreliable_without_melting_proof" in symptom_names:
        method_agreement_score -= 0.08
        batch_continuity_score -= 0.03
    if "batch_summary_conflicts_with_frame_evidence" in symptom_names:
        method_agreement_score -= 0.08
        batch_continuity_score -= 0.08
    if "thickness_chain_unreliable" in symptom_names:
        method_agreement_score -= 0.10
        batch_continuity_score -= 0.04
    if "strain_void_lamellar_conflict" in symptom_names:
        method_agreement_score -= 0.08
    if "lamellar_anchor_lost_under_strain" in symptom_names:
        method_agreement_score -= 0.10
        batch_continuity_score -= 0.03
    if "qstar_rel_without_lamellar_support" in symptom_names:
        method_agreement_score -= 0.06
    if "orientation_shift_breaks_lamellar_comparison" in symptom_names:
        method_agreement_score -= 0.08

    return {
        "condition_label": condition_label,
        "condition_continuity_score": condition_continuity_score,
        "coverage_score": coverage_score,
        "l_spread": l_spread,
        "lc_spread": lc_spread,
        "phi_spread": phi_spread,
        "parameter_stability_score": parameter_stability_score,
        "method_agreement_score": method_agreement_score,
        "batch_continuity_score": batch_continuity_score,
    }


__all__ = [
    "_clean_float",
    "_clamp_unit",
    "_mean_finite",
    "_relative_spread",
    "_inverse_ratio_score",
    "_non_empty_mapping",
    "_safe_int",
    "_saxs_stability_core_scores",
]
