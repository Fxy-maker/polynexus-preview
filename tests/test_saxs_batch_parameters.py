from __future__ import annotations

import numpy as np
from types import SimpleNamespace

from polynexus.core.engine import get_engine
from polynexus.core.saxs_batch_helpers import (
    build_static_batch_metric_evidence,
    copy_saxs_quality_evidence,
)
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_output import _result_to_params_dict


def test_saxs_batch_get_parameters_returns_full_batch_payload() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 100.0,
            "condition_source": "header",
            "condition_confidence": 0.9,
            "L_nm": 12.3,
            "lc_nm": 4.1,
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Temperature",
            "temperature_C": 110.0,
            "condition_source": "header",
            "condition_confidence": 0.9,
            "L_nm": 12.8,
            "lc_nm": 4.4,
        },
        {
            "file": "frame_003.edf",
            "condition_label": "Temperature",
            "temperature_C": 120.0,
            "condition_source": "header",
            "condition_confidence": 0.9,
            "L_nm": 13.1,
            "lc_nm": 4.6,
        },
    ]

    params = engine.get_parameters()

    assert params["batch_frames"] == 3
    assert len(params["_batch_data"]) == 3
    assert params["_batch_data"][0]["file"] == "frame_001.edf"
    assert params["_batch_data"][-1]["temperature_C"] == 120.0
    assert params["condition_label"] == "Temperature"
    assert params["condition_range"] == "100.0-120.0"
    assert params["condition_source"] == "header"
    assert params["condition_confidence"] == 0.9
    assert params["condition_continuity_score"] == 1.0


def test_copy_saxs_quality_evidence_copies_only_present_contract_fields() -> None:
    source = SimpleNamespace(
        data_quality_report={"level": "Diagnostic"},
        guinier_evidence={"metric": {"level": "Trend"}},
        metric_evidence={"porod": {"level": "Trend"}},
        quality_flag="WARN",
    )

    copied = copy_saxs_quality_evidence(source)

    assert copied == {
        "data_quality_report": {"level": "Diagnostic"},
        "guinier_evidence": {"metric": {"level": "Trend"}},
        "metric_evidence": {"porod": {"level": "Trend"}},
    }
    assert copied["metric_evidence"] is not source.metric_evidence


def test_build_static_batch_metric_evidence_keeps_missing_frame_counts() -> None:
    analyses = [
        SimpleNamespace(metric_evidence={"porod": {"level": "Trend"}}),
        None,
        SimpleNamespace(metric_evidence={"porod": {"level": "Diagnostic"}}),
    ]

    summary = build_static_batch_metric_evidence(analyses)

    assert summary["porod"]["frame_count"] == 3
    assert summary["porod"]["evidence_frame_count"] == 2
    assert summary["porod"]["missing_frame_count"] == 1
    assert summary["porod"]["level"] == "Diagnostic"
    assert "series_metric_missing_frames" in summary["porod"]["reason_codes"]
    assert summary["porod"]["source_ref"] == "saxs_static_batch.metric_evidence"


def test_saxs_static_single_get_parameters_transports_existing_evidence() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    from polynexus.core.saxs_engine.core import SAXSResult, StructureParams

    evidence = {"porod": {"level": "Trend", "value": 1.2}}
    result = SAXSResult(
        structure=StructureParams(L=12.0, lc=4.0, la=8.0, phi_c=1 / 3),
        data_quality_report={"level": "Trend"},
        guinier_evidence={"metric": {"level": "Trend", "rg_nm": 5.0}},
        metric_evidence=evidence,
    )
    engine._analysis = result  # type: ignore[attr-defined]
    before = result.metric_evidence.copy()

    params = engine.get_parameters()

    assert params["L_nm"] == 12.0
    assert params["data_quality_report"] == {"level": "Trend"}
    assert params["guinier_evidence"]["metric"]["rg_nm"] == 5.0
    assert params["metric_evidence"] == evidence
    assert params["metric_evidence"] is not evidence
    assert result.metric_evidence == before


