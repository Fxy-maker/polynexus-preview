from __future__ import annotations

import numpy as np

from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.waxs_temperature import WAXSTempResult


def test_waxs_temperature_result_parameters_include_axis_metadata() -> None:
    result = WAXSTempResult()
    result.temperatures = [170.0, 185.0, 195.0, 205.0]
    result.Xc_vs_T = [0.10, 0.08, 0.05, 0.02]

    params = result.parameters

    assert params["condition_label"] == "Temperature"
    assert params["condition_source"] == "filename"
    assert params["condition_confidence"] >= 0.8
    assert params["condition_continuity_score"] >= 0.8
    assert params["temperature_missing_count"] == 0
    assert params["temperature_duplicate_count"] == 0
    assert params["temperature_monotonic"] is True
    assert params["sequence_direction"] == "heating"
    assert params["temperature_axis_ready"] is True


def test_waxs_temperature_analysis_evidence_exposes_sequence_evidence() -> None:
    output = {
        "n_peaks": 2,
        "peak_count": 2,
        "peaks": [
            {"two_theta": 20.0, "fwhm_deg": 1.4, "area": 120.0},
            {"two_theta": 24.0, "fwhm_deg": 1.2, "area": 95.0},
        ],
        "peak_positions": [20.0, 24.0],
        "peak_widths": [1.4, 1.2],
        "peak_areas": [120.0, 95.0],
        "Xc_pct": 0.12,
        "Xc_method": "peak_deconvolution",
        "D_Scherrer_nm": 3.2,
        "r_squared": 0.92,
        "condition_label": "Temperature",
        "condition_unit": "C",
        "condition_source": "filename",
        "condition_source_key": "filename_parser",
        "condition_source_text": "directory frame names",
        "condition_confidence": 0.94,
        "condition_missing_frames": 0,
        "condition_continuity_score": 0.93,
        "temperature_values": [170.0, 185.0, 195.0, 205.0],
        "temperature_min_C": 170.0,
        "temperature_max_C": 205.0,
        "temperature_missing_count": 0,
        "temperature_duplicate_count": 0,
        "temperature_monotonic": True,
        "temperature_step_median_C": 10.0,
        "temperature_step_spread": 0.0,
        "sequence_order_source": "filename_parser",
        "sequence_direction": "heating",
        "temperature_axis_confidence": 0.94,
    }

    evidence = build_analysis_evidence("WAXS", output, {}, {"config_snapshot": {"amorphous_subtraction": "polynomial"}})

    assert evidence.condition_evidence["condition_source"] == "filename"
    assert evidence.condition_evidence["condition_confidence"] == 0.94
    assert evidence.feature_evidence["sequence_evidence"]["temperature_axis_confidence"] == 0.94
    assert "temperature_axis_missing" not in evidence.constraint_summary["triggered_names"]["hard_fail"]
    assert "temperature_sequence_nonmonotonic" not in evidence.constraint_summary["triggered_names"]["soft_warn"]


