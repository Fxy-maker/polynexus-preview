from __future__ import annotations

from polynexus.core.saxs_symptom_detector import detect_saxs_symptoms, symptom_bridge_lines


def test_detect_saxs_symptoms_flags_missing_axis_and_oscillation() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "batch_frames": 4,
            "condition_label": "Temperature",
            "condition_missing_frames": 4,
            "fit_regions": [
                {"region": "correlation", "peak_count": 12, "zero_crossings": 14},
            ],
        },
        residual_pattern={"residual_type": "noise"},
        condition_evidence={
            "condition_label": "Temperature",
            "condition_missing_frames": 4,
            "condition_confidence": 0.0,
        },
    )

    names = {item["name"] for item in symptoms}
    assert "condition_axis_missing" in names
    assert "idf_artifact_regular_spacing" in names

    bridge = symptom_bridge_lines(next(item for item in symptoms if item["name"] == "condition_axis_missing"))
    assert bridge[0].startswith("series_condition_axis_missing")


def test_detect_saxs_symptoms_flags_low_q_peak_and_method_disagreement() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "beam_stop_contaminated": True,
            "Q_star_valid": False,
            "q_peak_diff_pct": 3.4,
            "fit_regions": [
                {"region": "peak", "r_squared": 0.22, "rmse": 0.31},
            ],
            "L_bragg": 12.4,
            "L_corr_peak": 11.4,
            "L_best": 13.1,
        },
        residual_pattern={"residual_type": "peak_mismatch"},
        signal_evidence={"beam_stop_contaminated": True, "Q_star_valid": False},
        peak_evidence={"L_bragg": 12.4, "q_peak_diff_pct": 3.4},
        transform_evidence={"L_corr_peak": 11.4, "lc_tangent_nm": 4.1, "lc_gamma_min_nm": 4.7, "lc_idf_nm": 4.5},
        structure_evidence={"L_best": 13.1, "lc_confidence": 0.41, "lc_method": "tangent_warn"},
    )

    names = {item["name"] for item in symptoms}
    assert "beamstop_or_low_q_contamination" in names
    assert "peak_window_mismatch" in names
    assert "gamma_tangent_unstable" in names
    assert "multi_method_disagreement" in names


def test_detect_saxs_symptoms_flags_batch_mixing_and_axis_instability() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "batch_frames": 4,
            "condition_label": "Temperature",
            "condition_missing_frames": 1,
            "condition_continuity_score": 0.72,
            "_batch_data": [
                {"sample_name": "PA6", "temperature_C": 100.0},
                {"sample_name": "PA6", "temperature_C": 110.0},
                {"sample_name": "PET", "temperature_C": 120.0},
                {"sample_name": "PET", "temperature_C": None},
            ],
        },
        residual_pattern={"residual_type": "noise"},
        condition_evidence={
            "condition_label": "Temperature",
            "condition_missing_frames": 1,
            "condition_confidence": 0.68,
            "condition_continuity_score": 0.72,
        },
    )

    names = {item["name"] for item in symptoms}
    assert "condition_axis_unstable" in names
    assert "batch_mixed_samples" in names


def test_detect_saxs_symptoms_flags_temperature_fallback_conflict_chain() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "batch_frames": 3,
            "condition_label": "Temperature",
            "condition_missing_frames": 0,
            "condition_confidence": 0.9,
            "condition_continuity_score": 1.0,
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            "lc_method": "calibrated",
            "beam_stop_contaminated": True,
            "Q_star_valid": False,
            "mask_truncated": True,
            "L_bragg": 8.4,
            "L_corr_peak": 8.1,
            "L_best": 8.0,
            "lc_nm": 2.6,
            "la_nm": 5.4,
            "Xc": 0.25,
            "lc_nm_calibrated": 3.07,
            "la_nm_calibrated": 4.93,
            "Xc_calibrated": 0.365,
            "_batch_data": [
                {
                    "file": "frame_001.edf",
                    "temperature_C": 100.0,
                    "lc_nm": 2.6,
                    "la_nm": 5.4,
                    "Xc": 0.25,
                    "lc_nm_calibrated": 3.07,
                    "la_nm_calibrated": 4.93,
                    "Xc_calibrated": 0.365,
                    "calibrated_fallback_active": True,
                    "raw_snapshot": {
                        "structure": {"lc": 2.6, "la": 5.4, "phi_c": 0.25, "L": 8.0}
                    },
                },
                {
                    "file": "frame_002.edf",
                    "temperature_C": 110.0,
                    "lc_nm": 3.4,
                    "la_nm": 4.6,
                    "Xc": 0.45,
                    "lc_nm_calibrated": 3.07,
                    "la_nm_calibrated": 4.93,
                    "Xc_calibrated": 0.381,
                    "calibrated_fallback_active": True,
                    "raw_snapshot": {
                        "structure": {"lc": 3.4, "la": 4.6, "phi_c": 0.45, "L": 8.05}
                    },
                },
                {
                    "file": "frame_003.edf",
                    "temperature_C": 120.0,
                    "lc_nm": 4.0,
                    "la_nm": 4.0,
                    "Xc": 0.30,
                    "lc_nm_calibrated": 3.07,
                    "la_nm_calibrated": 4.88,
                    "Xc_calibrated": 0.386,
                    "calibrated_fallback_active": True,
                    "raw_snapshot": {
                        "structure": {"lc": 4.0, "la": 4.0, "phi_c": 0.30, "L": 7.95}
                    },
                },
            ],
        },
        residual_pattern={"residual_type": "noise"},
        structure_evidence={
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
        },
        batch_evidence={
            "batch_frames": 3,
            "sample_files": ["frame_001.edf", "frame_002.edf", "frame_003.edf"],
        },
        condition_evidence={
            "condition_label": "Temperature",
            "condition_missing_frames": 0,
            "condition_confidence": 0.9,
            "condition_continuity_score": 1.0,
        },
    )

    names = {item["name"] for item in symptoms}
    assert "temperature_calibration_fallback_active" in names
    assert "batch_summary_conflicts_with_frame_evidence" in names
    assert "thickness_chain_unreliable" in names