def test_saxs_static_batch_get_parameters_preserves_aligned_frame_evidence() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    from polynexus.core.saxs_engine.core import SAXSResult, StructureParams

    first = SAXSResult(
        structure=StructureParams(L=12.0),
        metric_evidence={"porod": {"level": "Trend", "value": 1.0}},
    )
    third = SAXSResult(
        structure=StructureParams(L=13.0),
        metric_evidence={"porod": {"level": "Diagnostic", "value": 0.5}},
    )
    engine._batch_results = [first, None, third]  # type: ignore[attr-defined]
    engine._batch_params = [  # type: ignore[attr-defined]
        {"file": "frame_001.dat", "L_nm": 12.0},
        {"file": "frame_002.dat", "L_nm": None},
        {"file": "frame_003.dat", "L_nm": 13.0},
    ]

    params = engine.get_parameters()

    rows = params["_batch_data"]
    assert rows[0]["metric_evidence"]["porod"]["value"] == 1.0
    assert "metric_evidence" not in rows[1]
    assert rows[2]["metric_evidence"]["porod"]["level"] == "Diagnostic"
    assert params["metric_evidence_scope"] == "static_batch"
    assert params["metric_evidence"]["porod"]["frame_count"] == 3
    assert params["metric_evidence"]["porod"]["missing_frame_count"] == 1
    assert params["metric_evidence"]["porod"]["level"] == "Diagnostic"


def test_saxs_batch_export_row_keeps_status_fields() -> None:
    result = SimpleNamespace(
        label="frame_001",
        structure=None,
        long_period=None,
        final_parameters={},
        lc_method="raw",
        calibrated_fallback_active=False,
        calibration_skipped_reason="missing_reference_crystallinity",
        melting_window_status="within_window",
        melting_window_reason="near_sequence_melting_onset",
        lc_reliability_status="diagnostic_only",
        lc_reliability_reason="low_lc_confidence|within_melting_window",
        quality_flag="WARN",
        validation_summary="status fields should export",
        Q_star_valid=True,
        q_peak_snr=3.2,
        effective_q_min=0.123,
    )

    row = _result_to_params_dict(result)

    assert row["label"] == "frame_001"
    assert row["lc_method"] == "raw"
    assert row["calibration_skipped_reason"] == "missing_reference_crystallinity"
    assert row["melting_window_status"] == "within_window"
    assert row["lc_reliability_status"] == "diagnostic_only"


def test_saxs_single_batch_row_does_not_get_wrapped() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 100.0,
            "L_nm": 12.3,
        }
    ]

    params = engine.get_parameters()

    assert "batch_frames" not in params
    assert "_batch_data" not in params
    assert params["L_nm"] == 12.3


def test_saxs_batch_payload_aggregates_condition_axis_recovery_metadata() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 100.0,
            "condition_source": "folder",
            "condition_source_key": "temp_directory_label",
            "condition_source_text": "temperature_100",
            "condition_confidence": 0.7,
            "L_nm": 12.3,
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Temperature",
            "temperature_C": None,
            "condition_source": "folder",
            "condition_source_key": "temp_directory_label",
            "condition_source_text": "temperature_100",
            "condition_confidence": 0.65,
            "L_nm": 12.8,
        },
        {
            "file": "frame_003.edf",
            "condition_label": "Temperature",
            "temperature_C": 120.0,
            "condition_source": "header",
            "condition_source_key": "temperature",
            "condition_source_text": "temperature",
            "condition_confidence": 0.9,
            "L_nm": 13.1,
        },
    ]

    params = engine.get_parameters()

    assert params["condition_source"] == "folder"
    assert params["condition_source_key"] == "temp_directory_label"
    assert params["condition_source_text"] == "temperature_100"
    assert params["condition_confidence"] == 0.75
    assert params["condition_missing_frames"] == 1
    assert params["condition_continuity_score"] == 1.0
    assert params["_batch_data"][0]["condition_source"] == "folder"
    assert params["_batch_data"][0]["condition_source_key"] == "temp_directory_label"
    assert params["_batch_data"][0]["condition_source_text"] == "temperature_100"
    assert params["_batch_data"][0]["condition_confidence"] == 0.7