def test_waxs_temperature_result_parameters_include_frame_evidence() -> None:
    result = WAXSTempResult(label="temp_series")
    result.temperatures = [170.0, 185.0, 195.0]
    result.results = [
        WAXSResult(
            label="frame_170",
            Xc_pct=0.18,
            D_Scherrer_nm=3.5,
            n_peaks=2,
            r_squared=0.95,
            peaks=[{"two_theta": 19.8, "fwhm_deg": 1.1}, {"two_theta": 23.5, "fwhm_deg": 1.0}],
        ),
        WAXSResult(
            label="frame_185",
            Xc_pct=np.nan,
            D_Scherrer_nm=np.nan,
            n_peaks=1,
            r_squared=0.78,
            peaks=[{"two_theta": 20.0, "fwhm_deg": 1.6}],
        ),
        WAXSResult(
            label="frame_195",
            Xc_pct=0.12,
            D_Scherrer_nm=3.1,
            n_peaks=2,
            r_squared=0.91,
            peaks=[{"two_theta": 20.2, "fwhm_deg": 1.2}, {"two_theta": 24.1, "fwhm_deg": 1.1}],
        ),
    ]

    params = result.parameters
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters=params,
        residual_pattern={"residual_type": "random", "summary": "series is stable enough for review"},
        validation_context={"config_snapshot": {"background_method": "polynomial", "amorphous_subtraction": "polynomial"}},
    ).to_dict()

    assert params["frame_count"] == 3
    assert params["frame_pass_count"] == 2
    assert params["frame_low_conf_count"] == 1
    assert params["dominant_frame_failure_type"] in {"fit_quality_low", "peak_count_underfit"}
    assert params["low_conf_frame_indices"] == [1]
    assert params["low_conf_temperature_values"] == [185.0]
    assert params["frame_evidence"][1]["frame_status"] == "fail"
    assert params["frame_evidence"][0]["frame_status"] == "pass"
    assert params["frame_constraint_summary"]["frame_count"] == 3
    assert params["frame_constraint_summary"]["valid_frame_count"] == 2
    assert params["frame_quality_distribution"]["median"] > 0.0
    assert params["D_support_peak_count"] == 2
    assert params["D_support_family_count"] >= 0
    assert len(params["D_confidence_by_frame"]) == 3
    assert params["D_confidence_by_frame"][0]["temperature_C"] == 170.0
    assert evidence["feature_evidence"]["frame_evidence"][1]["frame_status"] == "fail"
    assert evidence["feature_evidence"]["frame_summary_evidence"]["frame_count"] == 3
    assert evidence["feature_evidence"]["scherrer_trend_evidence"]["D_support_peak_count"] == 2
    assert "D_trend=" in evidence["summary"]
    assert "frames=3" in evidence["summary"]
    assert "low_conf_frames=1" in evidence["summary"]


def test_waxs_temperature_result_parameters_include_peak_family_evidence() -> None:
    result = WAXSTempResult(label="temp_series")
    result.temperatures = [170.0, 185.0, 195.0, 205.0]
    result.results = [
        WAXSResult(
            label="frame_170",
            Xc_pct=0.18,
            D_Scherrer_nm=3.5,
            n_peaks=2,
            r_squared=0.95,
            peaks=[
                {"two_theta": 19.8, "fwhm_deg": 1.1, "area": 120.0},
                {"two_theta": 23.5, "fwhm_deg": 1.0, "area": 95.0},
            ],
        ),
        WAXSResult(
            label="frame_185",
            Xc_pct=0.17,
            D_Scherrer_nm=3.4,
            n_peaks=3,
            r_squared=0.94,
            peaks=[
                {"two_theta": 19.9, "fwhm_deg": 1.1, "area": 118.0},
                {"two_theta": 23.6, "fwhm_deg": 1.0, "area": 93.0},
                {"two_theta": 28.4, "fwhm_deg": 0.9, "area": 42.0},
            ],
        ),
        WAXSResult(
            label="frame_195",
            Xc_pct=0.16,
            D_Scherrer_nm=3.3,
            n_peaks=3,
            r_squared=0.93,
            peaks=[
                {"two_theta": 20.0, "fwhm_deg": 1.2, "area": 116.0},
                {"two_theta": 23.8, "fwhm_deg": 1.1, "area": 91.0},
                {"two_theta": 28.5, "fwhm_deg": 0.9, "area": 41.0},
            ],
        ),
        WAXSResult(
            label="frame_205",
            Xc_pct=0.15,
            D_Scherrer_nm=3.2,
            n_peaks=2,
            r_squared=0.92,
            peaks=[
                {"two_theta": 20.1, "fwhm_deg": 1.2, "area": 114.0},
                {"two_theta": 23.9, "fwhm_deg": 1.1, "area": 89.0},
            ],
        ),
    ]

    params = result.parameters
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters=params,
        residual_pattern={"residual_type": "random", "summary": "series is stable enough for review"},
        validation_context={"config_snapshot": {"background_method": "polynomial", "amorphous_subtraction": "polynomial"}},
    ).to_dict()

    family = evidence["feature_evidence"]["peak_family_evidence"]

    assert params["peak_family_assignment_method"] == "nearest_position_continuity"
    assert params["peak_family_count"] == 3
    assert params["peak_family_identity_swap_count"] == 0
    assert params["peak_family_missing_frame_count"] == 2
    assert len(params["new_peak_birth_temperatures"]) == 3
    assert 185.0 in params["new_peak_birth_temperatures"]
    assert len(params["peak_family_tracks"]) == 3
    assert family["peak_family_count"] == 3
    assert family["peak_family_continuity_score"] > 0.5
    assert params["peak_family_tracks"][2]["fragmented"] is True
    assert "peak_families=3" in evidence["summary"]
    assert "family_continuity=" in evidence["summary"]


