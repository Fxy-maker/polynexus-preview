from __future__ import annotations

from typing import Any

from .analysis_evidence_utils import _clean_float, _non_empty_mapping, _safe_int


def _saxs_core_feature_bundle(
    output: dict[str, Any],
    *,
    quality_flag: str = "",
    validation_summary: str = "",
) -> dict[str, Any]:
    signal_evidence = _non_empty_mapping(
        [
            ("q_peak_snr", _clean_float(output.get("q_peak_snr"))),
            ("Q_star", _clean_float(output.get("Q_star"))),
            ("Q_star_valid", output.get("Q_star_valid")),
            ("beam_stop_contaminated", output.get("beam_stop_contaminated")),
            ("mask_truncated", output.get("mask_truncated")),
            ("quality_flag", quality_flag or None),
            ("validation_summary", validation_summary or None),
        ]
    )

    peak_evidence = _non_empty_mapping(
        [
            ("L_bragg", _clean_float(output.get("L_bragg"))),
            ("L_lorentz", _clean_float(output.get("L_lorentz"))),
            ("L_pyfai_nm", _clean_float(output.get("L_pyfai_nm"))),
            ("q_peak_diff_pct", _clean_float(output.get("q_peak_diff_pct"))),
            (
                "fit_regions",
                output.get("fit_regions") if isinstance(output.get("fit_regions"), list) else None,
            ),
        ]
    )

    transform_evidence = _non_empty_mapping(
        [
            ("L_corr_peak", _clean_float(output.get("L_corr_peak", output.get("L_corr")))),
            ("lc_tangent_nm", _clean_float(output.get("lc_tangent_nm"))),
            ("lc_gamma_min_nm", _clean_float(output.get("lc_gamma_min_nm"))),
            ("lc_idf_nm", _clean_float(output.get("lc_idf_nm"))),
            ("phi_c_invariant", _clean_float(output.get("phi_c_invariant"))),
        ]
    )

    structure_evidence = _non_empty_mapping(
        [
            ("L_nm", _clean_float(output.get("L_nm", output.get("L_best")))),
            ("L_best", _clean_float(output.get("L_best", output.get("L_nm")))),
            ("L_confidence", _clean_float(output.get("L_confidence"))),
            ("lc_nm", _clean_float(output.get("lc_nm"))),
            ("la_nm", _clean_float(output.get("la_nm"))),
            ("phi_c", _clean_float(output.get("phi_c"))),
            ("lc_confidence", _clean_float(output.get("lc_confidence"))),
            ("lc_nm_raw", _clean_float(output.get("lc_nm_raw"))),
            ("la_nm_raw", _clean_float(output.get("la_nm_raw"))),
            ("Xc_raw", _clean_float(output.get("Xc_raw"))),
            ("Q_star_abs", _clean_float(output.get("Q_star_abs", output.get("Q_star")))),
            ("Q_star_rel", _clean_float(output.get("Q_star_rel", output.get("Q_rel")))),
            ("Q_star_rel_mean", _clean_float(output.get("Q_star_rel_mean"))),
            ("Q_star_rel_span", _clean_float(output.get("Q_star_rel_span"))),
            ("has_voids", output.get("has_voids")),
            ("phi_void", _clean_float(output.get("phi_void"))),
            ("phi_void_mean", _clean_float(output.get("phi_void_mean"))),
            ("phi_void_span", _clean_float(output.get("phi_void_span"))),
            (
                "void_detected_frames",
                _safe_int(output.get("void_detected_frames"), default=0)
                if output.get("void_detected_frames") is not None
                else None,
            ),
            ("void_AR", _clean_float(output.get("void_AR"))),
            ("f_Herman", _clean_float(output.get("f_Herman", output.get("f_herman")))),
            ("f_Herman_mean", _clean_float(output.get("f_Herman_mean"))),
            ("f_Herman_span", _clean_float(output.get("f_Herman_span"))),
            ("porod_slope", _clean_float(output.get("porod_slope"))),
            ("porod_slope_mean", _clean_float(output.get("porod_slope_mean"))),
            ("porod_slope_span", _clean_float(output.get("porod_slope_span"))),
            ("lc_nm_effective", _clean_float(output.get("lc_nm_effective"))),
            ("la_nm_effective", _clean_float(output.get("la_nm_effective"))),
            ("Xc_effective", _clean_float(output.get("Xc_effective"))),
            (
                "lamellar_interpretation_mode",
                str(output.get("lamellar_interpretation_mode", "") or "").strip() or None,
            ),
            ("effective_param_reason", str(output.get("effective_param_reason", "") or "").strip() or None),
            ("melting_window_status", str(output.get("melting_window_status", "") or "").strip() or None),
            ("melting_window_reason", str(output.get("melting_window_reason", "") or "").strip() or None),
            ("lc_reliability_status", str(output.get("lc_reliability_status", "") or "").strip() or None),
            ("lc_reliability_reason", str(output.get("lc_reliability_reason", "") or "").strip() or None),
            ("lc_nm_calibrated", _clean_float(output.get("lc_nm_calibrated"))),
            ("la_nm_calibrated", _clean_float(output.get("la_nm_calibrated"))),
            ("Xc_calibrated", _clean_float(output.get("Xc_calibrated"))),
            ("lc_confidence_calibrated", _clean_float(output.get("lc_confidence_calibrated"))),
            ("lc_method", str(output.get("lc_method", "") or "").strip() or None),
            ("calibrated_fallback_active", output.get("calibrated_fallback_active")),
            (
                "calibrated_fallback_reason",
                str(output.get("calibrated_fallback_reason", "") or "").strip() or None,
            ),
            (
                "calibration_skipped_reason",
                str(output.get("calibration_skipped_reason", "") or "").strip() or None,
            ),
            (
                "fallback_applied_fields",
                output.get("fallback_applied_fields")
                if isinstance(output.get("fallback_applied_fields"), list)
                else None,
            ),
            ("sasmodels_R2", _clean_float(output.get("sasmodels_R2"))),
            ("sasmodels_model_used", str(output.get("sasmodels_model_used", "") or "").strip() or None),
        ]
    )

    return {
        "signal_evidence": signal_evidence,
        "peak_evidence": peak_evidence,
        "transform_evidence": transform_evidence,
        "structure_evidence": structure_evidence,
    }


__all__ = ["_saxs_core_feature_bundle"]