def test_saxs_temperature_batch_exposes_raw_and_calibrated_layers() -> None:
    engine = get_engine("saxs", config=SAXSConfig(experiment_type="temperature"))
    assert engine is not None

    from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams

    raw_result = SAXSResult(
        label="frame_001",
        long_period=LongPeriodResult(L_best=10.0, L_confidence=0.42, L_bragg=10.1, L_lorentz=9.8, L_corr_peak=10.2, method_used="bragg"),
        structure=StructureParams(L=10.0, lc=3.2, la=6.8, phi_c=0.32, confidence_lc=0.31, Q_invariant=18.2),
    )
    engine._batch_results = [raw_result]  # type: ignore[attr-defined]
    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 100.0,
            "L_nm": 10.0,
            "lc_nm": 3.2,
            "la_nm": 6.8,
            "Xc": 0.32,
            "lc_confidence": 0.31,
            "lc_nm_calibrated": 3.5,
            "la_nm_calibrated": 6.5,
            "Xc_calibrated": 0.35,
            "lc_confidence_calibrated": 0.5,
            "Q_star": 18.2,
            "lc_method": "calibrated",
        }
    ]

    engine._apply_batch_params_to_results()  # type: ignore[attr-defined]
    params = engine.get_parameters()

    assert params["lc_nm_raw"] == 3.2
    assert params["la_nm_raw"] == 6.8
    assert params["Xc_raw"] == 0.32
    assert params["calibrated_fallback_active"] is True
    assert params["calibrated_fallback_reason"] == "temperature_batch_lc_calibration"
    assert params["fallback_applied_fields"] == ["lc_nm_calibrated", "la_nm_calibrated", "Xc_calibrated", "lc_confidence_calibrated"]
    assert params["lc_nm"] == 3.2
    assert params["lc_nm_calibrated"] == 3.5
    assert params["raw_structure_available"] is True
    assert params["raw_snapshot"]["structure"]["lc"] == 3.2


def test_saxs_reference_crystallinity_requires_explicit_config_value() -> None:
    engine = get_engine("saxs", config=SAXSConfig(experiment_type="temperature"))
    assert engine is not None

    ref_xc, reason = engine._reference_crystallinity()  # type: ignore[attr-defined]
    assert ref_xc is None
    assert reason == "missing_reference_crystallinity"

    engine.cfg.crystallinity = 0.42  # type: ignore[attr-defined]
    ref_xc, reason = engine._reference_crystallinity()  # type: ignore[attr-defined]
    assert ref_xc == 0.42
    assert reason == ""


def test_saxs_batch_payload_reports_skipped_calibration_reason() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 100.0,
            "L_nm": 10.0,
            "lc_nm": 3.2,
            "Xc": 0.32,
            "lc_method": "raw",
            "calibration_skipped_reason": "missing_reference_crystallinity",
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Temperature",
            "temperature_C": 110.0,
            "L_nm": 10.2,
            "lc_nm": 3.3,
            "Xc": 0.323,
            "lc_method": "raw",
            "calibration_skipped_reason": "missing_reference_crystallinity",
        },
    ]

    params = engine.get_parameters()

    summary = params["batch_calibration_summary"]
    assert summary["calibration_skipped_rows"] == 2
    assert summary["calibration_skipped_reason"] == "missing_reference_crystallinity"
    assert params["_batch_data"][0]["lc_method"] == "raw"
    assert "lc_nm_calibrated" not in params["_batch_data"][0]


def test_saxs_batch_payload_reports_lc_status_summary() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Temperature",
            "temperature_C": 170.0,
            "L_nm": 10.0,
            "lc_nm": 3.2,
            "lc_method": "raw",
            "melting_window_status": "outside_window",
            "lc_reliability_status": "usable",
            "lc_reliability_reason": "stable_structure_support",
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Temperature",
            "temperature_C": 195.0,
            "L_nm": 9.7,
            "lc_nm": 1.1,
            "lc_method": "raw",
            "melting_window_status": "within_window",
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "low_lc_confidence|within_melting_window",
        },
    ]

    params = engine.get_parameters()

    structure_summary = params["batch_structure_summary"]
    assert structure_summary["diagnostic_only_rows"] == 1
    assert structure_summary["within_window_rows"] == 1
    assert structure_summary["dominant_lc_reliability_status"] in {"usable", "diagnostic_only"}
    assert params["lc_reliability_status"] in {"usable", "diagnostic_only"}


