from __future__ import annotations

import json
from pathlib import Path

from polynexus.orchestrator import ParameterOrchestrator
from rag.advisor import Advisor
from rag.prompt_builder import PromptBuilder
from polynexus.core.analysis_evidence import build_analysis_evidence, summarize_constraints
from tests.eval.runner import EvalRunner


class _StaticRetriever:
    def retrieve(self, *args, **kwargs):
        return []


class _StaticLLM:
    last_used_mock = False

    def chat(self, prompt: str, json_mode: bool = True, cancel_event=None) -> str:
        return json.dumps(
            {
                "assessment": "PASS",
                "confidence": 0.91,
                "diagnosis": "peak_window_mismatch",
                "reasoning": "Use the evidence to narrow the adjustment.",
                "hypothesis": "The residual structure points to a windowing mismatch.",
                "target_symptom": "systematic_peak",
                "recommended_actions": [
                    {
                        "name": "adjust_peak_window",
                        "reason": "Re-center the Bragg window first.",
                        "expected_evidence_change": "peak residual should weaken",
                    }
                ],
                "changes": {"savgol_window": 15},
                "allowed_changes": {"savgol_window": 15},
                "expected_improvement": {"r_squared": "increase"},
                "expected_evidence_change": {"residual_type": "more_random"},
                "rollback_condition": "If evidence flags worsen, revert.",
                "risk": "low",
                "suggestions": ["tighten the smoothing window"],
                "reference_cases": [],
                "converge": False,
            },
            ensure_ascii=False,
        )


def _temperature_ir_dir() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "测试数据"
        / "IR"
        / "原位变温红外"
    )


def test_analysis_evidence_round_trip_and_prompt_contract() -> None:
    case_path = Path("tests/eval/cases/real/waxs_real_static_pa6.json")
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    data_file = payload["config_overrides"]["source_file"]

    report = ParameterOrchestrator(
        technique="waxs",
        data_file=data_file,
        polymer_name=payload["polymer_name"],
        max_rounds=1,
        advisor=Advisor(retriever=_StaticRetriever(), llm_client=_StaticLLM()),
    ).run()

    round0 = report["history"][0]
    assert round0["analysis_evidence"]["technique"] == "WAXS"
    assert "constraints" in round0["analysis_evidence"]
    assert "constraint_summary" in round0["analysis_evidence"]

    prompt = PromptBuilder().build_prompt(
        {
            "technique": "WAXS",
            "polymer_name": payload["polymer_name"],
            "params": round0["output_parameters"],
            "current_config": round0["config_snapshot"],
            "r_squared": round0["r_squared"],
            "residual_pattern": round0["residuals_pattern"],
            "analysis_evidence": round0["analysis_evidence"],
            "polymer_knowledge": round0["polymer_knowledge"],
        },
        [],
    )

    assert "## Core evidence" in prompt
    assert "## Response contract" in prompt
    assert "## Boundary" in prompt
    assert "orchestrator decides accept / rollback" in prompt
    assert "constraint_summary" in prompt
    assert "peak_evidence" in prompt


def test_analysis_evidence_includes_symptom_action_bridge() -> None:
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters={"r_squared": 0.92, "quality_score": 0.81},
        residual_pattern={"residual_type": "peak_mismatch", "summary": "peak mismatch near 19.3 deg"},
    ).to_dict()

    assert any("peak_mismatch" in str(item) for item in evidence["actionable_symptoms"])
    assert any("peak_function" in str(item) for item in evidence["actionable_symptoms"])


def test_constraint_summary_groups_triggered_constraints_by_kind() -> None:
    summary = summarize_constraints(
        [
            {"name": "beamstop_contamination", "kind": "hard_fail", "triggered": True},
            {"name": "mask_truncated", "kind": "soft_warn", "triggered": True},
            {"name": "low_peak_snr", "kind": "evidence_only", "triggered": False},
        ]
    )

    assert summary["status"] == "hard_fail"
    assert summary["inventory"]["hard_fail"] == 1
    assert summary["inventory"]["soft_warn"] == 1
    assert summary["inventory"]["evidence_only"] == 1
    assert summary["triggered_total"] == 2
    assert summary["triggered_names"]["hard_fail"] == ["beamstop_contamination"]
    assert summary["triggered_names"]["soft_warn"] == ["mask_truncated"]


def test_saxs_constraint_summary_marks_hard_fail_and_warn_layers() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "quality_score": 0.78,
            "beam_stop_contaminated": True,
            "mask_truncated": True,
            "q_peak_snr": 2.4,
            "L_bragg": 12.0,
            "L_corr_peak": 11.1,
        },
        residual_pattern={"residual_type": "background_drift", "summary": "low-q drift remains"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    symptom_names = {item["name"] for item in evidence["symptoms"]}
    assert summary["status"] == "hard_fail"
    assert summary["triggered_counts"]["hard_fail"] == 1
    assert summary["triggered_counts"]["soft_warn"] >= 1
    assert "beamstop_contamination" in summary["triggered_names"]["hard_fail"]
    assert "mask_truncated" in summary["triggered_names"]["soft_warn"]
    assert "beamstop_or_low_q_contamination" in symptom_names
    assert "multi_method_disagreement" in symptom_names
    assert "constraint_status=hard_fail" in evidence["summary"]


def test_saxs_evidence_flags_missing_condition_axis_and_unstable_fit_regions() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "quality_score": 0.46,
            "condition_label": "Temperature",
            "file": "Check-20260618_0_00002.edf",
            "fit_regions": [
                {"region": "peak", "r_squared": 0.12, "rmse": 0.42},
                {"region": "correlation", "r_squared": 0.08, "rmse": 0.51, "peak_count": 14, "zero_crossings": 18},
                {"region": "idf", "r_squared": 0.19, "rmse": 0.39, "peak_count": 11},
            ],
        },
        residual_pattern={"residual_type": "noise", "summary": "correlation curve oscillates too densely"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    symptom_names = {item["name"] for item in evidence["symptoms"]}
    assert summary["status"] == "hard_fail"
    assert "missing_condition_axis" in summary["triggered_names"]["hard_fail"]
    assert "fit_regions_unstable" in summary["triggered_names"]["soft_warn"]
    assert "correlation_over_oscillation" in summary["triggered_names"]["soft_warn"]
    assert "condition_axis_missing" in symptom_names
    assert "peak_window_mismatch" in symptom_names
    assert "idf_artifact_regular_spacing" in symptom_names
    assert any("series_condition_axis_missing" in str(item) for item in evidence["actionable_symptoms"])
    assert any("correlation_curve_over_oscillating" in str(item) for item in evidence["actionable_symptoms"])


def test_saxs_analysis_evidence_includes_structured_single_frame_sections() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "r_squared": 0.88,
            "quality_score": 0.72,
            "fit_rmse": 0.12,
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: low-q region remains uncertain",
            "Q_star": 12.3,
            "Q_star_valid": False,
            "beam_stop_contaminated": True,
            "mask_truncated": True,
            "q_peak_snr": 2.7,
            "L_bragg": 12.4,
            "L_lorentz": 12.0,
            "L_corr_peak": 11.6,
            "L_pyfai_nm": 12.5,
            "q_peak_diff_pct": 3.1,
            "L_nm": 12.1,
            "L_best": 12.1,
            "L_confidence": 0.58,
            "lc_nm": 4.3,
            "la_nm": 7.8,
            "phi_c": 0.355,
            "lc_confidence": 0.41,
            "lc_method": "tangent_strain_qstar_warn",
            "lc_tangent_nm": 4.1,
            "lc_gamma_min_nm": 4.6,
            "lc_idf_nm": 4.4,
            "phi_c_invariant": 0.34,
            "sasmodels_R2": 0.63,
            "sasmodels_model_used": "lamellar_hg",
            "fit_regions": [
                {"region": "peak", "r_squared": 0.82, "rmse": 0.12},
                {"region": "correlation", "r_squared": 0.48, "rmse": 0.21},
            ],
            "condition_label": "Temperature",
            "condition_value": 120.0,
            "condition_source": "header",
            "condition_confidence": 0.91,
            "condition_continuity_score": 0.96,
        },
        residual_pattern={"residual_type": "background_drift", "summary": "low-q drift remains"},
    ).to_dict()

    assert evidence["signal_evidence"]["beam_stop_contaminated"] is True
    assert evidence["signal_evidence"]["Q_star_valid"] is False
    assert evidence["peak_evidence"]["L_bragg"] == 12.4
    assert evidence["transform_evidence"]["lc_tangent_nm"] == 4.1
    assert evidence["structure_evidence"]["lc_method"] == "tangent_strain_qstar_warn"
    assert evidence["structure_evidence"]["sasmodels_model_used"] == "lamellar_hg"
    assert evidence["condition_evidence"]["condition_source"] == "header"
    assert evidence["stability_evidence"]["stability_score"] > 0.0
    assert evidence["stability_evidence"]["parameter_stability_score"] > 0.0
    assert evidence["stability_evidence"]["method_agreement_score"] > 0.0
    assert any(item["name"] == "gamma_tangent_unstable" for item in evidence["symptoms"])
    assert evidence["feature_evidence"]["signal_evidence"]["q_peak_snr"] == 2.7
    assert "stability_evidence" in evidence["feature_evidence"]
    assert "condition_source" in evidence["source_fields"]
    assert "stability_score" in evidence["source_fields"]


