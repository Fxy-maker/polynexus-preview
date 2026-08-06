from __future__ import annotations

from polynexus.core.saxs_batch_helpers import _build_batch_parameters_payload


def test_build_batch_parameters_payload_aggregates_batch_metadata() -> None:
    batch_rows = [
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 170.0,
            "condition_source": "folder",
            "condition_source_key": "temp_directory_label",
            "condition_source_text": "temperature_170",
            "condition_confidence": 0.70,
            "L_nm": 10.0,
            "lc_nm": 3.2,
            "lc_nm_raw": 3.0,
            "lc_nm_calibrated": 3.2,
            "L_nm_raw": 9.8,
            "Xc_raw": 0.320,
            "Xc_calibrated": 0.340,
            "lc_method": "calibrated",
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            "fallback_applied_fields": ["lc_nm_calibrated", "Xc_calibrated"],
            "raw_snapshot": {"structure": {"lc": 3.0}},
            "melting_window_status": "outside_window",
            "melting_window_reason": "stable_structure_support",
            "lc_reliability_status": "usable",
            "lc_reliability_reason": "stable_structure_support",
            "Q_star_rel": 1.0,
            "porod_slope": -3.1,
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": True,
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Temperature",
            "temperature_C": 195.0,
            "condition_source": "folder",
            "condition_source_key": "temp_directory_label",
            "condition_source_text": "temperature_170",
            "condition_confidence": 0.80,
            "L_nm": 9.7,
            "lc_nm": 1.1,
            "lc_nm_raw": 1.0,
            "lc_nm_calibrated": 1.1,
            "L_nm_raw": 9.5,
            "Xc_raw": 0.280,
            "Xc_calibrated": 0.290,
            "lc_method": "raw",
            "calibration_skipped_reason": "missing_reference_crystallinity",
            "melting_window_status": "within_window",
            "melting_window_reason": "near_sequence_melting_onset",
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "low_lc_confidence|within_melting_window",
            "Q_star_rel": 0.92,
            "porod_slope": -3.4,
            "paper_figure_candidate": False,
            "paper_conclusion_candidate": False,
        },
    ]

    payload = _build_batch_parameters_payload(
        batch_rows,
        base_params={"n_temperatures": 2, "paper_conclusion_ready": False},
    )

    assert payload["n_temperatures"] == 2
    assert payload["batch_frames"] == 2
    assert payload["condition_label"] == "Temperature"
    assert payload["condition_range"] == "170.0-195.0"
    assert payload["condition_source"] == "folder"
    assert payload["condition_source_key"] == "temp_directory_label"
    assert payload["condition_source_text"] == "temperature_170"
    assert payload["condition_confidence"] == 0.75
    assert payload["condition_continuity_score"] == 1.0
    assert payload["raw_structure_available"] is True
    assert payload["calibrated_fallback_active"] is True
    assert payload["calibrated_fallback_reason"] == "temperature_batch_lc_calibration"
    assert payload["fallback_applied_fields"] == ["Xc_calibrated", "lc_nm_calibrated"]
    assert payload["paper_figure_candidate"] is True
    assert payload["paper_conclusion_candidate"] is True
    assert payload["paper_conclusion_ready"] is True

    calibration_summary = payload["batch_calibration_summary"]
    assert calibration_summary["batch_rows"] == 2
    assert calibration_summary["fallback_rows"] == 1
    assert calibration_summary["calibration_skipped_rows"] == 1
    assert calibration_summary["calibration_skipped_reason"] == "missing_reference_crystallinity"
    assert calibration_summary["raw_structure_available"] is True
    assert calibration_summary["calibrated_fallback_reason"] == "temperature_batch_lc_calibration"
    assert calibration_summary["fallback_ratio"] == 0.5

    structure_summary = payload["batch_structure_summary"]
    assert structure_summary["usable_rows"] == 1
    assert structure_summary["diagnostic_only_rows"] == 1
    assert structure_summary["within_window_rows"] == 1
    assert structure_summary["dominant_melting_window_reason"] in {
        "stable_structure_support",
        "near_sequence_melting_onset",
    }
    assert structure_summary["dominant_lc_reliability_status"] in {"usable", "diagnostic_only"}

    assert payload["_batch_data"][0]["file"] == "frame_001.edf"
    assert payload["_batch_data"][1]["temperature_C"] == 195.0
    assert "lc_reliability_status" not in batch_rows[0] or batch_rows[0]["lc_reliability_status"] == "usable"


def test_strain_batch_payload_aggregates_canonical_invariant_names() -> None:
    payload = _build_batch_parameters_payload(
        [
            {
                "condition_label": "Strain",
                "strain_pct": 0.0,
                "invariant_Q_rel": 1.0,
            },
            {
                "condition_label": "Strain",
                "strain_pct": 20.0,
                "invariant_Q_rel": 0.9,
            },
        ],
        experiment_type="strain",
    )

    assert payload["invariant_Q_rel_mean"] == 0.95
    assert payload["invariant_Q_rel_span"] == 0.1
    assert "Q_star_rel_mean" not in payload
    assert "Q_star_rel_span" not in payload


def test_build_batch_parameters_payload_leaves_single_row_unwrapped() -> None:
    base_params = {"n_temperatures": 1, "T_range_C": "100-100"}
    batch_rows = [
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 100.0,
            "L_nm": 12.3,
        }
    ]

    payload = _build_batch_parameters_payload(batch_rows, base_params=base_params)

    assert payload == base_params
    assert "batch_frames" not in payload
    assert "_batch_data" not in payload


def test_build_batch_parameters_payload_infers_missing_lc_reliability() -> None:
    batch_rows = [
        {
            "file": "frame_001.edf",
            "condition_label": "Condition",
            "condition_value": 1.0,
            "L_nm": 12.0,
            "lc_nm": 1.1,
            "lc_confidence": 0.18,
            "lc_method": "tangent",
            "Q_star": 0.2,
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Condition",
            "condition_value": 2.0,
            "L_nm": 11.8,
            "lc_nm": 3.4,
            "lc_confidence": 0.72,
            "lc_method": "calibrated",
            "Q_star": 12.0,
        },
    ]

    payload = _build_batch_parameters_payload(batch_rows)

    first = payload["_batch_data"][0]
    summary = payload["batch_structure_summary"]

    assert first["lc_reliability_status"] == "diagnostic_only"
    assert "low_lc_confidence" in first["lc_reliability_reason"]
    assert "single_method_fragile" in first["lc_reliability_reason"]
    assert summary["diagnostic_only_rows"] == 1
    assert summary["usable_rows"] == 1