def test_static_saxs_batch_infers_lc_reliability_for_fragile_single_frame_rows() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
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

    params = engine.get_parameters()

    first = params["_batch_data"][0]
    summary = params["batch_structure_summary"]

    assert first["lc_reliability_status"] == "diagnostic_only"
    assert "low_lc_confidence" in first["lc_reliability_reason"]
    assert "single_method_fragile" in first["lc_reliability_reason"]
    assert summary["diagnostic_only_rows"] == 1
    assert summary["usable_rows"] == 1


def test_saxs_apply_batch_params_keeps_failed_frame_alignment() -> None:
    engine = get_engine("saxs", config=SAXSConfig(experiment_type="temperature"))
    assert engine is not None

    from polynexus.core.saxs_engine.core import LongPeriodResult, SAXSResult, StructureParams

    second_result = SAXSResult(
        label="frame_002",
        long_period=LongPeriodResult(L_best=10.2, L_confidence=0.44, L_bragg=10.2),
        structure=StructureParams(L=10.2, lc=3.3, la=6.9, phi_c=0.323, confidence_lc=0.33),
    )
    engine._batch_results = [None, second_result]  # type: ignore[attr-defined]
    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "temperature_C": 100.0,
            "L_nm": None,
            "lc_nm": None,
            "lc_method": "raw",
            "calibration_skipped_reason": "missing_reference_crystallinity",
        },
        {
            "file": "frame_002.edf",
            "temperature_C": 110.0,
            "L_nm": 10.2,
            "lc_nm": 3.3,
            "Xc": 0.323,
            "lc_method": "raw",
            "calibration_skipped_reason": "missing_reference_crystallinity",
        },
    ]

    engine._apply_batch_params_to_results()  # type: ignore[attr-defined]
    params = engine.get_parameters()

    assert params["_batch_data"][0]["file"] == "frame_001.edf"
    assert params["_batch_data"][1]["file"] == "frame_002.edf"
    assert params["_batch_data"][1]["raw_snapshot"]["structure"]["lc"] == 3.3


def test_saxs_strain_batch_payload_exposes_raw_and_effective_layers() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    engine._batch_params = [  # type: ignore[attr-defined]
        {
            "file": "frame_001.edf",
            "condition_label": "Strain",
            "strain_pct": 8.0,
            "L_nm": 12.0,
            "L_nm_measured": 12.0,
            "Q_star_abs": 18.2,
            "Q_star_rel": 1.0,
            "lc_nm_raw": 2.5,
            "la_nm_raw": 9.5,
            "Xc_raw": 0.208,
            "lc_nm": 2.6,
            "la_nm": 9.4,
            "Xc": 0.217,
            "lc_nm_effective": 2.6,
            "la_nm_effective": 9.4,
            "Xc_effective": 0.217,
            "lamellar_interpretation_mode": "tangent_effective",
            "effective_param_reason": "tangent thickness anchored to the strain long period",
            "Q_star": 18.2,
            "Q_rel": 1.0,
            "lc_confidence": 0.5,
            "lc_method": "tangent_strain",
        },
        {
            "file": "frame_002.edf",
            "condition_label": "Strain",
            "strain_pct": 16.0,
            "L_nm": 12.4,
            "L_nm_measured": 12.4,
            "Q_star_abs": 17.7,
            "Q_star_rel": 0.97,
            "lc_nm_raw": 2.4,
            "la_nm_raw": 10.0,
            "Xc_raw": 0.194,
            "lc_nm": 2.7,
            "la_nm": 9.7,
            "Xc": 0.218,
            "lc_nm_effective": 2.7,
            "la_nm_effective": 9.7,
            "Xc_effective": 0.218,
            "lamellar_interpretation_mode": "tangent_effective_warn",
            "effective_param_reason": "tangent thickness accepted but Q* drift needs review",
            "Q_star": 17.7,
            "Q_rel": 0.97,
            "lc_confidence": 0.35,
            "lc_method": "tangent_strain_qstar_warn",
        }
    ]

    params = engine.get_parameters()

    assert params["batch_frames"] == 2
    assert params["_batch_data"][0]["Q_star_rel"] == 1.0
    assert params["_batch_data"][0]["lc_nm_raw"] == 2.5
    assert params["_batch_data"][0]["lc_nm_effective"] == 2.6
    assert params["_batch_data"][0]["lamellar_interpretation_mode"] == "tangent_effective"
    assert params["_batch_data"][1]["Q_star_rel"] == 0.97
    assert params["_batch_data"][1]["effective_param_reason"] == "tangent thickness accepted but Q* drift needs review"