def test_saxs_analysis_evidence_includes_batch_and_condition_sections() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "batch_frames": 3,
            "condition_label": "Temperature",
            "condition_range": "100.0-120.0",
            "condition_source": "folder",
            "condition_source_key": "temp_directory_label",
            "condition_source_text": "temperature_100",
            "condition_confidence": 0.68,
            "condition_missing_frames": 1,
            "condition_continuity_score": 0.74,
            "_batch_data": [
                {"file": "frame_001.edf", "temperature_C": 100.0, "condition_value": 100.0, "L_nm": 11.2},
                {"file": "frame_002.edf", "temperature_C": None, "condition_value": None, "L_nm": 11.0},
                {"file": "frame_003.edf", "temperature_C": 120.0, "condition_value": 120.0, "L_nm": 10.7},
            ],
        },
        residual_pattern={"residual_type": "noise", "summary": "trend looks incomplete"},
    ).to_dict()

    assert evidence["batch_evidence"]["batch_frames"] == 3
    assert evidence["batch_evidence"]["condition_range"] == "100.0-120.0"
    assert evidence["batch_evidence"]["sample_files"] == ["frame_001.edf", "frame_002.edf", "frame_003.edf"]
    assert evidence["condition_evidence"]["condition_missing_frames"] == 1
    assert evidence["condition_evidence"]["condition_continuity_score"] == 0.74
    assert evidence["condition_evidence"]["condition_source_key"] == "temp_directory_label"
    assert evidence["condition_evidence"]["condition_source_text"] == "temperature_100"
    assert evidence["stability_evidence"]["batch_continuity_score"] < 0.8
    assert "batch_frames=3" in evidence["summary"]
    assert "condition_source=folder" in evidence["summary"]
    assert "stability=" in evidence["summary"]


def test_saxs_analysis_evidence_includes_strain_void_orientation_sections() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "batch_frames": 4,
            "condition_label": "strain",
            "condition_source": "strain_series",
            "condition_confidence": 0.82,
            "Q_star_rel_mean": 1.08,
            "Q_star_rel_span": 0.11,
            "phi_void_mean": 0.034,
            "phi_void_span": 0.017,
            "f_Herman_mean": 0.21,
            "f_Herman_span": 0.54,
            "porod_slope_mean": -3.18,
            "void_detected_frames": 3,
            "phase_distribution": {"elastic": 1, "plastic_voiding": 2, "microfibrillation": 1},
            "dominant_phase": "microfibrillation",
            "phase_boundary_candidates": [
                {"strain_pct": 8.0, "from_phase": "elastic", "to_phase": "plastic_voiding"},
                {"strain_pct": 16.0, "from_phase": "plastic_voiding", "to_phase": "microfibrillation"},
            ],
            "phase_support_mean": 0.74,
            "phase_support_span": 0.18,
            "phase_ambiguous_frame_count": 1,
            "frame_low_conf_count": 1,
            "void_dominant_frame_count": 2,
            "effective_param_ratio": 0.67,
            "strain_reliability_status": "low_confidence",
            "strain_reliability_reason": "strain_axis_low_confidence|low_q_void_dominant",
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": False,
            "paper_conclusion_ready": False,
            "L_bragg": 11.8,
            "L_corr_peak": 9.9,
            "L_best": 12.1,
            "Q_star_valid": False,
            "mask_truncated": True,
        },
        residual_pattern={"residual_type": "noise", "summary": "strain series shows coupled low-q instability"},
    ).to_dict()

    summary = evidence["summary"]
    symptom_names = {item["name"] for item in evidence["symptoms"]}
    assert "low_q_void_dominant" in symptom_names
    assert "strain_void_lamellar_conflict" in symptom_names
    assert "qstar_rel_without_lamellar_support" in symptom_names
    assert evidence["structure_evidence"]["Q_star_rel_mean"] == 1.08
    assert evidence["structure_evidence"]["phi_void_mean"] == 0.034
    assert evidence["structure_evidence"]["f_Herman_span"] == 0.54
    assert evidence["structure_evidence"]["strain_reliability_status"] == "low_confidence"
    assert evidence["structure_evidence"]["paper_figure_candidate"] is True
    assert evidence["feature_evidence"]["strain_phase_evidence"]["dominant_phase"] == "microfibrillation"
    assert evidence["feature_evidence"]["strain_structure_evidence"]["void_detected_frames"] == 3
    assert "Q_star_rel=1.08" in summary
    assert "phi_void=0.034" in summary
    assert "f_Herman=0.21" in summary
    assert "void_frames=3" in summary
    assert "strain_status=low_confidence" in summary
    assert "paper_candidate=False" in summary or "paper_conclusion_candidate=False" in summary