def test_detect_saxs_symptoms_flags_strain_void_and_orientation_conflicts() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "batch_frames": 4,
            "condition_label": "strain",
            "Q_star_rel_mean": 1.08,
            "Q_star_rel_span": 0.11,
            "phi_void_mean": 0.034,
            "phi_void_span": 0.017,
            "f_Herman_mean": 0.21,
            "f_Herman_span": 0.54,
            "porod_slope_mean": -3.18,
            "void_detected_frames": 3,
            "has_voids_row_count": 3,
            "L_bragg": 11.8,
            "L_corr_peak": 9.9,
            "L_best": 12.1,
            "Q_star_valid": False,
            "mask_truncated": True,
        },
        residual_pattern={"residual_type": "noise"},
        condition_evidence={
            "condition_label": "strain",
            "condition_confidence": 0.81,
        },
    )

    names = {item["name"] for item in symptoms}
    assert "low_q_void_dominant" in names
    assert "strain_void_lamellar_conflict" in names
    assert "lamellar_anchor_lost_under_strain" in names
    assert "qstar_rel_without_lamellar_support" in names
    assert "orientation_shift_breaks_lamellar_comparison" in names


def test_detect_saxs_symptoms_flags_diagnostic_lc_without_melting_proof() -> None:
    symptoms = detect_saxs_symptoms(
        output_parameters={
            "batch_frames": 2,
            "condition_label": "Temperature",
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "low_lc_confidence|near_melting_onset",
            "melting_window_status": "near_onset",
            "batch_structure_summary": {
                "diagnostic_only_rows": 1,
                "within_window_rows": 0,
                "near_onset_rows": 1,
                "dominant_lc_reliability_status": "diagnostic_only",
                "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
                "dominant_melting_window_status": "near_onset",
            },
            "_batch_data": [
                {
                    "file": "frame_170.edf",
                    "temperature_C": 170.0,
                    "melting_window_status": "outside_window",
                    "lc_reliability_status": "usable",
                },
                {
                    "file": "frame_195.edf",
                    "temperature_C": 195.0,
                    "melting_window_status": "near_onset",
                    "lc_reliability_status": "diagnostic_only",
                },
            ],
        },
        residual_pattern={"residual_type": "noise"},
        structure_evidence={
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "low_lc_confidence|near_melting_onset",
            "melting_window_status": "near_onset",
        },
        batch_evidence={
            "batch_frames": 2,
            "batch_structure_summary": {
                "diagnostic_only_rows": 1,
                "within_window_rows": 0,
                "near_onset_rows": 1,
                "dominant_lc_reliability_status": "diagnostic_only",
                "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
                "dominant_melting_window_status": "near_onset",
            },
        },
    )

    names = {item["name"] for item in symptoms}
    assert "diagnostic_lc_frames_present" in names
    assert "temperature_sequence_near_melting_window" in names
    assert "lc_unreliable_without_melting_proof" in names

    bridge = symptom_bridge_lines(next(item for item in symptoms if item["name"] == "lc_unreliable_without_melting_proof"))
    assert bridge[0].startswith("lc_unreliable_without_melting_proof")