def test_saxs_strain_get_parameters_surfaces_phase_and_reliability_summary() -> None:
    engine = get_engine("saxs")
    assert engine is not None

    from polynexus.core.saxs_engine.saxs_strain import StrainPhase, StrainPointResult, StrainSeriesResult

    engine._strain_result = StrainSeriesResult(  # type: ignore[attr-defined]
        strain_points=[
            StrainPointResult(
                strain_pct=0.0,
                phase=StrainPhase.ELASTIC,
                Q_star=10.0,
                Q_star_rel=1.0,
                Q_star_normalized=1.0,
                confidence=0.82,
            ),
            StrainPointResult(
                strain_pct=8.0,
                phase=StrainPhase.PLASTIC_VOIDING,
                Q_star=10.4,
                Q_star_rel=1.04,
                Q_star_normalized=1.04,
                has_voids=True,
                phi_void=0.04,
                confidence=0.71,
            ),
            StrainPointResult(
                strain_pct=16.0,
                phase=StrainPhase.MICROFIBRILLATION,
                Q_star=10.9,
                Q_star_rel=1.09,
                Q_star_normalized=1.09,
                confidence=0.77,
            ),
        ],
        strains=np.asarray([0.0, 8.0, 16.0], dtype=float),
        Q_star_array=np.asarray([10.0, 10.4, 10.9], dtype=float),
        Q_star_rel_array=np.asarray([1.0, 1.04, 1.09], dtype=float),
        L_array=np.asarray([12.0, 11.8, 11.5], dtype=float),
        lc_array=np.asarray([2.5, 2.7, 2.8], dtype=float),
        la_array=np.asarray([9.5, 9.1, 8.7], dtype=float),
        f_herman_array=np.asarray([np.nan, np.nan, np.nan], dtype=float),
        phi_void_array=np.asarray([0.0, 0.04, 0.01], dtype=float),
    )
    engine._conditions = [0.0, 8.0, 16.0]  # type: ignore[attr-defined]
    engine._condition_confidences = [0.82, 0.71, 0.77]  # type: ignore[attr-defined]

    params = engine.get_parameters()

    assert params["phase_distribution"] == {"elastic": 1, "microfibrillation": 1, "plastic_voiding": 1}
    assert params["dominant_phase"] in {"elastic", "microfibrillation", "plastic_voiding"}
    assert params["strain_reliability_status"] in {"usable", "low_confidence"}
    assert "strain_axis_low_confidence" in params["strain_reliability_reason"] or "low_q_void_dominant" in params["strain_reliability_reason"]
    assert "phase_boundary_candidates" in params
    assert params["effective_param_ratio"] >= 0.0
    assert "paper_figure_candidate" in params
    assert "paper_conclusion_candidate" in params


def test_saxs_strain_series_result_exposes_q_star_rel() -> None:
    from polynexus.core.saxs_engine.saxs_strain import StrainPhase, StrainPointResult, StrainSeriesResult

    result = StrainSeriesResult(
        strain_points=[
            StrainPointResult(
                strain_pct=0.0,
                phase=StrainPhase.ELASTIC,
                Q_star=10.0,
                Q_star_rel=1.0,
                Q_star_normalized=1.0,
            ),
            StrainPointResult(
                strain_pct=8.0,
                phase=StrainPhase.PLASTIC_VOIDING,
                Q_star=11.5,
                Q_star_rel=1.15,
                Q_star_normalized=1.15,
            ),
        ],
        strains=np.asarray([0.0, 8.0], dtype=float),
        Q_star_array=np.asarray([10.0, 11.5], dtype=float),
        Q_star_rel_array=np.asarray([1.0, 1.15], dtype=float),
        L_array=np.asarray([12.0, 11.7], dtype=float),
        lc_array=np.asarray([2.5, 2.6], dtype=float),
        la_array=np.asarray([9.5, 9.1], dtype=float),
        f_herman_array=np.asarray([0.05, 0.20], dtype=float),
        phi_void_array=np.asarray([np.nan, 0.08], dtype=float),
    )

    df = result.to_dataframe()

    assert "Q_star_rel" in df.columns
    assert float(df.iloc[1]["Q_star_rel"]) == 1.15