def test_saxs_analysis_evidence_includes_batch_calibration_summary() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "batch_frames": 3,
            "condition_label": "Temperature",
            "condition_range": "100.0-120.0",
            "condition_source": "header",
            "condition_confidence": 0.9,
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            "fallback_applied_fields": ["lc_nm", "la_nm", "Xc"],
            "batch_calibration_summary": {
                "batch_rows": 3,
                "fallback_rows": 3,
                "raw_snapshot_rows": 3,
                "fallback_ratio": 1.0,
                "raw_structure_available": True,
                "calibrated_fallback_active": True,
                "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            },
            "_batch_data": [
                {
                    "file": "frame_001.edf",
                    "temperature_C": 100.0,
                    "lc_nm": 3.1,
                    "lc_nm_raw": 2.8,
                    "Xc": 0.36,
                    "Xc_raw": 0.32,
                    "raw_snapshot": {"structure": {"lc": 2.8, "phi_c": 0.32, "L": 8.0}},
                },
                {
                    "file": "frame_002.edf",
                    "temperature_C": 110.0,
                    "lc_nm": 3.1,
                    "lc_nm_raw": 2.7,
                    "Xc": 0.35,
                    "Xc_raw": 0.31,
                    "raw_snapshot": {"structure": {"lc": 2.7, "phi_c": 0.31, "L": 8.1}},
                },
                {
                    "file": "frame_003.edf",
                    "temperature_C": 120.0,
                    "lc_nm": 3.1,
                    "lc_nm_raw": 2.6,
                    "Xc": 0.34,
                    "Xc_raw": 0.30,
                    "raw_snapshot": {"structure": {"lc": 2.6, "phi_c": 0.30, "L": 8.2}},
                },
            ],
        },
        residual_pattern={"residual_type": "noise", "summary": "fallback summary should stay visible"},
    ).to_dict()

    assert evidence["batch_evidence"]["batch_calibration_summary"]["fallback_ratio"] == 1.0
    assert evidence["batch_evidence"]["batch_calibration_summary"]["raw_structure_available"] is True
    assert evidence["batch_evidence"]["batch_calibration_summary"]["calibrated_fallback_reason"] == "temperature_batch_lc_calibration"
    assert "fallback_ratio=1.0" in evidence["summary"]


def test_saxs_analysis_evidence_includes_raw_and_calibrated_layers() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "L_nm": 10.0,
            "lc_nm": 3.5,
            "la_nm": 6.5,
            "phi_c": 0.35,
            "lc_confidence": 0.5,
            "lc_method": "calibrated",
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            "fallback_applied_fields": ["lc_nm", "la_nm", "Xc", "lc_confidence"],
            "raw_snapshot": {
                "long_period": {"L_best": 10.0, "L_confidence": 0.42},
                "structure": {"L": 10.0, "lc": 3.2, "la": 6.8, "phi_c": 0.32, "confidence_lc": 0.31, "Q_invariant": 18.2},
            },
        },
        residual_pattern={"residual_type": "noise", "summary": "calibration layer should stay visible"},
    ).to_dict()

    assert evidence["structure_evidence"]["calibrated_fallback_active"] is True
    assert evidence["structure_evidence"]["calibrated_fallback_reason"] == "temperature_batch_lc_calibration"
    assert evidence["feature_evidence"]["raw_structure_evidence"]["lc_nm_raw"] == 3.2
    assert evidence["feature_evidence"]["raw_structure_evidence"]["raw_structure_available"] is True
    assert "raw_structure_available=True" in evidence["summary"]
    assert "lc_method=calibrated" in evidence["summary"]
    assert "fallback=temperature_batch_lc_calibration" in evidence["summary"]


def test_saxs_analysis_evidence_includes_calibration_skip_reason() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "L_nm": 9.8,
            "lc_nm": 3.0,
            "lc_method": "raw",
            "calibration_skipped_reason": "missing_reference_crystallinity",
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "low_lc_confidence|single_method_fragile",
        },
        residual_pattern={"residual_type": "noise", "summary": "skip reason should stay visible"},
    ).to_dict()

    assert evidence["structure_evidence"]["calibration_skipped_reason"] == "missing_reference_crystallinity"
    assert "lc_method=raw" in evidence["summary"]
    assert "calibration_skip=missing_reference_crystallinity" in evidence["summary"]