def test_waxs_temperature_result_parameters_include_crystallinity_trend_evidence() -> None:
    result = WAXSTempResult(label="temp_series")
    result.temperatures = [170.0, 185.0, 195.0, 205.0]
    result.results = [
        WAXSResult(
            label="frame_170",
            Xc_pct=0.18,
            D_Scherrer_nm=3.5,
            n_peaks=2,
            r_squared=0.95,
            peaks=[
                {"two_theta": 19.8, "fwhm_deg": 1.1, "area": 120.0},
                {"two_theta": 23.5, "fwhm_deg": 1.0, "area": 95.0},
            ],
        ),
        WAXSResult(
            label="frame_185",
            Xc_pct=0.16,
            D_Scherrer_nm=3.4,
            n_peaks=2,
            r_squared=0.94,
            peaks=[
                {"two_theta": 19.9, "fwhm_deg": 1.1, "area": 116.0},
                {"two_theta": 23.6, "fwhm_deg": 1.0, "area": 91.0},
            ],
        ),
        WAXSResult(
            label="frame_195",
            Xc_pct=0.14,
            D_Scherrer_nm=3.3,
            n_peaks=2,
            r_squared=0.93,
            peaks=[
                {"two_theta": 20.0, "fwhm_deg": 1.2, "area": 112.0},
                {"two_theta": 23.8, "fwhm_deg": 1.1, "area": 87.0},
            ],
        ),
        WAXSResult(
            label="frame_205",
            Xc_pct=0.12,
            D_Scherrer_nm=3.2,
            n_peaks=2,
            r_squared=0.92,
            peaks=[
                {"two_theta": 20.1, "fwhm_deg": 1.2, "area": 108.0},
                {"two_theta": 23.9, "fwhm_deg": 1.1, "area": 84.0},
            ],
        ),
    ]

    params = result.parameters
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters=params,
        residual_pattern={"residual_type": "random", "summary": "series is stable enough for review"},
        validation_context={"config_snapshot": {"background_method": "polynomial", "amorphous_subtraction": "polynomial"}},
    ).to_dict()

    trend = evidence["feature_evidence"]["trend_evidence"]

    assert params["Xc_values"] == [0.18, 0.16, 0.14, 0.12]
    assert params["Xc_trend_monotonicity"] == "decreasing"
    assert params["Xc_peak_support_ratio"] == 1.0
    assert params["Xc_background_sensitivity"] == 0.0
    assert params["Xc_trend_support_score"] > 0.7
    assert trend["Xc_trend_support_score"] == params["Xc_trend_support_score"]
    assert trend["Xc_trend_monotonicity"] == "decreasing"
    assert trend["crystallinity_jump_single_frame_count"] == 0
    assert "xc_trend=" in evidence["summary"]
    assert "crystallinity_trend_without_peak_support" not in evidence["constraint_summary"]["triggered_names"]["soft_warn"]


