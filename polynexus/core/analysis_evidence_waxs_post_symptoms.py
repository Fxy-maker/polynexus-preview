from __future__ import annotations

from typing import Any

from .analysis_evidence_common import _clean_float


def _waxs_symptoms_from_constraints(
    constraints: list[dict[str, Any]],
    output: dict[str, Any],
    validation: dict[str, Any],
    residual: dict[str, Any],
) -> list[dict[str, Any]]:
    symptom_specs: dict[str, tuple[str, list[str]]] = {
        "temperature_axis_missing": (
            "The temperature axis is missing or incomplete for this WAXS sequence.",
            ["condition_confidence", "temperature_missing_count"],
        ),
        "temperature_axis_low_confidence": (
            "The temperature axis is present but still low-confidence.",
            ["condition_confidence", "condition_continuity_score"],
        ),
        "temperature_sequence_nonmonotonic": (
            "The temperature sequence is not strictly monotonic.",
            ["temperature_values", "sequence_order_source"],
        ),
        "temperature_duplicate_frames": (
            "Duplicate temperature frames weaken sequence continuity.",
            ["temperature_duplicate_count", "temperature_values"],
        ),
        "peak_visibility": (
            "No resolved sharp peak support is visible yet.",
            ["peak_distance", "max_peaks"],
        ),
        "peak_count_insufficient": (
            "Too few resolved peaks to support stable phase or size claims.",
            ["peak_distance", "max_peaks"],
        ),
        "peak_family_unstable": (
            "Peak spacing or peak widths drift too much for a stable peak family.",
            ["peak_distance", "peak_function"],
        ),
        "peak_family_identity_swap": (
            "Peak identity appears to swap between frames instead of staying continuous.",
            ["peak_family_assignment_method", "peak_distance"],
        ),
        "peak_family_track_fragmented": (
            "Peak family tracks are fragmented and need continuity recovery.",
            ["peak_family_continuity_score", "peak_family_assignment_method"],
        ),
        "peak_family_missing_too_many_frames": (
            "Too many frames are missing from the peak family tracks.",
            ["peak_family_missing_frame_count", "peak_family_missing_ratio"],
        ),
        "peak_position_drift_unphysical": (
            "Peak family position drift is too large to be treated as a stable family.",
            ["peak_position_drift_per_family", "peak_family_continuity_score"],
        ),
        "peak_width_trend_unstable": (
            "Peak widths drift too much to keep the family assignment stable.",
            ["peak_width_drift_per_family", "peak_family_continuity_score"],
        ),
        "phase_transition_without_peak_family_support": (
            "A transition was detected without enough peak-family support.",
            ["peak_family_count", "peak_family_continuity_score"],
        ),
        "crystallinity_trend_without_peak_support": (
            "Xc trend is being interpreted without enough peak support behind it.",
            ["Xc_peak_support_ratio", "Xc_trend_support_score"],
        ),
        "crystallinity_jump_single_frame": (
            "Xc changes too sharply in a single frame to be treated as a stable trend.",
            ["crystallinity_jump_single_frame_count", "Xc_values"],
        ),
        "crystallinity_background_driven": (
            "Xc appears too sensitive to background partitioning or missing peak support.",
            ["Xc_background_sensitivity", "frame_low_conf_count"],
        ),
        "crystallinity_trend_conflicts_with_peak_area": (
            "Xc trend conflicts with the peak-area trend and needs review.",
            ["Xc_values", "peak_area_sum"],
        ),
        "crystallinity_outside_physical_range": (
            "Xc values go outside the physical range and should not be promoted.",
            ["Xc_values"],
        ),
        "melting_trend_without_peak_disappearance": (
            "Melting-like Xc drop does not line up with peak disappearance.",
            ["peak_family_tracks", "peak_disappearance_temperatures"],
        ),
        "cold_crystallization_without_new_peak_support": (
            "Cold-crystallisation-like Xc rise does not line up with new peak birth.",
            ["new_peak_birth_temperatures", "Xc_transition_candidates"],
        ),
        "amorphous_partition_unstable": (
            "Crystallinity still depends too much on the amorphous partition.",
            ["background_method", "amorphous_subtraction", "amorphous_n_peaks"],
        ),
        "peak_width_nonphysical": (
            "Peak widths look too broad or degenerate for a paper-grade WAXS fit.",
            ["peak_function", "smooth_window"],
        ),
        "offset_sensitive_solution": (
            "2theta offset is still steering the solution and should be checked first.",
            ["two_theta_offset"],
        ),
        "crystallinity_without_peak_support": (
            "Xc is being reported without enough peak support behind it.",
            ["peak_distance", "max_peaks", "amorphous_subtraction"],
        ),
        "size_without_multi_peak_support": (
            "Scherrer size needs at least two resolved peaks to stay trustworthy.",
            ["peak_distance", "max_peaks"],
        ),
        "scherrer_trend_without_multi_peak_support": (
            "Scherrer trend is being interpreted without repeated multi-peak support.",
            ["D_support_peak_count", "D_support_family_count"],
        ),
        "scherrer_jump_single_frame": (
            "Scherrer size changes too abruptly in a single frame.",
            ["D_jump_single_frame_count", "D_jump_single_frame_indices"],
        ),
        "scherrer_dominated_by_peak_width_noise": (
            "Scherrer trend is being driven more by peak-width noise than by a stable size change.",
            ["D_slope_distribution", "FWHM_values_by_family"],
        ),
        "scherrer_instrument_broadening_unresolved": (
            "Instrument broadening is not clearly modeled for the Scherrer result.",
            ["instrument_broadening_present", "caglioti_U", "caglioti_V", "caglioti_W"],
        ),
        "scherrer_conflicts_with_peak_family_tracking": (
            "Scherrer trend does not agree with the peak-family tracking story.",
            ["peak_family_continuity_score", "FWHM_values_by_family"],
        ),
        "scherrer_unphysical_temperature_trend": (
            "Scherrer trend is too oscillatory to be treated as physically stable.",
            ["D_values_nm", "D_trend_monotonicity"],
        ),
        "fit_quality_vs_phys": (
            "Fit score and physical support still need to agree before trust rises.",
            ["peak_function", "amorphous_subtraction"],
        ),
    }

    config_snapshot = validation.get("config_snapshot", {})
    if not isinstance(config_snapshot, dict):
        config_snapshot = {}

    symptom_list: list[dict[str, Any]] = []
    triggered = {
        str(item.get("name", "") or "").strip(): item
        for item in constraints
        if isinstance(item, dict) and item.get("triggered")
    }

    for name, item in triggered.items():
        spec = symptom_specs.get(name)
        if not spec:
            continue
        summary, target_params = spec
        observed = item.get("observed")

        if name == "offset_sensitive_solution" and _clean_float(observed) is None:
            observed = _clean_float(output.get("two_theta_offset", config_snapshot.get("two_theta_offset")))
        if name == "amorphous_partition_unstable" and observed is None:
            observed = {
                "Xc_method": output.get("Xc_method"),
                "amorphous_subtraction": output.get("amorphous_subtraction", config_snapshot.get("amorphous_subtraction")),
                "amorphous_n_peaks": output.get("amorphous_n_peaks", config_snapshot.get("amorphous_n_peaks")),
            }

        symptom_list.append(
            {
                "name": name,
                "summary": summary,
                "severity": str(item.get("severity", "") or "").strip() or "WARN",
                "source": "WAXS",
                "target_params": target_params,
                "observed": observed,
            }
        )

    waxs_residual_symptom_map: dict[str, tuple[str, list[str], list[str]]] = {
        "peak_position_bias": (
            "Peak positions are shifted relative to the observed profile.",
            ["two_theta_offset", "peak_function", "peak_distance"],
            ["peak positions should converge", "residual_type should move toward random"],
        ),
        "peak_count_underfit": (
            "The current peak family misses supported structure.",
            ["peak_distance", "max_peaks"],
            ["peak count should rise", "supporting peak regions should narrow"],
        ),
        "peak_count_overfit": (
            "The current peak family is too crowded for the observed structure.",
            ["max_peaks", "peak_distance"],
            ["peak count should fall", "peak family should simplify"],
        ),
        "amorphous_background_bias": (
            "Crystallinity is still too sensitive to halo/background partitioning.",
            ["background_method", "amorphous_subtraction", "amorphous_n_peaks"],
            ["background-related residuals should weaken", "crystallinity should stop depending on halo shape"],
        ),
        "peak_width_mismatch": (
            "Peak shoulders and cores disagree, suggesting a shape mismatch.",
            ["peak_function", "smooth_window"],
            ["shoulders and peak core should agree better", "peak widths should stabilize"],
        ),
        "low_angle_background_drift": (
            "Low-angle background is still drifting near the beamstop region.",
            ["background_method", "amorphous_subtraction", "two_theta_offset"],
            ["low-angle residuals should weaken", "max_residual_region should move away from beamstop"],
        ),
    }

    residual_type = str(residual.get("residual_type", "") or "").strip().lower()
    if residual_type in waxs_residual_symptom_map:
        summary, target_params, expected_change = waxs_residual_symptom_map[residual_type]
        symptom_list.append(
            {
                "name": residual_type,
                "summary": summary,
                "severity": "WARN",
                "source": "WAXS_residual",
                "target_params": target_params,
                "observed": {
                    "residual_type": residual_type,
                    "max_residual_region": residual.get("max_residual_region", "unknown"),
                },
                "expected_evidence_change": expected_change,
            }
        )

    return symptom_list


__all__ = ["_waxs_symptoms_from_constraints"]