def test_saxs_analysis_evidence_includes_lc_status_and_melting_window_fields() -> None:
    evidence = build_analysis_evidence(
        "SAXS",
        output_parameters={
            "batch_frames": 2,
            "L_nm": 9.6,
            "lc_nm": 1.2,
            "lc_confidence": 0.18,
            "melting_window_status": "near_onset",
            "melting_window_reason": "near_sequence_melting_onset",
            "lc_reliability_status": "diagnostic_only",
            "lc_reliability_reason": "low_lc_confidence|near_melting_onset",
            "batch_structure_summary": {
                "diagnostic_only_rows": 1,
                "within_window_rows": 0,
                "dominant_melting_window_status": "near_onset",
                "dominant_lc_reliability_status": "diagnostic_only",
                "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
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
        residual_pattern={"residual_type": "noise", "summary": "status fields should stay visible"},
    ).to_dict()

    assert evidence["structure_evidence"]["melting_window_status"] == "near_onset"
    assert evidence["structure_evidence"]["lc_reliability_status"] == "diagnostic_only"
    assert evidence["batch_evidence"]["batch_structure_summary"]["diagnostic_only_rows"] == 1
    assert evidence["batch_evidence"]["frame_condition_values"][1]["lc_reliability_status"] == "diagnostic_only"
    assert "melting_window=near_onset" in evidence["summary"]
    assert "lc_status=diagnostic_only" in evidence["summary"]
    assert any("do not call this melting yet" in str(item) for item in evidence["actionable_symptoms"])


def test_dsc_constraint_summary_marks_quality_floor_hard_fail() -> None:
    evidence = build_analysis_evidence(
        "DSC",
        output_parameters={
            "quality_score": 0.42,
            "scan_r_squared": [{"scan": 1, "r_squared": 0.81}],
            "Tm_peak_C": 221.0,
        },
        residual_pattern={"residual_type": "noise", "summary": "noise remains"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    assert summary["status"] == "hard_fail"
    assert "quality_floor" in summary["triggered_names"]["hard_fail"]
    assert summary["inventory"]["evidence_only"] == 1
    assert summary["triggered_counts"]["evidence_only"] == 0


def test_dsc_analysis_evidence_surfaces_temperature_peaks_and_quality_gate() -> None:
    evidence = build_analysis_evidence(
        "DSC",
        output_parameters={
            "quality_score": 0.85,
            "scan_r_squared": [{"scan": 1, "r_squared": 0.89}],
            "Tm_peak_C": 222.4,
            "Tcc_peak_C": 177.0,
            "Xc_pct": 11.9,
            "DHm_Jg": 33.8,
            "DHcc_Jg": 6.5,
            "peak_components": [],
        },
        residual_pattern={"residual_type": "random", "summary": "balanced residuals"},
    ).to_dict()

    feature = evidence["feature_evidence"]
    summary = evidence["constraint_summary"]

    assert feature["Tm_peak_C"] == 222.4
    assert feature["Tcc_peak_C"] == 177.0
    assert feature["Xc_pct"] == 11.9
    assert feature["scan_r_squared"] == [{"scan": 1, "r_squared": 0.89}]
    assert feature["peak_components"] == []
    assert "thermal_event_evidence" in feature
    assert "baseline_evidence" in feature
    assert "scan_evidence" in feature
    assert "event_support_evidence" in feature
    assert summary["status"] != "hard_fail"
    assert "quality_floor" not in summary["triggered_names"]["hard_fail"]
    assert evidence["feature_evidence"]["Tm_peak_C"] == 222.4
    assert evidence["feature_evidence"]["Xc_pct"] == 11.9


def test_dsc_xc_with_unstable_baseline_is_low_confidence() -> None:
    evidence = build_analysis_evidence(
        "DSC",
        output_parameters={
            "quality_score": 0.9,
            "scan_mode": "heating",
            "Tm_peak_C": 221.0,
            "DHm_Jg": 78.0,
            "DHcc_Jg": 18.0,
            "Xc_pct": 38.0,
            "Xc_method": "enthalpy",
            "DHm0_Jg": 230.0,
            "DHm0_source": "polymer_reference",
            "baseline_sensitivity_pct": 14.0,
            "integration_boundary_sensitivity_pct": 9.0,
            "peak_components": [
                {"type": "melting", "peak_C": 221.0, "onset_C": 205.0, "end_C": 235.0, "enthalpy_Jg": 78.0},
                {"type": "cold_crystallization", "peak_C": 125.0, "onset_C": 110.0, "end_C": 140.0, "enthalpy_Jg": 18.0},
            ],
        },
        residual_pattern={"residual_type": "random", "summary": "baseline is visually calm but sensitivity is high"},
        validation_context={"config_snapshot": {"min_event_enthalpy_Jg": 0.05}},
    ).to_dict()

    structure = evidence["feature_evidence"]["structure_evidence"]
    crystallinity = evidence["feature_evidence"]["crystallinity_evidence"]

    assert crystallinity["baseline_sensitivity_pct"] == 14.0
    assert crystallinity["integration_boundary_sensitivity_pct"] == 9.0
    assert structure["Xc_reliability_status"] == "low_confidence"
    assert "dsc_baseline_sensitive_xc" in evidence["constraint_summary"]["triggered_names"]["soft_warn"]


def test_dsc_xc_uncertainty_distribution_is_evidence() -> None:
    evidence = build_analysis_evidence(
        "DSC",
        output_parameters={
            "quality_score": 0.9,
            "scan_mode": "heating",
            "Tm_peak_C": 221.0,
            "DHm_Jg": 78.0,
            "DHm_Jg_mean": 77.6,
            "DHm_Jg_std": 2.5,
            "DHcc_Jg": 18.0,
            "DHcc_Jg_mean": 18.4,
            "DHcc_Jg_std": 1.0,
            "Xc_pct": 38.0,
            "Xc_pct_mean": 37.5,
            "Xc_pct_std": 4.6,
            "Xc_pct_ci95": 9.0,
            "Xc_method": "enthalpy",
            "DHm0_Jg": 230.0,
            "DHm0_source": "polymer_reference",
            "baseline_sensitivity_pct": 3.1,
            "integration_boundary_sensitivity_pct": 4.2,
            "baseline_variant_count": 3,
            "integration_variant_count": 27,
            "peak_components": [
                {"type": "melting", "peak_C": 221.0, "onset_C": 205.0, "end_C": 235.0, "enthalpy_Jg": 78.0},
                {"type": "cold_crystallization", "peak_C": 125.0, "onset_C": 110.0, "end_C": 140.0, "enthalpy_Jg": 18.0},
            ],
        },
        residual_pattern={"residual_type": "random", "summary": "variant spread is the dominant uncertainty"},
        validation_context={"config_snapshot": {"min_event_enthalpy_Jg": 0.05}},
    ).to_dict()

    structure = evidence["feature_evidence"]["structure_evidence"]
    crystallinity = evidence["feature_evidence"]["crystallinity_evidence"]

    assert crystallinity["Xc_pct_mean"] == 37.5
    assert crystallinity["Xc_pct_std"] == 4.6
    assert crystallinity["Xc_pct_ci95"] == 9.0
    assert crystallinity["DHm_Jg_mean"] == 77.6
    assert crystallinity["DHm_Jg_std"] == 2.5
    assert crystallinity["DHcc_Jg_mean"] == 18.4
    assert crystallinity["DHcc_Jg_std"] == 1.0
    assert crystallinity["baseline_variant_count"] == 3
    assert crystallinity["integration_variant_count"] == 27
    assert structure["Xc_pct_ci95"] == 9.0
    assert structure["Xc_reliability_status"] == "low_confidence"


def test_dsc_analysis_evidence_flags_physical_conflicts_and_window_issues() -> None:
    evidence = build_analysis_evidence(
        "DSC",
        output_parameters={
            "quality_score": 0.82,
            "scan_mode": "heating",
            "Tg_C": 18.0,
            "DTg_C": 0.6,
            "DCp_JgK": 0.0,
            "Tm_onset_C": 220.0,
            "Tm_peak_C": 225.0,
            "Tm_end_C": 242.0,
            "Tcc_onset_C": 224.0,
            "Tcc_peak_C": 228.0,
            "DHm_Jg": 12.4,
            "DHcc_Jg": 4.2,
            "Xc_pct": 14.5,
            "peak_components": [
                {"type": "melting", "peak_C": 225.0, "onset_C": 220.0, "end_C": 242.0, "enthalpy_Jg": 12.4},
                {"type": "cold_crystallisation", "peak_C": 228.0, "onset_C": 224.0, "end_C": 236.0, "enthalpy_Jg": -4.2},
            ],
            "scan_r_squared": [
                {"scan": 1, "r_squared": 0.92},
                {"scan": 2, "r_squared": 0.61},
            ],
        },
        residual_pattern={"residual_type": "baseline_drift", "summary": "baseline drift remains"},
        validation_context={
            "config_snapshot": {
                "exo_up": True,
                "baseline_corr": "tangential",
                "smooth_window": 11,
                "Tg_search_low_C": 20.0,
                "Tg_search_high_C": 120.0,
                "Tm_search_low_C": 100.0,
                "Tm_search_high_C": 300.0,
                "Tc_search_low_C": 50.0,
                "Tc_search_high_C": 250.0,
                "peak_function": "gaussian",
                "peak_prominence_ratio": 0.03,
                "min_event_enthalpy_Jg": 0.05,
                "max_melting_peak_width_C": 50.0,
            }
        },
    ).to_dict()

    summary = evidence["constraint_summary"]
    feature = evidence["feature_evidence"]
    triggered = summary["triggered_names"]["soft_warn"]

    assert summary["status"] == "soft_warn"
    assert "baseline_sensitive_result" in triggered
    assert "Tg_without_DCp_step" in triggered
    assert "Tg_outside_supported_window" in triggered
    assert "cold_crystallization_conflicts_with_melting" in triggered
    assert "event_polarity_conflict" in triggered
    assert "multi_scan_inconsistent" in triggered
    assert feature["thermal_event_evidence"]["Tg_search_low_C"] == 20.0
    assert feature["thermal_event_evidence"]["Tm_search_high_C"] == 300.0
    assert feature["baseline_evidence"]["baseline_corr"] == "tangential"
    assert feature["event_support_evidence"]["event_support_score"] >= 0.0


def test_dsc_analysis_evidence_keeps_real_pa6_conservative() -> None:
    project_root = Path(__file__).resolve().parents[1]
    case_path = project_root / "tests" / "eval" / "cases" / "real" / "dsc_real_standard_pa6.json"
    runner = EvalRunner(project_root=project_root)
    case = runner.load_case(case_path)
    result = runner.run_case(case)

    evidence = build_analysis_evidence(
        "DSC",
        output_parameters=result.output_parameters,
        residual_pattern={"residual_type": "random", "summary": "balanced residuals"},
        validation_context={"config_snapshot": case.config_overrides},
    ).to_dict()

    feature = evidence["feature_evidence"]
    structure = feature["structure_evidence"]
    summary = evidence["constraint_summary"]

    assert summary["status"] == "soft_warn"
    assert "multi_scan_inconsistent" in summary["triggered_names"]["soft_warn"]
    assert "event_polarity_conflict" not in summary["triggered_names"]["soft_warn"]
    assert structure["supported_event_count"] == 3
    assert structure["supported_melting_event_count"] == 1
    assert structure["paper_conclusion_candidate"] is False
    assert structure["paper_conclusion_ready"] is False
    assert structure["event_support_score"] > 0.9
    assert structure["structure_support_score"] < 0.85
    assert feature["event_support_evidence"]["scan_r_squared_median"] > 0.9
    assert feature["event_support_evidence"]["scan_r_squared_spread"] > 0.0
    assert "paper_candidate=False" in evidence["summary"]
    assert "paper_ready=False" in evidence["summary"]


def test_waxs_constraint_summary_marks_soft_warn_without_hard_fail() -> None:
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters={
            "r_squared": 0.97,
            "quality_score": 0.84,
            "n_peaks": 0,
        },
        residual_pattern={"residual_type": "peak_mismatch", "summary": "sharp peaks are missing"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    assert summary["status"] == "soft_warn"
    assert summary["triggered_counts"]["hard_fail"] == 0
    assert "peak_visibility" in summary["triggered_names"]["soft_warn"]
    assert summary["triggered_total"] >= 1


def test_waxs_analysis_evidence_exposes_peak_background_and_phase_support() -> None:
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters={
            "r_squared": 0.93,
            "quality_score": 0.93,
            "n_peaks": 1,
            "Xc_pct": 69.6,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 8.3,
            "crystallinity_method": "peak_deconvolution",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "two_theta_offset": 0.08,
            "peaks": [
                {"two_theta": 17.8781, "fwhm_deg": 0.8549, "area": 2442.34},
            ],
        },
        residual_pattern={"residual_type": "random", "summary": "baseline looks calm"},
        validation_context={"config_snapshot": {"two_theta_offset": 0.08, "amorphous_subtraction": "polynomial", "amorphous_n_peaks": 2}},
    ).to_dict()

    summary = evidence["constraint_summary"]
    assert summary["status"] == "soft_warn"
    assert "peak_count_insufficient" in summary["triggered_names"]["soft_warn"]
    assert "crystallinity_without_peak_support" in summary["triggered_names"]["soft_warn"]
    assert "size_without_multi_peak_support" in summary["triggered_names"]["soft_warn"]
    assert "offset_sensitive_solution" in summary["triggered_names"]["soft_warn"]
    assert evidence["background_evidence"]["two_theta_offset"] == 0.08
    assert evidence["phase_evidence"]["D_Scherrer_nm"] == 8.3
    assert evidence["feature_evidence"]["peak_evidence"]["peak_count"] == 1
    assert evidence["feature_evidence"]["background_evidence"]["two_theta_offset"] == 0.08
    assert evidence["feature_evidence"]["phase_evidence"]["D_Scherrer_nm"] == 8.3
    assert any(item["name"] == "offset_sensitive_solution" for item in evidence["symptoms"])
    assert any("offset_sensitive_solution" in item for item in evidence["actionable_symptoms"])
    assert "constraint_status=soft_warn" in evidence["summary"]


def test_waxs_analysis_evidence_exposes_structure_contract_for_confidence_review() -> None:
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters={
            "r_squared": 0.93,
            "quality_score": 0.93,
            "n_peaks": 2,
            "Xc_pct": 61.4,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 7.9,
            "crystallinity_method": "peak_deconvolution",
            "crystal_system": "alpha",
            "unit_cell_params": {"a": 4.9, "b": 5.4},
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "two_theta_offset": 0.02,
            "peaks": [
                {"two_theta": 17.88, "fwhm_deg": 0.82, "area": 2442.34},
                {"two_theta": 21.75, "fwhm_deg": 0.94, "area": 1810.52},
            ],
        },
        residual_pattern={"residual_type": "random", "summary": "baseline looks calm"},
        validation_context={"config_snapshot": {"two_theta_offset": 0.02, "amorphous_subtraction": "polynomial", "amorphous_n_peaks": 2}},
    ).to_dict()

    structure = evidence["structure_evidence"]
    phase = evidence["phase_evidence"]

    assert phase["Xc_pct"] == 61.4
    assert structure["peak_count_detected"] == 2
    assert structure["peak_count_fitted"] == 2
    assert structure["dominant_peak_positions"] == [17.88, 21.75]
    assert structure["fit_only_pass"] is True
    assert structure["physical_support_pass"] is True
    assert "structure_support_score" in structure
    assert "paper_ready_candidate" in structure
    assert any(item["name"] == "structure_support_score" for item in evidence["confidence_signals"])


def test_ir_constraint_summary_marks_key_band_mismatch_as_soft_warn() -> None:
    evidence = build_analysis_evidence(
        "IR",
        output_parameters={
            "n_peaks": 5,
            "r_squared": 0.89,
        },
        residual_pattern={"residual_type": "peak_mismatch", "summary": "band mismatch remains"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    assert summary["status"] == "soft_warn"
    assert summary["triggered_counts"]["soft_warn"] == 1
    assert "key_band_mismatch" in summary["triggered_names"]["soft_warn"]
    assert "peak_structure" in summary["triggered_names"]["evidence_only"]
    assert "constraint_status=soft_warn" in evidence["summary"]


def test_ir_constraint_summary_marks_score_without_band_support_as_soft_warn() -> None:
    evidence = build_analysis_evidence(
        "IR",
        output_parameters={
            "n_peaks": 5,
            "polymer_score": 0.74,
            "r_squared": 0.89,
        },
        residual_pattern={"residual_type": "peak_mismatch", "summary": "band mismatch remains"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    assert summary["status"] == "soft_warn"
    assert summary["triggered_counts"]["soft_warn"] == 3
    assert "assignment_without_characteristic_bands" in summary["triggered_names"]["soft_warn"]
    assert "key_band_mismatch" in summary["triggered_names"]["soft_warn"]
    assert "polymer_score_without_assignment_support" in summary["triggered_names"]["soft_warn"]
    assert "peak_structure" in summary["triggered_names"]["evidence_only"]
    assert "constraint_status=soft_warn" in evidence["summary"]


def test_ir_analysis_evidence_surfaces_reference_bands_and_assignment_contract() -> None:
    evidence = build_analysis_evidence(
        "IR",
        output_parameters={
            "n_peaks": 5,
            "polymer_name": "PA6",
            "polymer_score": 0.74,
            "assignment_confidence": 0.68,
            "r_squared": 0.89,
            "peaks": [
                {"wavenumber": 3298, "height": 1.2, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
                {"wavenumber": 1637, "height": 1.0, "prominence": 0.7, "fwhm_cm1": 14.0, "assignment": "amide I"},
                {"wavenumber": 1541, "height": 0.8, "prominence": 0.5, "fwhm_cm1": 16.0, "assignment": "unknown"},
            ],
        },
        residual_pattern={"residual_type": "peak_mismatch", "summary": "band mismatch remains"},
        validation_context={
            "ir_reference_bands": {
                "polymer_name": "PA6",
                "band_count": 3,
                "source": "IRConfig.polymer_peaks_db",
                "bands": [
                    {"wavenumber": 3298, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                    {"wavenumber": 1637, "assignment": "amide I", "crystallinity_sensitive": False},
                    {"wavenumber": 1541, "assignment": "amide II", "crystallinity_sensitive": False},
                ],
            }
        },
    ).to_dict()

    reference = evidence["feature_evidence"]["reference_evidence"]
    assignment = evidence["feature_evidence"]["assignment_evidence"]
    structure = evidence["feature_evidence"]["structure_evidence"]
    summary = evidence["constraint_summary"]

    assert reference["band_count"] == 3
    assert reference["hit_count"] == 3
    assert reference["missing_count"] == 0
    assert len(reference["bands"]) == 3
    assert "peak_prominence_distribution" in evidence["feature_evidence"]["peak_evidence"]
    assert evidence["feature_evidence"]["peak_evidence"]["assigned_peak_count"] == 2
    assert evidence["feature_evidence"]["peak_evidence"]["unassigned_peak_count"] == 1
    assert len(evidence["feature_evidence"]["peak_evidence"]["assigned_peaks"]) == 2
    assert len(evidence["feature_evidence"]["peak_evidence"]["unassigned_peaks"]) == 1
    assert assignment["key_band_hit_count"] == 3
    assert assignment["key_band_missing_count"] == 0
    assert assignment["assignment_confidence"] == 0.68
    assert assignment["assignment_confidence_score"] is not None
    assert assignment["key_band_support_score"] == 1.0
    assert assignment["peak_coverage_score"] == 2 / 3
    assert "assigned_peaks" in assignment
    assert "unassigned_peaks" in assignment
    assert structure["reference_band_count"] == 3
    assert structure["reference_band_hit_count"] == 3
    assert structure["reference_band_missing_count"] == 0
    assert structure["characteristic_band_support_ok"] is True
    assert structure["paper_conclusion_ready"] is False
    assert structure["classification_basis"] == "peak_assignment"
    assert structure["baseline_stability_score"] is not None
    assert structure["triggered_constraint_count"] >= 0
    assert structure["ir_support_score"] is not None
    assert "ir_support_evidence" in evidence["feature_evidence"]
    assert evidence["feature_evidence"]["classification_evidence"] == structure
    assert summary["status"] == "soft_warn"
    assert summary["triggered_counts"]["soft_warn"] == 2
    assert "polymer_score_without_assignment_support" in summary["triggered_names"]["soft_warn"]
    assert "key_band_mismatch" in summary["triggered_names"]["soft_warn"]
    assert "assignment_confidence" not in summary["triggered_names"]["soft_warn"]
    assert any(item["name"] == "assignment_confidence" for item in evidence["confidence_signals"])


def test_ir_analysis_evidence_keeps_real_pa6_yl_conservative() -> None:
    case_path = Path("tests/eval/cases/real/ir_real_standard_pa6_yl.json")
    payload = json.loads(case_path.read_text(encoding="utf-8"))

    from polynexus.core.ir_engine import IRConfig, analyze_spectrum, load_spectrum, preprocess_pipeline

    data_file = Path(payload["config_overrides"]["source_file"])
    cfg = IRConfig(
        peak_height_min=payload["config_overrides"]["peak_height_min"],
        peak_prominence_min=payload["config_overrides"]["peak_prominence_min"],
        peak_distance=payload["config_overrides"]["peak_distance"],
        baseline_method=payload["config_overrides"]["baseline_method"],
        smooth_window=payload["config_overrides"]["smooth_window"],
        normalization_method=payload["config_overrides"]["normalization_method"],
        lineshape=payload["config_overrides"]["lineshape"],
        polymer_name=payload["polymer_name"],
    )
    spec = load_spectrum(str(data_file))
    processed = preprocess_pipeline(spec, cfg)
    result = analyze_spectrum(processed, cfg, label=spec.label, polymer_name=payload["polymer_name"])

    evidence = build_analysis_evidence(
        "IR",
        output_parameters=result.__dict__,
        residual_pattern={
            "residual_type": "crowded_band_underfit",
            "summary": "IR residual maximum near 1469.5 cm^-1 with negative residual (fit too high); RMSE=0.006745, residual_type=crowded_band_underfit.",
            "max_residual_region": "1469.5 cm^-1",
            "rmse": 0.006745,
        },
        validation_context={
            "config_snapshot": cfg.to_dict(),
            "ir_reference_bands": {
                "polymer_name": "PA6",
                "band_count": len(cfg.polymer_peaks_db["PA6"]),
                "source": "IRConfig.polymer_peaks_db",
                "bands": [
                    {
                        "wavenumber": band[0],
                        "assignment": band[1],
                        "intensity": band[2],
                        "crystallinity_sensitive": bool(band[3]),
                    }
                    for band in cfg.polymer_peaks_db["PA6"]
                ],
            },
        },
    ).to_dict()

    reference = evidence["feature_evidence"]["reference_evidence"]
    assignment = evidence["feature_evidence"]["assignment_evidence"]
    structure = evidence["feature_evidence"]["structure_evidence"]
    summary = evidence["constraint_summary"]

    assert reference["band_count"] == 13
    assert reference["hit_count"] == 10
    assert reference["missing_count"] == 3
    assert assignment["assignment_confidence"] == 1.0
    assert assignment["key_band_support_score"] == 10 / 13
    assert assignment["peak_coverage_score"] < 1.0
    assert structure["characteristic_band_support_ok"] is False
    assert structure["paper_conclusion_ready"] is False
    assert structure["classification_basis"] == "peak_assignment"
    assert structure["ir_support_score"] < 0.85
    assert summary["status"] == "soft_warn"
    assert "baseline_sensitive_assignment" in summary["triggered_names"]["soft_warn"]
    assert "crowded_band_underfit" in summary["triggered_names"]["soft_warn"]
    assert "overcrowded_band_separation_unstable" in summary["triggered_names"]["soft_warn"]
    assert "paper_ready=False" in evidence["summary"]
    assert "band_support=False" in evidence["summary"]
    assert "ref_hits=10" in evidence["summary"]
    assert "ref_missing=3" in evidence["summary"]


def test_ir_paper_ready_requires_assignment_support_not_just_band_hits() -> None:
    peaks = [
        {"wavenumber": 3298, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
        {"wavenumber": 1637, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide I"},
        {"wavenumber": 1541, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide II"},
        {"wavenumber": 1263, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide III"},
        {"wavenumber": 929, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide V"},
        {"wavenumber": 685, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide V"},
    ]
    reference_bands = [
        {"wavenumber": item["wavenumber"], "assignment": item["assignment"], "crystallinity_sensitive": False}
        for item in peaks
    ]
    validation_context = {
        "config_snapshot": {
            "baseline_method": "rubberband",
            "normalization_method": "minmax",
            "smooth_window": 7,
            "peak_distance": 18.0,
            "peak_fit_window_cm1": 35.0,
        },
        "ir_reference_bands": {
            "polymer_name": "PA6",
            "band_count": len(reference_bands),
            "bands": reference_bands,
        },
    }

    low_confidence = build_analysis_evidence(
        "IR",
        output_parameters={
            "n_peaks": len(peaks),
            "polymer_name": "PA6",
            "polymer_score": 0.25,
            "assignment_confidence": 0.25,
            "r_squared": 0.95,
            "peaks": peaks,
        },
        residual_pattern={"residual_type": "random", "summary": "baseline is calm"},
        validation_context=validation_context,
    ).to_dict()
    low_structure = low_confidence["feature_evidence"]["structure_evidence"]

    assert low_structure["paper_conclusion_candidate"] is True
    assert low_structure["paper_conclusion_ready"] is False
    assert "assignment_confidence" in low_confidence["constraint_summary"]["triggered_names"]["soft_warn"]

    high_confidence = build_analysis_evidence(
        "IR",
        output_parameters={
            "n_peaks": len(peaks),
            "polymer_name": "PA6",
            "polymer_score": 0.92,
            "assignment_confidence": 0.92,
            "r_squared": 0.97,
            "peaks": peaks,
        },
        residual_pattern={"residual_type": "random", "summary": "baseline is calm"},
        validation_context=validation_context,
    ).to_dict()
    high_structure = high_confidence["feature_evidence"]["structure_evidence"]

    assert high_structure["paper_conclusion_candidate"] is True
    assert high_structure["paper_conclusion_ready"] is True
    assert high_structure["ir_support_score"] >= 0.78


def test_ir_uncalibrated_band_index_is_not_paper_ready_xc() -> None:
    peaks = [
        {"wavenumber": 3298, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "N-H stretch"},
        {"wavenumber": 1637, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide I"},
        {"wavenumber": 1541, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide II"},
        {"wavenumber": 1263, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide III"},
        {"wavenumber": 929, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide V"},
        {"wavenumber": 685, "height": 1.0, "prominence": 0.9, "fwhm_cm1": 18.0, "assignment": "amide V"},
    ]
    reference_bands = [
        {"wavenumber": item["wavenumber"], "assignment": item["assignment"], "crystallinity_sensitive": False}
        for item in peaks
    ]

    evidence = build_analysis_evidence(
        "IR",
        output_parameters={
            "n_peaks": len(peaks),
            "polymer_name": "PA6",
            "polymer_score": 0.96,
            "assignment_confidence": 0.96,
            "r_squared": 0.98,
            "Xc_pct": 62.0,
            "Xc_method": "PA6_A1200_A1637_uncalibrated",
            "Xc_calibration_status": "uncalibrated_index",
            "peaks": peaks,
        },
        residual_pattern={"residual_type": "random", "summary": "baseline is calm"},
        validation_context={
            "config_snapshot": {
                "baseline_method": "rubberband",
                "normalization_method": "minmax",
                "smooth_window": 7,
                "peak_distance": 18.0,
                "peak_fit_window_cm1": 35.0,
            },
            "ir_reference_bands": {
                "polymer_name": "PA6",
                "band_count": len(reference_bands),
                "bands": reference_bands,
            },
        },
    ).to_dict()

    structure = evidence["feature_evidence"]["structure_evidence"]
    summary = evidence["constraint_summary"]

    assert structure["Xc_calibration_status"] == "uncalibrated_index"
    assert structure["paper_conclusion_ready"] is False
    assert "ir_xc_uncalibrated" in summary["triggered_names"]["soft_warn"]


def test_ir_temperature_2d_analysis_evidence_surfaces_sequence_matrix_and_cos_contracts() -> None:
    from polynexus.core.ir_engine import IRConfig, analyze_temperature_2d_series, load_project, preprocess_pipeline

    cfg = IRConfig(
        peak_height_min=0.03,
        peak_prominence_min=0.02,
        peak_distance=18.0,
        polymer_name="PA6",
    )
    spectra = load_project(str(_temperature_ir_dir()), cfg.wavenumber_range)
    processed = [preprocess_pipeline(s, cfg) for s in spectra]
    result = analyze_temperature_2d_series(processed, cfg)

    evidence = build_analysis_evidence(
        "IR",
        output_parameters=result.parameters,
        residual_pattern={"residual_type": "random", "summary": "2D sequence is stable enough for review"},
        validation_context={
            "config_snapshot": cfg.to_dict(),
            "submodule_id": "ir.temperature_2d",
        },
    ).to_dict()

    sequence = evidence["feature_evidence"]["sequence_evidence"]
    matrix = evidence["feature_evidence"]["peak_evidence"]
    cos = evidence["feature_evidence"]["transform_evidence"]
    band_tracking = evidence["feature_evidence"]["band_tracking_evidence"]
    contract = evidence["feature_evidence"]["temperature_2d_evidence"]
    summary = evidence["constraint_summary"]

    assert sequence["n_frames"] == 48
    assert sequence["stage_counts"] == {"heating": 23, "hold": 3, "cooling": 22}
    assert matrix["matrix_shape"] == (48, len(result.wavenumber))
    assert cos["sync_cross_peak_count"] == 12
    assert cos["async_cross_peak_count"] == 12
    assert contract["interpretation_ready"] is True
    assert contract["paper_conclusion_ready"] is False
    assert summary["status"] == "soft_warn"
    assert "negative_matrix_fraction_high" in summary["triggered_names"]["soft_warn"]
    assert "dynamic_signal_too_weak" not in summary["triggered_names"]["soft_warn"]
    assert "wavenumber_grid_inconsistent" not in summary["triggered_names"]["hard_fail"]
    assert matrix["dynamic_rms"] > 0.0
    assert evidence["feature_evidence"]["sequence_evidence"]["sequence_order_source"] == "filename_stage"
    assert evidence["feature_evidence"]["peak_evidence"]["wavenumber_grid_consistent"] is True
    assert cos["cross_peak_count"] >= 24
    assert cos["assigned_cross_peak_count"] > 0
    assert cos["noda_rule_interpretation_ready"] is True
    assert band_tracking["band_index_transition_support_band_count"] >= 2
    assert band_tracking["band_index_transition_reproducible"] is True
    assert band_tracking["band_index_transition_single_frame_only"] is False
    assert band_tracking["band_tracking_missing_key_band"] is False
    assert contract["band_tracking_score"] > 0.0
    assert any(item["name"] == "negative_matrix_fraction_high" for item in evidence["symptoms"])
    assert any("reduce baseline over-subtraction" in str(item) for item in evidence["actionable_symptoms"])


def test_nmr_constraint_summary_marks_fit_quality_soft_warn() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        output_parameters={
            "n_peaks": 8,
            "median_snr": 7.2,
            "quality_metrics": {"fit_quality": 0.0, "noise_mad": 0.014},
        },
        residual_pattern={"residual_type": "noise", "summary": "noise remains"},
    ).to_dict()

    summary = evidence["constraint_summary"]
    assert summary["status"] == "soft_warn"
    assert summary["triggered_counts"]["soft_warn"] == 1
    assert "fit_quality" in summary["triggered_names"]["soft_warn"]
    assert "constraint_status=soft_warn" in evidence["summary"]


def test_nmr_analysis_evidence_surfaces_signal_peak_assignment_sections() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        output_parameters={
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 4,
            "median_snr": 9.5,
            "mean_fwhm_ppm": 1.8,
            "r_squared": 0.91,
            "dominant_peak_ppm": 172.4,
            "peak_area_total": 120.0,
            "quality_noise_mad": 0.012,
            "quality_fit_quality": 2.0,
            "peak_0_assignment": "C=O (c)",
            "peak_0_phase": "c",
            "peak_0_delta_ppm": 0.4,
            "peak_0_snr": 12.0,
            "peak_1_assignment": "C=O (a)",
            "peak_1_phase": "a",
            "peak_1_delta_ppm": 0.8,
            "peak_1_snr": 10.0,
            "Xc_pct": 47.0,
            "Xc_method": "solid_13c_peak_area",
            "n_matches": 2,
        },
        residual_pattern={"residual_type": "noise", "summary": "noise remains"},
    ).to_dict()

    assert evidence["technique"] == "NMR"
    assert evidence["signal_evidence"]["median_snr"] == 9.5
    assert evidence["peak_evidence"]["peak_count"] == 4
    assert evidence["assignment_evidence"]["phase_assignment_count"] == 2
    assert evidence["assignment_evidence"]["assigned_peak_fraction"] > 0
    assert evidence["phase_evidence"]["crystalline_peak_count"] == 1
    assert evidence["phase_evidence"]["amorphous_peak_count"] == 1
    assert evidence["structure_evidence"]["Xc_assignment_status"] == "supported"
    assert "nmr_xc=supported" in evidence["summary"]


def test_nmr_low_confidence_symptoms_are_actionable() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        output_parameters={
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 1,
            "median_snr": 2.1,
            "mean_fwhm_ppm": 45.0,
            "quality_fit_quality": 0.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
        },
        residual_pattern={"residual_type": "structured", "summary": "structured residual"},
    ).to_dict()

    names = {item["name"] for item in evidence["symptoms"]}
    assert "nmr_low_snr" in names
    assert "nmr_broad_linewidth" in names
    assert "nmr_xc_assignment_missing" in names
    assert any("baseline" in item or "peak" in item for item in evidence["actionable_symptoms"])
    assert evidence["constraint_summary"]["status"] in {"soft_warn", "hard_fail"}


def test_nmr_evidence_marks_assignment_limited_xc_not_ready() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        {
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 4,
            "median_snr": 12.0,
            "mean_fwhm_ppm": 3.5,
            "r_squared": 0.91,
            "Xc_pct": 55.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "assignment_source": "generic_region",
            "generic_assignment_fraction": 1.0,
            "phase_assignment_count": 0,
            "solvent_peak_count": 0,
        },
        {},
        {},
    ).to_dict()

    assert evidence["structure_evidence"]["Xc_assignment_status"] == "assignment_limited"
    assert evidence["structure_evidence"]["paper_conclusion_ready"] is False
    assert "nmr_xc_assignment_limited" in evidence["constraint_summary"]["triggered_names"]["soft_warn"]


def test_advisor_normalizes_evidence_contract_fields() -> None:
    advisor = Advisor(retriever=_StaticRetriever(), llm_client=_StaticLLM())
    advice = advisor.advise(
        {
            "case_id": "demo",
            "technique": "WAXS",
            "polymer_name": "PA6",
            "params": {"r_squared": 0.9},
            "output_parameters": {"r_squared": 0.9},
            "residual_pattern": {"residual_type": "systematic_peak"},
            "analysis_evidence": {"technique": "WAXS"},
        }
    )

    assert advice["hypothesis"]
    assert advice["diagnosis"] == "peak_window_mismatch"
    assert advice["target_symptom"] == "systematic_peak"
    assert advice["allowed_changes"] == {"savgol_window": 15}
    assert advice["recommended_actions"][0]["name"] == "adjust_peak_window"
    assert advice["expected_evidence_change"]["residual_type"] == "more_random"
    assert advice["rollback_condition"]


def test_advisor_normalizes_string_recommended_actions_compatibly() -> None:
    advisor = Advisor(retriever=_StaticRetriever(), llm_client=_StaticLLM())
    normalized = advisor._normalize_advice(
        {
            "assessment": "warn",
            "confidence": 0.5,
            "target_symptom": "condition_axis_missing",
            "recommended_actions": ["rerun_condition_recovery"],
            "changes": {},
            "converge": False,
        }
    )

    assert normalized["assessment"] == "WARN"
    assert normalized["recommended_actions"][0]["name"] == "rerun_condition_recovery"
    assert normalized["diagnosis"] == ""