def test_waxs_temperature_result_parameters_include_transition_support_evidence() -> None:
    result = WAXSTempResult(label="temp_series")
    result.temperatures = [170.0, 185.0, 195.0, 205.0]
    result.results = [
        WAXSResult(
            label="frame_170",
            Xc_pct=0.18,
            D_Scherrer_nm=3.5,
            n_peaks=2,
            r_squared=0.95,
            peaks=[
                {"two_theta": 19.8, "fwhm_deg": 1.1, "area": 120.0},
                {"two_theta": 23.5, "fwhm_deg": 1.0, "area": 95.0},
            ],
        ),
        WAXSResult(
            label="frame_185",
            Xc_pct=0.17,
            D_Scherrer_nm=3.4,
            n_peaks=2,
            r_squared=0.94,
            peaks=[
                {"two_theta": 19.9, "fwhm_deg": 1.1, "area": 118.0},
                {"two_theta": 23.6, "fwhm_deg": 1.0, "area": 93.0},
            ],
        ),
        WAXSResult(
            label="frame_195",
            Xc_pct=0.31,
            D_Scherrer_nm=3.3,
            n_peaks=2,
            r_squared=0.93,
            peaks=[
                {"two_theta": 20.0, "fwhm_deg": 1.2, "area": 116.0},
                {"two_theta": 23.8, "fwhm_deg": 1.1, "area": 91.0},
            ],
        ),
        WAXSResult(
            label="frame_205",
            Xc_pct=0.29,
            D_Scherrer_nm=3.2,
            n_peaks=2,
            r_squared=0.92,
            peaks=[
                {"two_theta": 20.1, "fwhm_deg": 1.2, "area": 114.0},
                {"two_theta": 23.9, "fwhm_deg": 1.1, "area": 89.0},
            ],
        ),
    ]

    params = result.parameters
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters=params,
        residual_pattern={"residual_type": "random", "summary": "series is stable enough for review"},
        validation_context={"config_snapshot": {"background_method": "polynomial", "amorphous_subtraction": "polynomial"}},
    ).to_dict()

    transition = evidence["feature_evidence"]["transition_evidence"]

    assert params["transition_candidate_count"] >= 1
    assert params["transition_support_score"] > 0.0
    assert transition["transition_support_score"] == params["transition_support_score"]
    assert "transition_support=" in evidence["summary"]


def test_waxs_temperature_result_parameters_include_scherrer_trend_evidence() -> None:
    result = WAXSTempResult(label="temp_series")
    result.config_snapshot = {"caglioti_U": 0.12, "caglioti_V": 0.0, "caglioti_W": 0.0}
    result.temperatures = [170.0, 185.0, 195.0, 205.0]
    result.results = [
        WAXSResult(
            label="frame_170",
            Xc_pct=0.18,
            D_Scherrer_nm=12.5,
            n_peaks=2,
            r_squared=0.95,
            peaks=[
                {"two_theta": 19.8, "fwhm_deg": 0.9, "area": 120.0},
                {"two_theta": 23.5, "fwhm_deg": 0.8, "area": 95.0},
            ],
        ),
        WAXSResult(
            label="frame_185",
            Xc_pct=0.17,
            D_Scherrer_nm=12.1,
            n_peaks=2,
            r_squared=0.94,
            peaks=[
                {"two_theta": 19.9, "fwhm_deg": 0.92, "area": 118.0},
                {"two_theta": 23.6, "fwhm_deg": 0.81, "area": 93.0},
            ],
        ),
        WAXSResult(
            label="frame_195",
            Xc_pct=0.16,
            D_Scherrer_nm=11.7,
            n_peaks=2,
            r_squared=0.93,
            peaks=[
                {"two_theta": 20.0, "fwhm_deg": 0.94, "area": 116.0},
                {"two_theta": 23.8, "fwhm_deg": 0.82, "area": 91.0},
            ],
        ),
        WAXSResult(
            label="frame_205",
            Xc_pct=0.15,
            D_Scherrer_nm=11.3,
            n_peaks=2,
            r_squared=0.92,
            peaks=[
                {"two_theta": 20.1, "fwhm_deg": 0.95, "area": 114.0},
                {"two_theta": 23.9, "fwhm_deg": 0.83, "area": 89.0},
            ],
        ),
    ]

    params = result.parameters
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters=params,
        residual_pattern={"residual_type": "random", "summary": "series is stable enough for review"},
        validation_context={"config_snapshot": result.config_snapshot},
    ).to_dict()

    trend = evidence["feature_evidence"]["scherrer_trend_evidence"]

    assert params["instrument_broadening_present"] is True
    assert params["D_values_nm"] == [12.5, 12.1, 11.7, 11.3]
    assert params["D_trend_monotonicity"] == "decreasing"
    assert params["D_support_peak_count"] == 4
    assert params["D_trend_support_score"] > 0.5
    assert len(params["D_confidence_by_frame"]) == 4
    assert trend["D_trend_support_score"] == params["D_trend_support_score"]
    assert trend["instrument_broadening_present"] is True
    assert "scherrer_instrument_broadening_unresolved" not in evidence["constraint_summary"]["triggered_names"]["soft_warn"]
    assert "D_trend=" in evidence["summary"]
