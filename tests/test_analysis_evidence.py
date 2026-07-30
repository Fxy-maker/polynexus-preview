from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import polynexus.core.analysis_evidence_saxs as analysis_evidence_saxs
import polynexus.core.analysis_evidence_dsc as analysis_evidence_dsc
import polynexus.core.analysis_evidence_ir as analysis_evidence_ir
import polynexus.core.analysis_evidence_nmr as analysis_evidence_nmr
import polynexus.core.analysis_evidence_waxs as analysis_evidence_waxs
from polynexus.orchestrator import ParameterOrchestrator
from rag.advisor import Advisor
from rag.prompt_builder import PromptBuilder
from polynexus.core.analysis_evidence import build_analysis_evidence
from polynexus.core.analysis_evidence_ir import (
    _ir_band_support_metrics,
    _ir_match_reference_bands,
    _ir_peak_records,
    _ir_reference_band_context,
    _ir_summary_details,
    _ir_support_enrichment_bundle,
    _ir_static_feature_bundle,
    _ir_symptom_bridge_lines,
    _ir_symptoms_from_constraints,
    _ir_temperature_2d_feature_bundle,
    _ir_temperature_2d_summary_details,
)
from polynexus.core.analysis_evidence_waxs import (
    _evaluate_waxs_constraint,
    _waxs_core_feature_evidence,
    _waxs_feature_bundle,
    _waxs_peak_metrics,
    _waxs_summary_details,
    _waxs_structure_metrics,
    _waxs_temperature_feature_evidence,
    _waxs_symptoms_from_constraints,
)
from polynexus.core.analysis_evidence_constraints import (
    EvidenceConstraint,
    physical_constraint_inventory,
    summarize_constraints,
    symptom_action_hints,
)
from tests.eval.runner import EvalRunner


def _require_external_real_data_file(source_file: str, *, technique: str) -> None:
    path = Path(source_file).resolve()
    if not path.is_file():
        pytest.skip(f"external {technique} real-data fixture is unavailable: {path}")


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
    path = (
        Path(__file__).resolve().parents[1]
        / "测试数据"
        / "IR"
        / "原位变温红外"
    )
    if not path.is_dir():
        pytest.skip("external IR temperature-series fixture is unavailable")
    return path


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


def test_physical_constraint_inventory_keeps_technique_specific_rules_together() -> None:
    saxs_names = [item.name for item in physical_constraint_inventory("saxs")]
    nmr_names = [item.name for item in physical_constraint_inventory("NMR")]

    assert all(isinstance(item, EvidenceConstraint) for item in physical_constraint_inventory("saxs"))
    assert "beamstop_contamination" in saxs_names
    assert "orientation_shift_breaks_lamellar_comparison" in saxs_names
    assert "nmr_xc_assignment_limited" in nmr_names


def test_symptom_action_hints_surfaces_expected_followup_actions() -> None:
    hints = symptom_action_hints(
        "SAXS",
        "background_drift",
        {"quality_flag": "WARN:low_confidence", "validation_summary": "All checks passed"},
    )

    assert hints[0].startswith("background_drift ->")
    assert any("expected evidence change" in item for item in hints)
    assert any("current quality_flag" in item for item in hints)


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


def test_saxs_summary_details_collect_strain_and_calibration_bits() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs")
    assert spec is not None

    analysis_evidence_saxs = importlib.import_module("polynexus.core.analysis_evidence_saxs")
    assert hasattr(analysis_evidence_saxs, "_saxs_summary_details")

    details = analysis_evidence_saxs._saxs_summary_details(
        batch_evidence={
            "batch_frames": 4,
            "batch_calibration_summary": {"fallback_ratio": 1.0},
            "batch_structure_summary": {"diagnostic_only_rows": 1, "within_window_rows": 0},
        },
        condition_evidence={
            "condition_source": "strain_series",
            "condition_label": "strain",
            "strain_axis_confidence": 0.82,
        },
        structure_evidence={
            "Q_star_rel_mean": 1.08,
            "phi_void_mean": 0.034,
            "f_Herman_mean": 0.21,
            "void_detected_frames": 3,
            "porod_slope_mean": -3.18,
            "strain_reliability_status": "low_confidence",
            "dominant_phase": "microfibrillation",
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": False,
            "paper_conclusion_ready": False,
            "lc_method": "calibrated",
            "calibrated_fallback_active": True,
            "calibrated_fallback_reason": "temperature_batch_lc_calibration",
            "calibration_skipped_reason": "missing_reference_crystallinity",
            "lamellar_interpretation_mode": "effective",
            "melting_window_status": "near_onset",
            "lc_reliability_status": "diagnostic_only",
        },
        stability_evidence={"stability_score": 0.74},
        raw_structure_evidence={"raw_structure_available": True},
    )

    assert details["summary_bits"] == [
        "batch_frames=4",
        "condition_source=strain_series",
        "strain_axis=0.82",
        "Q_star_rel=1.08",
        "phi_void=0.034",
        "f_Herman=0.21",
        "void_frames=3",
        "porod_slope=-3.18",
        "strain_status=low_confidence",
        "dominant_phase=microfibrillation",
        "paper_figure_candidate=True",
        "paper_candidate=False",
        "paper_ready=False",
        "fallback_ratio=1.0",
        "stability=0.74",
        "raw_structure_available=True",
        "lc_method=calibrated",
        "fallback=temperature_batch_lc_calibration",
        "calibration_skip=missing_reference_crystallinity",
        "lamellar_mode=effective",
        "melting_window=near_onset",
        "lc_status=diagnostic_only",
        "diagnostic_lc_rows=1",
        "melting_window_rows=0",
    ]


def test_saxs_stability_evidence_collects_scores_coverage_and_strain_flags() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs")
    assert spec is not None

    analysis_evidence_saxs = importlib.import_module("polynexus.core.analysis_evidence_saxs")
    assert hasattr(analysis_evidence_saxs, "_build_saxs_stability_evidence")

    stability = analysis_evidence_saxs._build_saxs_stability_evidence(
        {
            "quality_score": 0.72,
            "L_confidence": 0.58,
            "lc_confidence": 0.41,
            "q_peak_snr": 2.7,
            "q_peak_diff_pct": 3.1,
            "L_bragg": 12.4,
            "L_corr_peak": 11.6,
            "L_nm": 12.1,
            "lc_tangent_nm": 4.1,
            "lc_gamma_min_nm": 4.6,
            "lc_idf_nm": 4.4,
            "phi_c": 0.355,
            "phi_c_invariant": 0.34,
            "batch_frames": 4,
            "condition_label": "strain",
            "condition_continuity_score": 0.74,
            "condition_confidence": 0.82,
            "condition_missing_frames": 1,
            "strain_reliability_status": "low_confidence",
            "strain_reliability_reason": "strain_axis_low_confidence|low_q_void_dominant",
            "phase_ambiguous_frame_count": 1,
            "frame_low_conf_count": 1,
            "void_dominant_frame_count": 2,
            "effective_param_ratio": 0.67,
        },
        symptoms=[
            {"name": "low_q_void_dominant"},
            {"name": "strain_void_lamellar_conflict"},
        ],
    )

    assert stability["condition_frame_coverage"] == 0.75
    assert stability["strain_reliability_status"] == "low_confidence"
    assert stability["phase_ambiguous_frame_count"] == 1
    assert stability["frame_low_conf_count"] == 1
    assert stability["void_dominant_frame_count"] == 2
    assert stability["parameter_stability_score"] > 0.0
    assert stability["method_agreement_score"] > 0.0
    assert stability["batch_continuity_score"] < 0.8
    assert "strain_reliability_low" in stability["stability_flags"]
    assert "phase_ambiguous" in stability["stability_flags"]
    assert "void_dominant" in stability["stability_flags"]


def test_analysis_evidence_saxs_reuses_post_helpers_from_saxs_post_module() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_post")
    assert spec is not None

    analysis_evidence_saxs_post = importlib.import_module("polynexus.core.analysis_evidence_saxs_post")

    assert (
        analysis_evidence_saxs._build_saxs_stability_evidence
        is analysis_evidence_saxs_post._build_saxs_stability_evidence
    )
    assert (
        analysis_evidence_saxs._saxs_summary_details
        is analysis_evidence_saxs_post._saxs_summary_details
    )
    assert (
        analysis_evidence_saxs._saxs_post_analysis_bundle
        is analysis_evidence_saxs_post._saxs_post_analysis_bundle
    )


def test_analysis_evidence_saxs_post_reuses_stability_and_summary_modules() -> None:
    stability_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_post_stability")
    summary_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_post_summary")
    assert stability_spec is not None
    assert summary_spec is not None

    analysis_evidence_saxs_post = importlib.import_module("polynexus.core.analysis_evidence_saxs_post")
    analysis_evidence_saxs_post_stability = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_post_stability"
    )
    analysis_evidence_saxs_post_summary = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_post_summary"
    )

    assert (
        analysis_evidence_saxs_post._build_saxs_stability_evidence
        is analysis_evidence_saxs_post_stability._build_saxs_stability_evidence
    )
    assert (
        analysis_evidence_saxs_post._saxs_post_analysis_bundle
        is analysis_evidence_saxs_post_stability._saxs_post_analysis_bundle
    )
    assert (
        analysis_evidence_saxs_post._saxs_summary_details
        is analysis_evidence_saxs_post_summary._saxs_summary_details
    )


def test_analysis_evidence_saxs_post_stability_reuses_score_and_strain_modules() -> None:
    score_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_post_stability_score")
    strain_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_post_stability_strain")
    assert score_spec is not None
    assert strain_spec is not None

    analysis_evidence_saxs_post_stability = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_post_stability"
    )
    analysis_evidence_saxs_post_stability_score = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_post_stability_score"
    )
    analysis_evidence_saxs_post_stability_strain = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_post_stability_strain"
    )

    assert (
        analysis_evidence_saxs_post_stability._saxs_stability_core_scores
        is analysis_evidence_saxs_post_stability_score._saxs_stability_core_scores
    )
    assert (
        analysis_evidence_saxs_post_stability._saxs_stability_strain_adjustments
        is analysis_evidence_saxs_post_stability_strain._saxs_stability_strain_adjustments
    )


def test_analysis_evidence_saxs_reuses_condition_context_core_and_constraints_modules() -> None:
    condition_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_condition")
    context_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_context")
    core_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_core")
    constraints_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_constraints")
    assert condition_spec is not None
    assert context_spec is not None
    assert core_spec is not None
    assert constraints_spec is not None

    analysis_evidence_saxs_condition = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_condition"
    )
    analysis_evidence_saxs_context = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_context"
    )
    analysis_evidence_saxs_core = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_core"
    )
    analysis_evidence_saxs_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_constraints"
    )

    assert analysis_evidence_saxs._condition_values is analysis_evidence_saxs_condition._condition_values
    assert (
        analysis_evidence_saxs._saxs_condition_feature_bundle
        is analysis_evidence_saxs_condition._saxs_condition_feature_bundle
    )
    assert analysis_evidence_saxs._saxs_context_bundle is analysis_evidence_saxs_context._saxs_context_bundle
    assert analysis_evidence_saxs._saxs_core_feature_bundle is analysis_evidence_saxs_core._saxs_core_feature_bundle
    assert (
        analysis_evidence_saxs._SAXS_CONSTRAINT_NAMES
        is analysis_evidence_saxs_constraints._SAXS_CONSTRAINT_NAMES
    )
    assert (
        analysis_evidence_saxs._evaluate_saxs_constraint
        is analysis_evidence_saxs_constraints._evaluate_saxs_constraint
    )


def test_analysis_evidence_reuses_saxs_constraint_helper_from_saxs_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._evaluate_saxs_constraint
        is analysis_evidence_saxs._evaluate_saxs_constraint
    )


def test_evaluate_saxs_constraint_keeps_condition_sequence_and_void_rules() -> None:
    assert hasattr(analysis_evidence_saxs, "_evaluate_saxs_constraint")

    missing_triggered, missing_observed = analysis_evidence_saxs._evaluate_saxs_constraint(
        "missing_condition_axis",
        {
            "condition_label": "strain",
            "file": "check-strain-series.dat",
        },
        None,
        [],
    )
    sequence_triggered, sequence_observed = analysis_evidence_saxs._evaluate_saxs_constraint(
        "strain_sequence_nonmonotonic",
        {
            "condition_label": "strain",
        },
        None,
        [
            {"strain_pct": 0.0},
            {"strain_pct": 8.0},
            {"strain_pct": 6.0},
        ],
    )
    low_q_triggered, low_q_observed = analysis_evidence_saxs._evaluate_saxs_constraint(
        "low_q_void_dominant",
        {
            "has_voids_row_count": 2,
            "phi_void_mean": 0.034,
            "phi_void_span": 0.017,
            "porod_slope_mean": -3.18,
            "Q_star_valid": False,
        },
        None,
        [],
    )
    anchor_triggered, anchor_observed = analysis_evidence_saxs._evaluate_saxs_constraint(
        "lamellar_anchor_lost_under_strain",
        {
            "condition_label": "strain",
            "has_voids": True,
            "L_bragg": 11.8,
            "L_corr_peak": 9.9,
            "L_best": 12.1,
            "Q_star_valid": False,
        },
        None,
        [],
    )
    orientation_triggered, orientation_observed = analysis_evidence_saxs._evaluate_saxs_constraint(
        "orientation_shift_breaks_lamellar_comparison",
        {
            "condition_label": "strain",
            "f_Herman_mean": 0.21,
            "f_Herman_span": 0.54,
            "Q_star_rel_span": 0.11,
        },
        None,
        [],
    )

    assert missing_triggered is True
    assert missing_observed["condition_label"] == "strain"
    assert missing_observed["file"] == "check-strain-series.dat"

    assert sequence_triggered is True
    assert sequence_observed["strain_values"] == [0.0, 8.0, 6.0]
    assert sequence_observed["sequence_direction"] == "mixed"

    assert low_q_triggered is True
    assert low_q_observed["has_voids"] is True
    assert low_q_observed["phi_void"] == 0.034
    assert low_q_observed["Q_star_valid"] is False

    assert anchor_triggered is True
    assert round(anchor_observed["l_spread"], 3) == 0.182
    assert anchor_observed["Q_star_valid"] is False

    assert orientation_triggered is True
    assert orientation_observed["f_Herman"] == 0.21
    assert orientation_observed["f_Herman_span"] == 0.54
    assert orientation_observed["Q_star_rel_span"] == 0.11


def test_analysis_evidence_reuses_saxs_condition_feature_bundle_from_saxs_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._saxs_condition_feature_bundle
        is analysis_evidence_saxs._saxs_condition_feature_bundle
    )


def test_analysis_evidence_saxs_condition_reuses_value_sequence_and_structure_modules() -> None:
    values_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_condition_values")
    sequence_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_condition_sequence")
    structure_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_saxs_condition_structure")
    assert values_spec is not None
    assert sequence_spec is not None
    assert structure_spec is not None

    analysis_evidence_saxs_condition = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_condition"
    )
    analysis_evidence_saxs_condition_values = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_condition_values"
    )
    analysis_evidence_saxs_condition_sequence = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_condition_sequence"
    )
    analysis_evidence_saxs_condition_structure = importlib.import_module(
        "polynexus.core.analysis_evidence_saxs_condition_structure"
    )

    assert (
        analysis_evidence_saxs_condition._condition_values
        is analysis_evidence_saxs_condition_values._condition_values
    )
    assert (
        analysis_evidence_saxs_condition._saxs_strain_sequence_evidence
        is analysis_evidence_saxs_condition_sequence._saxs_strain_sequence_evidence
    )
    assert (
        analysis_evidence_saxs_condition._saxs_strain_structure_layers
        is analysis_evidence_saxs_condition_structure._saxs_strain_structure_layers
    )


def test_saxs_condition_feature_bundle_collects_sequence_phase_and_structure_layers() -> None:
    assert hasattr(analysis_evidence_saxs, "_saxs_condition_feature_bundle")

    bundle = analysis_evidence_saxs._saxs_condition_feature_bundle(
        {
            "condition_label": "strain",
            "condition_source": "strain_series",
            "condition_source_text": "strain_0_16",
            "condition_confidence": 0.82,
            "condition_continuity_score": 0.74,
            "Q_star_rel_mean": 1.08,
            "Q_star_rel_span": 0.11,
            "phi_void_mean": 0.034,
            "phi_void_span": 0.017,
            "f_Herman_mean": 0.21,
            "f_Herman_span": 0.54,
            "porod_slope_mean": -3.18,
            "void_detected_frames": 3,
            "phase_distribution": {"elastic": 1, "plastic_voiding": 1, "microfibrillation": 1},
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
        },
        batch_rows=[
            {"file": "f0.dat", "strain_pct": 0.0},
            {"file": "f1.dat", "strain_pct": 8.0},
            {"file": "f2.dat", "strain_pct": 16.0},
        ],
        structure_evidence={"L_bragg": 11.8},
    )

    assert bundle["condition_evidence"]["sequence_direction"] == "increasing"
    assert bundle["condition_evidence"]["strain_values"] == [0.0, 8.0, 16.0]
    assert bundle["feature_evidence"]["sequence_evidence"]["strain_min_pct"] == 0.0
    assert bundle["feature_evidence"]["strain_structure_evidence"]["Q_star_rel_mean"] == 1.08
    assert bundle["feature_evidence"]["strain_phase_evidence"]["dominant_phase"] == "microfibrillation"
    assert bundle["structure_evidence"]["L_bragg"] == 11.8
    assert bundle["structure_evidence"]["strain_reliability_status"] == "low_confidence"
    assert bundle["structure_evidence"]["paper_figure_candidate"] is True
    assert bundle["confidence_signals"] == [
        {"name": "strain_axis_confidence", "value": 0.82, "source": "SAXS_strain"}
    ]


def test_analysis_evidence_reuses_saxs_context_bundle_from_saxs_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._saxs_context_bundle
        is analysis_evidence_saxs._saxs_context_bundle
    )


def test_saxs_context_bundle_collects_raw_snapshot_and_batch_layers() -> None:
    assert hasattr(analysis_evidence_saxs, "_saxs_context_bundle")

    bundle = analysis_evidence_saxs._saxs_context_bundle(
        {
            "batch_frames": 3,
            "condition_label": "Temperature",
            "condition_range": "100.0-120.0",
            "batch_calibration_summary": {
                "fallback_ratio": 1.0,
                "raw_structure_available": True,
            },
            "batch_structure_summary": {
                "diagnostic_only_rows": 1,
                "within_window_rows": 0,
            },
            "raw_snapshot": {
                "long_period": {"L_best": 10.0},
                "structure": {"L": 10.0, "lc": 3.2, "la": 6.8, "phi_c": 0.32, "confidence_lc": 0.31, "Q_invariant": 18.2},
            },
        },
        batch_rows=[
            {
                "file": "frame_001.edf",
                "temperature_C": 100.0,
                "melting_window_status": "outside_window",
                "lc_reliability_status": "usable",
            },
            {
                "file": "frame_002.edf",
                "temperature_C": 110.0,
                "melting_window_status": "near_onset",
                "lc_reliability_status": "diagnostic_only",
            },
            {
                "file": "frame_003.edf",
                "temperature_C": 120.0,
                "melting_window_status": "near_onset",
                "lc_reliability_status": "diagnostic_only",
            },
        ],
    )

    assert bundle["raw_structure_evidence"]["L_nm_raw"] == 10.0
    assert bundle["raw_structure_evidence"]["lc_nm_raw"] == 3.2
    assert bundle["raw_structure_evidence"]["raw_structure_available"] is True
    assert bundle["batch_evidence"]["batch_frames"] == 3
    assert bundle["batch_evidence"]["condition_label"] == "Temperature"
    assert bundle["batch_evidence"]["sample_files"] == ["frame_001.edf", "frame_002.edf", "frame_003.edf"]
    assert bundle["batch_evidence"]["frame_condition_values"][1]["temperature_C"] == 110.0
    assert bundle["batch_evidence"]["frame_condition_values"][1]["lc_reliability_status"] == "diagnostic_only"
    assert bundle["feature_evidence"]["raw_structure_evidence"] == bundle["raw_structure_evidence"]


def test_analysis_evidence_reuses_saxs_core_feature_bundle_from_saxs_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._saxs_core_feature_bundle
        is analysis_evidence_saxs._saxs_core_feature_bundle
    )


def test_saxs_core_feature_bundle_collects_signal_peak_transform_and_structure_layers() -> None:
    assert hasattr(analysis_evidence_saxs, "_saxs_core_feature_bundle")

    bundle = analysis_evidence_saxs._saxs_core_feature_bundle(
        {
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
        },
        quality_flag="WARN:low_confidence",
        validation_summary="WARN: low-q region remains uncertain",
    )

    assert bundle["signal_evidence"]["q_peak_snr"] == 2.7
    assert bundle["signal_evidence"]["Q_star_valid"] is False
    assert bundle["peak_evidence"]["L_bragg"] == 12.4
    assert bundle["peak_evidence"]["fit_regions"][1]["region"] == "correlation"
    assert bundle["transform_evidence"]["lc_tangent_nm"] == 4.1
    assert bundle["structure_evidence"]["lc_method"] == "tangent_strain_qstar_warn"
    assert bundle["structure_evidence"]["Q_star_abs"] == 12.3
    assert bundle["structure_evidence"]["sasmodels_model_used"] == "lamellar_hg"


def test_analysis_evidence_reuses_saxs_post_analysis_bundle_from_saxs_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._saxs_post_analysis_bundle
        is analysis_evidence_saxs._saxs_post_analysis_bundle
    )


def test_saxs_post_analysis_bundle_collects_stability_signals_and_actionable_lines() -> None:
    assert hasattr(analysis_evidence_saxs, "_saxs_post_analysis_bundle")

    bundle = analysis_evidence_saxs._saxs_post_analysis_bundle(
        {
            "quality_score": 0.72,
            "L_confidence": 0.58,
            "lc_confidence": 0.41,
            "q_peak_snr": 2.7,
            "q_peak_diff_pct": 3.1,
            "L_bragg": 12.4,
            "L_corr_peak": 11.6,
            "L_nm": 12.1,
            "lc_tangent_nm": 4.1,
            "lc_gamma_min_nm": 4.6,
            "lc_idf_nm": 4.4,
            "phi_c": 0.355,
            "phi_c_invariant": 0.34,
            "batch_frames": 4,
            "condition_label": "strain",
            "condition_continuity_score": 0.74,
            "condition_confidence": 0.82,
            "condition_missing_frames": 1,
            "strain_reliability_status": "low_confidence",
            "phase_ambiguous_frame_count": 1,
            "frame_low_conf_count": 1,
            "void_dominant_frame_count": 2,
            "effective_param_ratio": 0.67,
        },
        symptoms=[
            {"name": "gamma_tangent_unstable", "target_params": ["correlation_window"]},
            {"name": "low_q_void_dominant", "target_params": ["low_q_mask"]},
        ],
        constraint_summary={
            "triggered_names": {
                "soft_warn": ["fit_regions_unstable"],
            }
        },
    )

    assert bundle["stability_evidence"]["stability_score"] > 0.0
    assert bundle["feature_evidence"]["stability_evidence"] == bundle["stability_evidence"]
    assert [item["name"] for item in bundle["confidence_signals"]] == [
        "stability_score",
        "parameter_stability_score",
        "method_agreement_score",
        "batch_continuity_score",
    ]
    assert any("gamma_tangent_unstable -> correlation_window" in item for item in bundle["actionable_symptoms"])
    assert any("fit_regions_unstable -> do not trust pretty figures" in item for item in bundle["actionable_symptoms"])


def test_analysis_evidence_reuses_waxs_actionable_constraint_lines_from_waxs_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._waxs_actionable_constraint_lines
        is analysis_evidence_waxs._waxs_actionable_constraint_lines
    )


def test_analysis_evidence_waxs_reuses_post_helpers_from_waxs_post_module() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_post")
    assert spec is not None

    analysis_evidence_waxs_post = importlib.import_module("polynexus.core.analysis_evidence_waxs_post")

    assert (
        analysis_evidence_waxs._waxs_summary_details
        is analysis_evidence_waxs_post._waxs_summary_details
    )
    assert (
        analysis_evidence_waxs._waxs_actionable_constraint_lines
        is analysis_evidence_waxs_post._waxs_actionable_constraint_lines
    )
    assert (
        analysis_evidence_waxs._waxs_symptoms_from_constraints
        is analysis_evidence_waxs_post._waxs_symptoms_from_constraints
    )


def test_analysis_evidence_waxs_post_reuses_summary_guidance_and_symptom_modules() -> None:
    summary_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_post_summary")
    guidance_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_post_guidance")
    symptoms_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_post_symptoms")
    assert summary_spec is not None
    assert guidance_spec is not None
    assert symptoms_spec is not None

    analysis_evidence_waxs_post = importlib.import_module("polynexus.core.analysis_evidence_waxs_post")
    analysis_evidence_waxs_post_summary = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_post_summary"
    )
    analysis_evidence_waxs_post_guidance = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_post_guidance"
    )
    analysis_evidence_waxs_post_symptoms = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_post_symptoms"
    )

    assert (
        analysis_evidence_waxs_post._waxs_summary_details
        is analysis_evidence_waxs_post_summary._waxs_summary_details
    )
    assert (
        analysis_evidence_waxs_post._waxs_actionable_constraint_lines
        is analysis_evidence_waxs_post_guidance._waxs_actionable_constraint_lines
    )
    assert (
        analysis_evidence_waxs_post._waxs_symptoms_from_constraints
        is analysis_evidence_waxs_post_symptoms._waxs_symptoms_from_constraints
    )


def test_analysis_evidence_waxs_reuses_metrics_bundle_and_constraint_modules() -> None:
    metrics_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_metrics")
    bundle_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_feature_bundle")
    constraints_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_constraints")
    assert metrics_spec is not None
    assert bundle_spec is not None
    assert constraints_spec is not None

    analysis_evidence_waxs_metrics = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_metrics"
    )
    analysis_evidence_waxs_feature_bundle = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_feature_bundle"
    )
    analysis_evidence_waxs_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_constraints"
    )

    assert analysis_evidence_waxs._waxs_peak_metrics is analysis_evidence_waxs_metrics._waxs_peak_metrics
    assert (
        analysis_evidence_waxs._waxs_structure_metrics
        is analysis_evidence_waxs_metrics._waxs_structure_metrics
    )
    assert (
        analysis_evidence_waxs._waxs_core_feature_evidence
        is analysis_evidence_waxs_feature_bundle._waxs_core_feature_evidence
    )
    assert (
        analysis_evidence_waxs._waxs_temperature_feature_evidence
        is analysis_evidence_waxs_feature_bundle._waxs_temperature_feature_evidence
    )
    assert (
        analysis_evidence_waxs._waxs_feature_bundle
        is analysis_evidence_waxs_feature_bundle._waxs_feature_bundle
    )
    assert (
        analysis_evidence_waxs._WAXS_CONSTRAINT_NAMES
        is analysis_evidence_waxs_constraints._WAXS_CONSTRAINT_NAMES
    )
    assert (
        analysis_evidence_waxs._evaluate_waxs_constraint
        is analysis_evidence_waxs_constraints._evaluate_waxs_constraint
    )


def test_analysis_evidence_waxs_constraints_reuse_context_and_rule_modules() -> None:
    context_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_waxs_constraints_context"
    )
    peak_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_constraints_peak")
    crystallinity_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_waxs_constraints_crystallinity"
    )
    assert context_spec is not None
    assert peak_spec is not None
    assert crystallinity_spec is not None

    analysis_evidence_waxs_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_constraints"
    )
    analysis_evidence_waxs_constraints_context = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_constraints_context"
    )
    analysis_evidence_waxs_constraints_peak = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_constraints_peak"
    )
    analysis_evidence_waxs_constraints_crystallinity = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_constraints_crystallinity"
    )

    assert (
        analysis_evidence_waxs_constraints._waxs_constraint_context
        is analysis_evidence_waxs_constraints_context._waxs_constraint_context
    )
    assert (
        analysis_evidence_waxs_constraints._evaluate_waxs_peak_constraint
        is analysis_evidence_waxs_constraints_peak._evaluate_waxs_peak_constraint
    )
    assert (
        analysis_evidence_waxs_constraints._evaluate_waxs_crystallinity_constraint
        is analysis_evidence_waxs_constraints_crystallinity._evaluate_waxs_crystallinity_constraint
    )


def test_analysis_evidence_waxs_feature_bundle_reuses_core_and_temperature_modules() -> None:
    core_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_waxs_feature_bundle_core")
    temperature_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_waxs_feature_bundle_temperature"
    )
    assert core_spec is not None
    assert temperature_spec is not None

    analysis_evidence_waxs_feature_bundle = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_feature_bundle"
    )
    analysis_evidence_waxs_feature_bundle_core = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_feature_bundle_core"
    )
    analysis_evidence_waxs_feature_bundle_temperature = importlib.import_module(
        "polynexus.core.analysis_evidence_waxs_feature_bundle_temperature"
    )

    assert (
        analysis_evidence_waxs_feature_bundle._waxs_core_feature_evidence
        is analysis_evidence_waxs_feature_bundle_core._waxs_core_feature_evidence
    )
    assert (
        analysis_evidence_waxs_feature_bundle._waxs_temperature_feature_evidence
        is analysis_evidence_waxs_feature_bundle_temperature._waxs_temperature_feature_evidence
    )


def test_waxs_actionable_constraint_lines_keep_scherrer_followup_text() -> None:
    assert hasattr(analysis_evidence_waxs, "_waxs_actionable_constraint_lines")

    lines = analysis_evidence_waxs._waxs_actionable_constraint_lines(
        {
            "scherrer_instrument_broadening_unresolved",
            "scherrer_jump_single_frame",
            "scherrer_dominated_by_peak_width_noise",
        }
    )

    assert lines == [
        "scherrer_instrument_broadening_unresolved -> keep D provisional until instrument broadening is modeled or documented",
        "scherrer_jump_single_frame -> review the unstable frame before trusting the temperature trend",
        "scherrer_dominated_by_peak_width_noise -> stabilize peak widths and family tracking before promoting D",
    ]


def test_analysis_evidence_common_summary_details_collect_prefix_bits() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_common")
    assert spec is not None

    analysis_evidence_common = importlib.import_module("polynexus.core.analysis_evidence_common")
    assert hasattr(analysis_evidence_common, "_common_summary_details")

    details = analysis_evidence_common._common_summary_details(
        quality_flag="WARN:low_confidence",
        residual_type="baseline_drift",
        risk_flags=["beamstop_contamination", "beamstop_contamination", "mask_truncated"],
        constraints=[{"name": "c1"}, {"name": "c2"}],
        constraint_summary={"status": "hard_fail", "triggered_total": 2},
    )

    assert details["summary_bits"] == [
        "quality=WARN:low_confidence",
        "residual=baseline_drift",
        "risks=2",
        "constraints=2",
        "constraint_status=hard_fail",
        "triggered_constraints=2",
    ]


def test_analysis_evidence_common_collect_source_fields_deduplicates_and_sorts() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_common")
    assert spec is not None

    analysis_evidence_common = importlib.import_module("polynexus.core.analysis_evidence_common")
    assert hasattr(analysis_evidence_common, "_collect_source_fields")

    fields = analysis_evidence_common._collect_source_fields(
        fit_evidence={"r_squared": 0.91},
        physical_evidence={"quality_score": 0.72},
        residual_evidence={"residual_type": "noise"},
        feature_evidence={"signal_evidence": {"q_peak_snr": 2.7}},
        signal_evidence={"median_snr": 9.5},
        peak_evidence={"peak_count": 4},
        reference_evidence={"source": "db"},
        background_evidence={"baseline_method": "rubberband"},
        phase_evidence={"crystalline_peak_count": 1},
        transform_evidence={"lc_tangent_nm": 4.1},
        structure_evidence={"lc_method": "calibrated"},
        raw_structure_evidence={"raw_structure_available": True},
        batch_evidence={"batch_frames": 3},
        condition_evidence={"condition_source": "header"},
        stability_evidence={"stability_score": 0.74},
        symptoms=[{"name": "peak_window_mismatch"}],
    )

    assert fields == [
        "baseline_method",
        "batch_frames",
        "condition_source",
        "crystalline_peak_count",
        "lc_method",
        "lc_tangent_nm",
        "median_snr",
        "peak_count",
        "quality_score",
        "r_squared",
        "raw_structure_available",
        "residual_type",
        "signal_evidence",
        "source",
        "stability_score",
        "symptoms",
    ]


def test_analysis_evidence_reuses_xray_common_feature_bundle_from_common_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")
    analysis_evidence_common = importlib.import_module("polynexus.core.analysis_evidence_common")

    assert (
        analysis_evidence_module._xray_common_feature_bundle
        is analysis_evidence_common._xray_common_feature_bundle
    )


def test_analysis_evidence_modules_reuse_shared_helpers_from_utils_module() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_utils")
    assert spec is not None

    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")
    analysis_evidence_utils = importlib.import_module("polynexus.core.analysis_evidence_utils")

    assert analysis_evidence_module._clean_float is analysis_evidence_utils._clean_float
    assert analysis_evidence_module._clamp_unit is analysis_evidence_utils._clamp_unit
    assert analysis_evidence_module._mean_finite is analysis_evidence_utils._mean_finite
    assert analysis_evidence_module._relative_spread is analysis_evidence_utils._relative_spread
    assert analysis_evidence_module._inverse_ratio_score is analysis_evidence_utils._inverse_ratio_score
    assert analysis_evidence_module._match_constraint_value is analysis_evidence_utils._match_constraint_value
    assert analysis_evidence_module._non_empty_mapping is analysis_evidence_utils._non_empty_mapping
    assert analysis_evidence_module._shape_tuple is analysis_evidence_utils._shape_tuple
    assert analysis_evidence_module._safe_int is analysis_evidence_utils._safe_int
    assert analysis_evidence_ir._clean_float is analysis_evidence_utils._clean_float
    assert analysis_evidence_ir._clamp_unit is analysis_evidence_utils._clamp_unit
    assert analysis_evidence_ir._relative_spread is analysis_evidence_utils._relative_spread
    assert analysis_evidence_ir._non_empty_mapping is analysis_evidence_utils._non_empty_mapping
    assert analysis_evidence_ir._extract_nested_mapping is analysis_evidence_utils._extract_nested_mapping
    assert analysis_evidence_ir._safe_int is analysis_evidence_utils._safe_int
    assert analysis_evidence_saxs._clean_float is analysis_evidence_utils._clean_float
    assert analysis_evidence_saxs._relative_spread is analysis_evidence_utils._relative_spread
    assert analysis_evidence_saxs._non_empty_mapping is analysis_evidence_utils._non_empty_mapping
    assert analysis_evidence_saxs._extract_nested_mapping is analysis_evidence_utils._extract_nested_mapping
    assert analysis_evidence_saxs._safe_int is analysis_evidence_utils._safe_int
    assert analysis_evidence_dsc._clean_float is analysis_evidence_utils._clean_float
    assert analysis_evidence_dsc._non_empty_mapping is analysis_evidence_utils._non_empty_mapping
    assert analysis_evidence_dsc._safe_int is analysis_evidence_utils._safe_int
    assert analysis_evidence_dsc._clamp_unit is analysis_evidence_utils._clamp_unit
    assert analysis_evidence_dsc._mean_finite is analysis_evidence_utils._mean_finite
    assert analysis_evidence_dsc._relative_spread is analysis_evidence_utils._relative_spread
    assert analysis_evidence_waxs._clean_float is analysis_evidence_utils._clean_float
    assert analysis_evidence_waxs._safe_int is analysis_evidence_utils._safe_int
    assert analysis_evidence_waxs._relative_spread is analysis_evidence_utils._relative_spread
    assert analysis_evidence_waxs._clamp_unit is analysis_evidence_utils._clamp_unit
    assert analysis_evidence_waxs._mean_finite is analysis_evidence_utils._mean_finite
    assert analysis_evidence_waxs._inverse_ratio_score is analysis_evidence_utils._inverse_ratio_score
    assert analysis_evidence_waxs._non_empty_mapping is analysis_evidence_utils._non_empty_mapping
    assert analysis_evidence_nmr._clean_float is analysis_evidence_utils._clean_float
    assert analysis_evidence_nmr._non_empty_mapping is analysis_evidence_utils._non_empty_mapping
    assert analysis_evidence_nmr._safe_int is analysis_evidence_utils._safe_int


def test_analysis_evidence_reuses_physical_helpers_from_physical_module() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_physical")
    assert spec is not None

    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")
    analysis_evidence_physical = importlib.import_module(
        "polynexus.core.analysis_evidence_physical"
    )

    assert (
        analysis_evidence_module._is_ir_temperature_2d
        is analysis_evidence_physical._is_ir_temperature_2d
    )
    assert (
        analysis_evidence_module._ir_temperature_2d_metrics
        is analysis_evidence_physical._ir_temperature_2d_metrics
    )
    assert (
        analysis_evidence_module.evaluate_physical_constraints
        is analysis_evidence_physical.evaluate_physical_constraints
    )


def test_analysis_evidence_physical_reuses_constraint_evaluator_from_dedicated_module() -> None:
    evaluator_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_evaluator")
    assert evaluator_spec is not None

    analysis_evidence_physical = importlib.import_module("polynexus.core.analysis_evidence_physical")
    analysis_evidence_constraint_evaluator = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_evaluator"
    )

    assert (
        analysis_evidence_physical.evaluate_physical_constraints
        is analysis_evidence_constraint_evaluator.evaluate_physical_constraints
    )


def test_analysis_evidence_physical_reuses_ir_temperature_2d_helpers_from_dedicated_module() -> None:
    ir_2d_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d"
    )
    assert ir_2d_spec is not None

    analysis_evidence_physical = importlib.import_module(
        "polynexus.core.analysis_evidence_physical"
    )
    analysis_evidence_physical_ir_temperature_2d = importlib.import_module(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d"
    )

    assert (
        analysis_evidence_physical._is_ir_temperature_2d
        is analysis_evidence_physical_ir_temperature_2d._is_ir_temperature_2d
    )
    assert (
        analysis_evidence_physical._ir_temperature_2d_metrics
        is analysis_evidence_physical_ir_temperature_2d._ir_temperature_2d_metrics
    )


def test_analysis_evidence_physical_ir_temperature_2d_reuses_context_and_score_modules() -> None:
    context_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d_context"
    )
    score_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d_scores"
    )
    assert context_spec is not None
    assert score_spec is not None

    analysis_evidence_physical_ir_temperature_2d = importlib.import_module(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d"
    )
    analysis_evidence_physical_ir_temperature_2d_context = importlib.import_module(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d_context"
    )
    analysis_evidence_physical_ir_temperature_2d_scores = importlib.import_module(
        "polynexus.core.analysis_evidence_physical_ir_temperature_2d_scores"
    )

    assert (
        analysis_evidence_physical_ir_temperature_2d._ir_temperature_2d_metric_context
        is analysis_evidence_physical_ir_temperature_2d_context._ir_temperature_2d_metric_context
    )
    assert (
        analysis_evidence_physical_ir_temperature_2d._ir_temperature_2d_metric_scores
        is analysis_evidence_physical_ir_temperature_2d_scores._ir_temperature_2d_metric_scores
    )


def test_analysis_evidence_reuses_model_and_builder_from_dedicated_modules() -> None:
    models_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_models")
    builder_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_builder")
    assert models_spec is not None
    assert builder_spec is not None

    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")
    analysis_evidence_models = importlib.import_module("polynexus.core.analysis_evidence_models")
    analysis_evidence_builder = importlib.import_module("polynexus.core.analysis_evidence_builder")

    assert analysis_evidence_module.AnalysisEvidence is analysis_evidence_models.AnalysisEvidence
    assert (
        analysis_evidence_module.build_analysis_evidence
        is analysis_evidence_builder.build_analysis_evidence
    )


def test_analysis_evidence_builder_reuses_summary_helper_from_summary_module() -> None:
    summary_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_summary")
    assert summary_spec is not None

    analysis_evidence_builder = importlib.import_module("polynexus.core.analysis_evidence_builder")
    analysis_evidence_summary = importlib.import_module("polynexus.core.analysis_evidence_summary")

    assert (
        analysis_evidence_builder.build_analysis_summary
        is analysis_evidence_summary.build_analysis_summary
    )


def test_analysis_evidence_builder_reuses_postprocess_helper_from_postprocess_module() -> None:
    postprocess_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_postprocess")
    assert postprocess_spec is not None

    analysis_evidence_builder = importlib.import_module("polynexus.core.analysis_evidence_builder")
    analysis_evidence_postprocess = importlib.import_module(
        "polynexus.core.analysis_evidence_postprocess"
    )

    assert (
        analysis_evidence_builder.build_analysis_postprocess
        is analysis_evidence_postprocess.build_analysis_postprocess
    )


def test_analysis_evidence_builder_reuses_finalizer_helper_from_finalize_module() -> None:
    finalize_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_finalize")
    assert finalize_spec is not None

    analysis_evidence_builder = importlib.import_module("polynexus.core.analysis_evidence_builder")
    analysis_evidence_finalize = importlib.import_module(
        "polynexus.core.analysis_evidence_finalize"
    )

    assert (
        analysis_evidence_builder.finalize_analysis_evidence
        is analysis_evidence_finalize.finalize_analysis_evidence
    )


def test_analysis_evidence_builder_reuses_technique_bundle_helpers_from_dedicated_module() -> None:
    technique_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_technique_bundles")
    assert technique_spec is not None

    analysis_evidence_builder = importlib.import_module("polynexus.core.analysis_evidence_builder")
    analysis_evidence_technique_bundles = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles"
    )

    assert (
        analysis_evidence_builder.build_saxs_technique_bundle
        is analysis_evidence_technique_bundles.build_saxs_technique_bundle
    )
    assert (
        analysis_evidence_builder.build_dsc_technique_bundle
        is analysis_evidence_technique_bundles.build_dsc_technique_bundle
    )
    assert (
        analysis_evidence_builder.build_ir_technique_bundle
        is analysis_evidence_technique_bundles.build_ir_technique_bundle
    )
    assert (
        analysis_evidence_builder.build_nmr_technique_bundle
        is analysis_evidence_technique_bundles.build_nmr_technique_bundle
    )
    assert (
        analysis_evidence_builder.build_waxs_technique_bundle
        is analysis_evidence_technique_bundles.build_waxs_technique_bundle
    )


def test_analysis_evidence_technique_bundles_reuse_per_technique_modules() -> None:
    saxs_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_technique_bundles_saxs")
    dsc_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_technique_bundles_dsc")
    ir_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_technique_bundles_ir")
    nmr_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_technique_bundles_nmr")
    waxs_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_technique_bundles_waxs")
    assert saxs_spec is not None
    assert dsc_spec is not None
    assert ir_spec is not None
    assert nmr_spec is not None
    assert waxs_spec is not None

    analysis_evidence_technique_bundles = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles"
    )
    analysis_evidence_technique_bundles_saxs = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles_saxs"
    )
    analysis_evidence_technique_bundles_dsc = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles_dsc"
    )
    analysis_evidence_technique_bundles_ir = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles_ir"
    )
    analysis_evidence_technique_bundles_nmr = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles_nmr"
    )
    analysis_evidence_technique_bundles_waxs = importlib.import_module(
        "polynexus.core.analysis_evidence_technique_bundles_waxs"
    )

    assert (
        analysis_evidence_technique_bundles.build_saxs_technique_bundle
        is analysis_evidence_technique_bundles_saxs.build_saxs_technique_bundle
    )
    assert (
        analysis_evidence_technique_bundles.build_dsc_technique_bundle
        is analysis_evidence_technique_bundles_dsc.build_dsc_technique_bundle
    )
    assert (
        analysis_evidence_technique_bundles.build_ir_technique_bundle
        is analysis_evidence_technique_bundles_ir.build_ir_technique_bundle
    )
    assert (
        analysis_evidence_technique_bundles.build_nmr_technique_bundle
        is analysis_evidence_technique_bundles_nmr.build_nmr_technique_bundle
    )
    assert (
        analysis_evidence_technique_bundles.build_waxs_technique_bundle
        is analysis_evidence_technique_bundles_waxs.build_waxs_technique_bundle
    )


def test_analysis_evidence_constraints_reuses_inventory_from_dedicated_module() -> None:
    inventory_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_inventory")
    assert inventory_spec is not None

    analysis_evidence_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_constraints"
    )
    analysis_evidence_constraint_inventory = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory"
    )

    assert (
        analysis_evidence_constraints.EvidenceConstraint
        is analysis_evidence_constraint_inventory.EvidenceConstraint
    )
    assert (
        analysis_evidence_constraints.physical_constraint_inventory
        is analysis_evidence_constraint_inventory.physical_constraint_inventory
    )


def test_analysis_evidence_constraints_reuses_action_hints_from_dedicated_module() -> None:
    hints_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hints")
    assert hints_spec is not None

    analysis_evidence_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_constraints"
    )
    analysis_evidence_action_hints = importlib.import_module(
        "polynexus.core.analysis_evidence_action_hints"
    )

    assert (
        analysis_evidence_constraints.symptom_action_hints
        is analysis_evidence_action_hints.symptom_action_hints
    )


def test_analysis_evidence_action_hints_reuses_rules_from_rules_module() -> None:
    rules_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hint_rules")
    assert rules_spec is not None

    analysis_evidence_action_hints = importlib.import_module(
        "polynexus.core.analysis_evidence_action_hints"
    )
    analysis_evidence_action_hint_rules = importlib.import_module(
        "polynexus.core.analysis_evidence_action_hint_rules"
    )

    assert (
        analysis_evidence_action_hints.ACTION_HINT_MAPPING
        is analysis_evidence_action_hint_rules.ACTION_HINT_MAPPING
    )


def test_analysis_evidence_action_hint_rules_reuse_technique_modules() -> None:
    waxs_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hint_rules_waxs")
    saxs_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hint_rules_saxs")
    dsc_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hint_rules_dsc")
    ir_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hint_rules_ir")
    nmr_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_action_hint_rules_nmr")
    assert waxs_spec is not None
    assert saxs_spec is not None
    assert dsc_spec is not None
    assert ir_spec is not None
    assert nmr_spec is not None

    rules_module = importlib.import_module("polynexus.core.analysis_evidence_action_hint_rules")
    waxs_module = importlib.import_module("polynexus.core.analysis_evidence_action_hint_rules_waxs")
    saxs_module = importlib.import_module("polynexus.core.analysis_evidence_action_hint_rules_saxs")
    dsc_module = importlib.import_module("polynexus.core.analysis_evidence_action_hint_rules_dsc")
    ir_module = importlib.import_module("polynexus.core.analysis_evidence_action_hint_rules_ir")
    nmr_module = importlib.import_module("polynexus.core.analysis_evidence_action_hint_rules_nmr")

    assert rules_module.ACTION_HINT_MAPPING["WAXS"] is waxs_module.ACTION_HINT_RULES_WAXS
    assert rules_module.ACTION_HINT_MAPPING["SAXS"] is saxs_module.ACTION_HINT_RULES_SAXS
    assert rules_module.ACTION_HINT_MAPPING["DSC"] is dsc_module.ACTION_HINT_RULES_DSC
    assert rules_module.ACTION_HINT_MAPPING["IR"] is ir_module.ACTION_HINT_RULES_IR
    assert rules_module.ACTION_HINT_MAPPING["NMR"] is nmr_module.ACTION_HINT_RULES_NMR


def test_analysis_evidence_constraint_inventory_reuses_models_and_technique_modules() -> None:
    models_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_models")
    saxs_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_inventory_saxs")
    dsc_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_inventory_dsc")
    waxs_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_inventory_waxs")
    ir_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_inventory_ir")
    nmr_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_constraint_inventory_nmr")
    assert models_spec is not None
    assert saxs_spec is not None
    assert dsc_spec is not None
    assert waxs_spec is not None
    assert ir_spec is not None
    assert nmr_spec is not None

    inventory_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory"
    )
    models_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_models"
    )
    saxs_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory_saxs"
    )
    dsc_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory_dsc"
    )
    waxs_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory_waxs"
    )
    ir_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory_ir"
    )
    nmr_module = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_inventory_nmr"
    )

    assert inventory_module.EvidenceConstraint is models_module.EvidenceConstraint
    assert inventory_module._inventory is models_module._inventory
    assert inventory_module._saxs_constraint_inventory is saxs_module._saxs_constraint_inventory
    assert inventory_module._dsc_constraint_inventory is dsc_module._dsc_constraint_inventory
    assert inventory_module._waxs_constraint_inventory is waxs_module._waxs_constraint_inventory
    assert inventory_module._ir_constraint_inventory is ir_module._ir_constraint_inventory
    assert inventory_module._nmr_constraint_inventory is nmr_module._nmr_constraint_inventory


def test_xray_common_feature_bundle_collects_physical_fields_fit_regions_and_confidence_signals() -> None:
    analysis_evidence_common = importlib.import_module("polynexus.core.analysis_evidence_common")
    assert hasattr(analysis_evidence_common, "_xray_common_feature_bundle")

    bundle = analysis_evidence_common._xray_common_feature_bundle(
        "SAXS",
        {
            "quality_score": 0.72,
            "L_bragg": 12.4,
            "L_lorentz": 12.0,
            "L_corr_peak": 11.6,
            "L_nm": 12.1,
            "L_best": 12.1,
            "L_confidence": 0.58,
            "q_peak_snr": 2.7,
            "Q_star": 12.3,
            "Q_star_rel": 1.08,
            "Q_star_valid": False,
            "has_voids": True,
            "phi_void": 0.034,
            "void_AR": 2.1,
            "f_Herman": 0.21,
            "porod_slope": -3.18,
            "beam_stop_contaminated": True,
            "mask_truncated": True,
            "condition_value": 120.0,
            "condition_label": "Temperature",
            "temperature_C": 120.0,
            "fit_regions": [
                {"region": "peak", "r_squared": 0.82, "rmse": 0.12},
                {"region": "correlation", "r_squared": 0.48, "rmse": 0.21},
            ],
            "pyfai_q_peak_diff_pct": 3.4,
        },
        quality_score=0.72,
    )

    assert bundle["physical_evidence"]["L_bragg"] == 12.4
    assert bundle["physical_evidence"]["beam_stop_contaminated"] is True
    assert bundle["physical_evidence"]["condition_label"] == "Temperature"
    assert bundle["feature_evidence"]["fit_regions"][1]["region"] == "correlation"
    assert bundle["confidence_signals"] == [
        {"name": "quality_score", "value": 0.72, "source": "SAXS"},
        {"name": "q_peak_snr", "value": 2.7, "source": "SAXS"},
        {"name": "L_confidence", "value": 0.58, "source": "SAXS"},
        {"name": "pyfai_q_peak_diff_pct", "value": 3.4, "source": "cross_validation"},
    ]


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


def test_dsc_feature_bundle_collects_sections_and_support_metrics() -> None:
    assert hasattr(analysis_evidence_dsc, "_dsc_feature_bundle")

    bundle = analysis_evidence_dsc._dsc_feature_bundle(
        {
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
            "quality_flags": {"baseline": "drift"},
            "peak_components": [
                {"type": "melting", "peak_C": 225.0, "onset_C": 220.0, "end_C": 242.0, "enthalpy_Jg": 12.4},
                {"type": "cold_crystallisation", "peak_C": 228.0, "onset_C": 224.0, "end_C": 236.0, "enthalpy_Jg": -4.2},
            ],
            "scan_r_squared": [
                {"scan": 1, "r_squared": 0.92},
                {"scan": 2, "r_squared": 0.61},
            ],
        },
        {
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
        validation_summary="validation says drift remains",
        residual_type="baseline_drift",
        residual_summary="baseline drift remains",
    )

    assert bundle["feature_evidence"]["thermal_event_evidence"]["Tg_search_low_C"] == 20.0
    assert bundle["feature_evidence"]["baseline_evidence"]["baseline_corr"] == "tangential"
    assert bundle["feature_evidence"]["peak_evidence"]["supported_melting_component_count"] == 1
    assert bundle["feature_evidence"]["event_support_evidence"]["event_support_score"] >= 0.0
    assert bundle["physical_evidence"]["quality_flags"] == {"baseline": "drift"}
    assert bundle["xc_reliability_status"] == "diagnostic_only"
    assert len(bundle["supported_components"]) == 2
    assert len(bundle["supported_melting_components"]) == 1
    assert bundle["structure_support_score"] is not None
    assert any(item["name"] == "scan_r_squared_median" for item in bundle["confidence_signals"])


def test_dsc_structure_evidence_uses_support_metrics_and_constraint_gates() -> None:
    assert hasattr(analysis_evidence_dsc, "_dsc_structure_evidence")

    feature_bundle = analysis_evidence_dsc._dsc_feature_bundle(
        {
            "quality_score": 0.95,
            "scan_mode": "heating",
            "Tg_C": 55.0,
            "Tm_peak_C": 221.0,
            "Tcc_peak_C": 125.0,
            "DHm_Jg": 78.0,
            "DHm_Jg_mean": 77.6,
            "DHm_Jg_std": 2.5,
            "DHcc_Jg": 18.0,
            "DHcc_Jg_mean": 18.4,
            "DHcc_Jg_std": 1.0,
            "Xc_pct": 38.0,
            "Xc_pct_mean": 37.5,
            "Xc_pct_std": 4.6,
            "Xc_pct_ci95": 4.0,
            "Xc_method": "enthalpy",
            "DHm0_Jg": 230.0,
            "DHm0_source": "polymer_reference",
            "peak_components": [
                {"type": "melting", "peak_C": 221.0, "onset_C": 205.0, "end_C": 235.0, "enthalpy_Jg": 78.0},
                {"type": "cold_crystallization", "peak_C": 125.0, "onset_C": 110.0, "end_C": 140.0, "enthalpy_Jg": 18.0},
            ],
            "scan_r_squared": [
                {"scan": 1, "r_squared": 0.95},
                {"scan": 2, "r_squared": 0.96},
            ],
        },
        {
            "config_snapshot": {
                "exo_up": True,
                "baseline_corr": "tangential",
                "min_event_enthalpy_Jg": 0.05,
            }
        },
        validation_summary="all good",
        residual_type="random",
        residual_summary="balanced residuals",
    )

    ok_structure = analysis_evidence_dsc._dsc_structure_evidence(
        {
            "Tg_C": 55.0,
            "Tm_peak_C": 221.0,
            "Tcc_peak_C": 125.0,
            "DHm_Jg": 78.0,
            "DHcc_Jg": 18.0,
            "Xc_pct": 38.0,
        },
        feature_bundle=feature_bundle,
        constraint_summary={"status": "ok", "triggered_total": 0},
        hard_fail_names=set(),
    )

    assert ok_structure["Xc_reliability_status"] == "usable"
    assert ok_structure["supported_event_count"] == 2
    assert ok_structure["supported_melting_event_count"] == 1
    assert ok_structure["structure_support_score"] is not None
    assert ok_structure["physical_support_pass"] is True
    assert ok_structure["paper_conclusion_candidate"] is True
    assert ok_structure["paper_conclusion_ready"] is True

    blocked_structure = analysis_evidence_dsc._dsc_structure_evidence(
        {
            "Tg_C": 55.0,
            "Tm_peak_C": 221.0,
            "Tcc_peak_C": 125.0,
            "DHm_Jg": 78.0,
            "DHcc_Jg": 18.0,
            "Xc_pct": 38.0,
        },
        feature_bundle=feature_bundle,
        constraint_summary={"status": "hard_fail", "triggered_total": 1},
        hard_fail_names={"quality_floor"},
    )

    assert blocked_structure["physical_support_pass"] is False
    assert blocked_structure["paper_conclusion_candidate"] is False
    assert blocked_structure["paper_conclusion_ready"] is False


def test_dsc_actionable_lines_translate_soft_warning_names() -> None:
    assert hasattr(analysis_evidence_dsc, "_dsc_actionable_lines")

    lines = analysis_evidence_dsc._dsc_actionable_lines(
        {
            "baseline_sensitive_result",
            "Tg_without_DCp_step",
            "Tg_outside_supported_window",
            "melting_without_supported_event",
            "cold_crystallization_conflicts_with_melting",
            "event_polarity_conflict",
            "multi_scan_inconsistent",
            "dsc_baseline_sensitive_xc",
        }
    )

    assert lines == [
        "baseline_sensitive_result -> stabilize baseline_corr and smooth_window before trusting Tg/Tm",
        "Tg support is weak -> re-center the Tg window before promoting Tg as stable",
        "melting_without_supported_event -> check Tm onset/end and peak_components before accepting Tm",
        "cold_crystallization_conflicts_with_melting -> separate Tcc from the melting window before re-using the result",
        "event_polarity_conflict -> verify exo_up and signed enthalpy before writing conclusions",
        "multi_scan_inconsistent -> stabilize the scan-to-scan evidence before accepting the file-level result",
        "dsc_baseline_sensitive_xc -> keep Xc low-confidence until baseline and integration sensitivity settle",
    ]


def test_dsc_summary_details_collect_support_and_paper_ready_bits() -> None:
    assert hasattr(analysis_evidence_dsc, "_dsc_summary_details")

    details = analysis_evidence_dsc._dsc_summary_details(
        {
            "structure_support_score": 0.88,
            "event_support_score": 0.91,
            "baseline_stability_score": 0.73,
            "thermodynamic_consistency_score": 0.69,
            "paper_conclusion_candidate": True,
            "paper_conclusion_ready": False,
        }
    )

    assert details["summary_bits"] == [
        "structure_support=0.88",
        "event_support=0.91",
        "baseline_stability=0.73",
        "thermo_consistency=0.69",
        "paper_candidate=True",
        "paper_ready=False",
    ]


def test_analysis_evidence_reuses_dsc_constraint_helper_from_dsc_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._evaluate_dsc_constraint
        is analysis_evidence_dsc._evaluate_dsc_constraint
    )


def test_analysis_evidence_dsc_reuses_rows_and_post_helpers_from_dedicated_modules() -> None:
    rows_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_rows")
    post_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_post")
    assert rows_spec is not None
    assert post_spec is not None

    analysis_evidence_dsc_rows = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_rows"
    )
    analysis_evidence_dsc_post = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_post"
    )

    assert analysis_evidence_dsc._dsc_scan_rows is analysis_evidence_dsc_rows._dsc_scan_rows
    assert (
        analysis_evidence_dsc._dsc_peak_component_rows
        is analysis_evidence_dsc_rows._dsc_peak_component_rows
    )
    assert (
        analysis_evidence_dsc._dsc_actionable_lines
        is analysis_evidence_dsc_post._dsc_actionable_lines
    )
    assert (
        analysis_evidence_dsc._dsc_summary_details
        is analysis_evidence_dsc_post._dsc_summary_details
    )
    assert analysis_evidence_dsc._DSC_CONSTRAINT_NAMES is analysis_evidence_dsc_post._DSC_CONSTRAINT_NAMES
    assert (
        analysis_evidence_dsc._evaluate_dsc_constraint
        is analysis_evidence_dsc_post._evaluate_dsc_constraint
    )


def test_analysis_evidence_dsc_post_reuses_guidance_context_and_rule_modules() -> None:
    guidance_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_post_guidance")
    context_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_post_constraint_context")
    quality_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_post_constraint_quality")
    event_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_post_constraint_event")
    assert guidance_spec is not None
    assert context_spec is not None
    assert quality_spec is not None
    assert event_spec is not None

    analysis_evidence_dsc_post = importlib.import_module("polynexus.core.analysis_evidence_dsc_post")
    analysis_evidence_dsc_post_guidance = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_post_guidance"
    )
    analysis_evidence_dsc_post_constraint_context = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_post_constraint_context"
    )
    analysis_evidence_dsc_post_constraint_quality = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_post_constraint_quality"
    )
    analysis_evidence_dsc_post_constraint_event = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_post_constraint_event"
    )

    assert (
        analysis_evidence_dsc_post._dsc_actionable_lines
        is analysis_evidence_dsc_post_guidance._dsc_actionable_lines
    )
    assert (
        analysis_evidence_dsc_post._dsc_summary_details
        is analysis_evidence_dsc_post_guidance._dsc_summary_details
    )
    assert (
        analysis_evidence_dsc_post._dsc_constraint_context
        is analysis_evidence_dsc_post_constraint_context._dsc_constraint_context
    )
    assert (
        analysis_evidence_dsc_post._evaluate_dsc_quality_constraint
        is analysis_evidence_dsc_post_constraint_quality._evaluate_dsc_quality_constraint
    )
    assert (
        analysis_evidence_dsc_post._evaluate_dsc_event_constraint
        is analysis_evidence_dsc_post_constraint_event._evaluate_dsc_event_constraint
    )


def test_analysis_evidence_dsc_reuses_feature_and_structure_modules() -> None:
    feature_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_feature_bundle")
    structure_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_structure")
    assert feature_spec is not None
    assert structure_spec is not None

    analysis_evidence_dsc_feature_bundle = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_feature_bundle"
    )
    analysis_evidence_dsc_structure = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_structure"
    )

    assert (
        analysis_evidence_dsc._dsc_feature_bundle
        is analysis_evidence_dsc_feature_bundle._dsc_feature_bundle
    )
    assert (
        analysis_evidence_dsc._dsc_structure_evidence
        is analysis_evidence_dsc_structure._dsc_structure_evidence
    )


def test_analysis_evidence_dsc_feature_bundle_reuses_context_and_support_modules() -> None:
    context_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_feature_context")
    support_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_feature_support")
    assert context_spec is not None
    assert support_spec is not None

    analysis_evidence_dsc_feature_bundle = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_feature_bundle"
    )
    analysis_evidence_dsc_feature_context = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_feature_context"
    )
    analysis_evidence_dsc_feature_support = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_feature_support"
    )

    assert (
        analysis_evidence_dsc_feature_bundle._dsc_feature_context
        is analysis_evidence_dsc_feature_context._dsc_feature_context
    )
    assert (
        analysis_evidence_dsc_feature_bundle._dsc_feature_support_bundle
        is analysis_evidence_dsc_feature_support._dsc_feature_support_bundle
    )


def test_analysis_evidence_dsc_feature_context_reuses_sections_module() -> None:
    sections_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_dsc_feature_sections")
    assert sections_spec is not None

    analysis_evidence_dsc_feature_context = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_feature_context"
    )
    analysis_evidence_dsc_feature_sections = importlib.import_module(
        "polynexus.core.analysis_evidence_dsc_feature_sections"
    )

    assert (
        analysis_evidence_dsc_feature_context._dsc_feature_evidence_sections
        is analysis_evidence_dsc_feature_sections._dsc_feature_evidence_sections
    )


def test_evaluate_dsc_constraint_keeps_quality_and_event_rules() -> None:
    assert hasattr(analysis_evidence_dsc, "_evaluate_dsc_constraint")

    baseline_triggered, baseline_observed = analysis_evidence_dsc._evaluate_dsc_constraint(
        "baseline_sensitive_result",
        {
            "quality_score": 0.50,
            "fit_rmse": 0.21,
            "quality_flags": {"baseline": "drift"},
        },
        "baseline_drift",
        {"config_snapshot": {}},
    )

    polarity_triggered, polarity_observed = analysis_evidence_dsc._evaluate_dsc_constraint(
        "event_polarity_conflict",
        {
            "scan_mode": "heating",
            "peak_components": [
                {"type": "melting", "peak_C": 221.0, "onset_C": 205.0, "end_C": 235.0, "enthalpy_Jg": 12.0},
                {"type": "cold_crystallization", "peak_C": 125.0, "onset_C": 110.0, "end_C": 140.0, "enthalpy_Jg": -4.0},
            ],
        },
        "random",
        {"config_snapshot": {"exo_up": True}},
    )

    assert baseline_triggered is True
    assert baseline_observed["residual_type"] == "baseline_drift"
    assert baseline_observed["quality_flags"] == "baseline:drift"
    assert baseline_observed["fit_rmse"] == 0.21
    assert polarity_triggered is True
    assert polarity_observed["exo_up_known"] is True
    assert polarity_observed["conflicting_types"] == []
    assert len(polarity_observed["signed_conflicts"]) == 2


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
    _require_external_real_data_file(str(case.config_overrides["source_file"]), technique="DSC")
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


def test_waxs_peak_metrics_uses_peak_centers_fallback() -> None:
    metrics = _waxs_peak_metrics({"peak_centers": [17.88, 21.75, 24.30]})

    assert metrics["peak_count"] == 3
    assert metrics["peak_positions"] == [17.88, 21.75, 24.30]
    assert metrics["peak_width_spread"] is None
    assert metrics["peak_area_ratio"] is None


def test_waxs_structure_metrics_surfaces_structure_support_contract() -> None:
    peak_metrics = _waxs_peak_metrics(
        {
            "peaks": [
                {"two_theta": 17.88, "fwhm_deg": 0.82, "area": 2442.34},
                {"two_theta": 21.75, "fwhm_deg": 0.94, "area": 1810.52},
            ]
        }
    )
    metrics = _waxs_structure_metrics(
        {
            "Xc_pct": 61.4,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 7.9,
            "crystallinity_method": "peak_deconvolution",
            "crystal_system": "alpha",
            "unit_cell_params": {"a": 4.9, "b": 5.4},
            "two_theta_offset": 0.02,
        },
        peak_metrics=peak_metrics,
        config_snapshot={"two_theta_offset": 0.02},
    )

    assert metrics["peak_count_detected"] == 2
    assert metrics["peak_count_fitted"] == 2
    assert metrics["dominant_peak_positions"] == [17.88, 21.75]
    assert metrics["fit_only_pass"] is True
    assert metrics["physical_support_pass"] is True
    assert metrics["paper_ready_candidate"] is True


def test_waxs_symptoms_from_constraints_keeps_offset_and_residual_context() -> None:
    symptoms = _waxs_symptoms_from_constraints(
        [
            {
                "name": "offset_sensitive_solution",
                "triggered": True,
                "severity": "WARN",
                "observed": None,
            }
        ],
        {
            "two_theta_offset": 0.08,
            "Xc_method": "peak_deconvolution",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
        },
        {
            "config_snapshot": {
                "two_theta_offset": 0.08,
                "amorphous_subtraction": "polynomial",
                "amorphous_n_peaks": 2,
            }
        },
        {
            "residual_type": "peak_width_mismatch",
            "max_residual_region": "18-22 deg",
        },
    )

    assert any(
        item["name"] == "offset_sensitive_solution"
        and item["observed"] == 0.08
        and item["source"] == "WAXS"
        for item in symptoms
    )
    assert any(
        item["name"] == "peak_width_mismatch"
        and item["source"] == "WAXS_residual"
        and item["expected_evidence_change"] == [
            "shoulders and peak core should agree better",
            "peak widths should stabilize",
        ]
        for item in symptoms
    )


def test_waxs_core_feature_evidence_groups_peak_background_phase_and_structure() -> None:
    sections = _waxs_core_feature_evidence(
        {
            "peaks": [
                {"two_theta": 17.88, "fwhm_deg": 0.82, "area": 2442.34},
                {"two_theta": 21.75, "fwhm_deg": 0.94, "area": 1810.52},
            ],
            "Xc_pct": 61.4,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 7.9,
            "D_uncertainty_nm": 0.8,
            "crystallinity_method": "peak_deconvolution",
            "crystal_system": "alpha",
            "unit_cell_params": {"a": 4.9, "b": 5.4},
            "background_method": "spline",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "two_theta_offset": 0.02,
        },
        config_snapshot={"two_theta_offset": 0.02, "background_method": "spline"},
    )

    assert sections["peak_evidence"]["peak_count"] == 2
    assert sections["peak_evidence"]["scherrer_support_peaks"] == 2
    assert sections["background_evidence"]["background_method"] == "spline"
    assert sections["background_evidence"]["two_theta_offset"] == 0.02
    assert sections["phase_evidence"]["Xc_pct"] == 61.4
    assert sections["phase_evidence"]["D_Scherrer_nm"] == 7.9
    assert sections["structure_evidence"]["paper_ready_candidate"] is True


def test_waxs_temperature_feature_evidence_groups_sequence_and_trend_sections() -> None:
    sections = _waxs_temperature_feature_evidence(
        {
            "condition_label": "Temperature",
            "condition_unit": "C",
            "condition_source": "header",
            "condition_confidence": 0.91,
            "temperature_values": [80, 90, 100],
            "temperature_min_C": 80,
            "temperature_max_C": 100,
            "temperature_monotonic": True,
            "temperature_axis_confidence": 0.88,
            "frame_count": 3,
            "frame_pass_count": 3,
            "frame_low_conf_count": 0,
            "physical_support_pass_ratio": 1.0,
            "peak_family_count": 2,
            "peak_family_continuity_score": 0.94,
            "D_support_peak_count": 2,
            "D_trend_support_score": 0.83,
            "Xc_values": [55.2, 58.4, 61.4],
            "Xc_trend_support_score": 0.87,
            "transition_candidate_count": 1,
            "transition_support_score": 0.79,
        }
    )

    assert sections["sequence_evidence"]["condition_label"] == "Temperature"
    assert sections["frame_summary_evidence"]["frame_count"] == 3
    assert sections["peak_family_evidence"]["peak_family_count"] == 2
    assert sections["scherrer_trend_evidence"]["D_support_peak_count"] == 2
    assert sections["crystallinity_trend_evidence"]["Xc_values"] == [55.2, 58.4, 61.4]
    assert sections["transition_evidence"]["transition_support_score"] == 0.79
    assert any(item["name"] == "temperature_axis_confidence" for item in sections["confidence_signals"])


def test_evaluate_waxs_constraint_uses_peak_metrics_for_peak_count_insufficient() -> None:
    triggered, observed = _evaluate_waxs_constraint(
        "peak_count_insufficient",
        {"peak_centers": [17.88]},
        None,
        {},
    )

    assert triggered is True
    assert observed == {"peak_count": 1, "peak_positions": [17.88]}


def test_evaluate_waxs_constraint_uses_config_offset_fallback() -> None:
    triggered, observed = _evaluate_waxs_constraint(
        "offset_sensitive_solution",
        {},
        None,
        {"two_theta_offset": 0.08},
    )

    assert triggered is True
    assert observed == {"two_theta_offset": 0.08}


def test_waxs_summary_details_collects_peak_temperature_and_trend_bits() -> None:
    details = _waxs_summary_details(
        {
            "temperature_axis_confidence": 0.88,
            "frame_count": 3,
            "frame_low_conf_count": 1,
            "peak_family_count": 2,
            "peak_family_continuity_score": 0.94,
            "D_trend_support_score": 0.83,
            "Xc_trend_support_score": 0.87,
            "transition_support_score": 0.79,
        },
        {"peak_count": 2},
        {"physical_support_pass": True, "paper_ready_candidate": False},
        {"condition_source": "header"},
    )

    assert any(item["name"] == "peak_evidence_peak_count" and item["value"] == 2 for item in details["confidence_signals"])
    assert "temperature_axis=0.88" in details["summary_bits"]
    assert "condition_source=header" in details["summary_bits"]
    assert "physical_support=True" in details["summary_bits"]
    assert "paper_ready=False" in details["summary_bits"]
    assert "frames=3" in details["summary_bits"]
    assert "peak_families=2" in details["summary_bits"]
    assert "transition_support=0.79" in details["summary_bits"]


def test_waxs_feature_bundle_collects_sections_and_signals() -> None:
    bundle = _waxs_feature_bundle(
        {
            "peaks": [
                {"two_theta": 17.88, "fwhm_deg": 0.82, "area": 2442.34},
                {"two_theta": 21.75, "fwhm_deg": 0.94, "area": 1810.52},
            ],
            "Xc_pct": 61.4,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 7.9,
            "crystallinity_method": "peak_deconvolution",
            "crystal_system": "alpha",
            "unit_cell_params": {"a": 4.9, "b": 5.4},
            "background_method": "spline",
            "amorphous_subtraction": "polynomial",
            "amorphous_n_peaks": 2,
            "two_theta_offset": 0.02,
            "condition_label": "Temperature",
            "condition_source": "header",
            "temperature_axis_confidence": 0.88,
            "frame_count": 3,
            "peak_family_count": 2,
            "peak_family_continuity_score": 0.94,
            "D_trend_support_score": 0.83,
            "Xc_values": [55.2, 58.4, 61.4],
            "Xc_trend_support_score": 0.87,
            "transition_support_score": 0.79,
        },
        config_snapshot={"two_theta_offset": 0.02, "background_method": "spline"},
    )

    assert bundle["peak_evidence"]["peak_count"] == 2
    assert bundle["background_evidence"]["background_method"] == "spline"
    assert bundle["phase_evidence"]["D_Scherrer_nm"] == 7.9
    assert bundle["structure_evidence"]["paper_ready_candidate"] is True
    assert bundle["condition_evidence"]["condition_source"] == "header"
    assert bundle["feature_evidence"]["sequence_evidence"]["condition_label"] == "Temperature"
    assert bundle["feature_evidence"]["transition_evidence"]["transition_support_score"] == 0.79
    assert any(item["name"] == "peak_count" and item["source"] == "WAXS" for item in bundle["confidence_signals"])
    assert any(item["name"] == "structure_support_score" and item["source"] == "WAXS" for item in bundle["confidence_signals"])
    assert any(item["name"] == "temperature_axis_confidence" for item in bundle["confidence_signals"])


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


def test_waxs_size_uncertainty_is_evidence() -> None:
    evidence = build_analysis_evidence(
        "WAXS",
        output_parameters={
            "r_squared": 0.94,
            "quality_score": 0.9,
            "n_peaks": 3,
            "Xc_pct": 55.2,
            "Xc_method": "peak_deconvolution",
            "D_Scherrer_nm": 9.1,
            "D_uncertainty_nm": 0.8,
            "D_WH_nm": 10.4,
            "D_WH_uncertainty_nm": 1.1,
            "epsilon_WH_pct": 0.18,
            "epsilon_WH_uncertainty_pct": 0.03,
            "WH_fit_r_squared": 0.92,
            "size_reliability_status": "usable",
            "instrument_broadening_model": "caglioti",
            "instrument_broadening_applied": True,
            "scherrer_peak_records": [
                {"two_theta": 18.0, "beta_sample_deg": 0.39, "D_nm": 9.8, "D_uncertainty_nm": 0.7},
                {"two_theta": 21.5, "beta_sample_deg": 0.42, "D_nm": 9.0, "D_uncertainty_nm": 0.8},
                {"two_theta": 24.0, "beta_sample_deg": 0.46, "D_nm": 8.6, "D_uncertainty_nm": 0.9},
            ],
            "peaks": [
                {"two_theta": 18.0, "fwhm_deg": 0.40, "area": 120.0},
                {"two_theta": 21.5, "fwhm_deg": 0.43, "area": 105.0},
                {"two_theta": 24.0, "fwhm_deg": 0.47, "area": 90.0},
            ],
        },
        residual_pattern={"residual_type": "random", "summary": "size uncertainty is explicitly modeled"},
        validation_context={"config_snapshot": {"caglioti_U": 0.002, "caglioti_W": 0.0004}},
    ).to_dict()

    phase = evidence["feature_evidence"]["phase_evidence"]
    structure = evidence["feature_evidence"]["structure_evidence"]

    assert phase["D_uncertainty_nm"] == 0.8
    assert phase["D_WH_uncertainty_nm"] == 1.1
    assert phase["epsilon_WH_uncertainty_pct"] == 0.03
    assert phase["WH_fit_r_squared"] == 0.92
    assert phase["size_reliability_status"] == "usable"
    assert structure["size_reliability_status"] == "usable"
    assert structure["instrument_broadening_model"] == "caglioti"
    assert structure["scherrer_peak_record_count"] == 3


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


def test_ir_peak_records_uses_peak_centers_fallback() -> None:
    records = _ir_peak_records({"peak_centers": [3298, 1637, 1541]})

    assert [item["wavenumber"] for item in records] == [3298.0, 1637.0, 1541.0]
    assert all(item["assignment"] == "" for item in records)
    assert all(item["ref_wavenumber"] is None for item in records)


def test_ir_band_support_metrics_tracks_reference_band_hits() -> None:
    support = _ir_band_support_metrics(
        {
            "polymer_name": "PA6",
            "assignment_confidence": 0.68,
            "peaks": [
                {"wavenumber": 3298, "assignment": "N-H stretch", "fwhm_cm1": 18.0},
                {"wavenumber": 1637, "assignment": "amide I", "fwhm_cm1": 14.0},
                {"wavenumber": 1541, "assignment": "unknown", "fwhm_cm1": 16.0},
            ],
        },
        {
            "ir_reference_bands": {
                "bands": [
                    {"wavenumber": 3298, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                    {"wavenumber": 1637, "assignment": "amide I", "crystallinity_sensitive": False},
                    {"wavenumber": 1541, "assignment": "amide II", "crystallinity_sensitive": False},
                ]
            }
        },
    )

    assert support["peak_count"] == 3
    assert support["assigned_peak_count"] == 2
    assert support["reference_band_hit_count"] == 3
    assert support["reference_band_missing_count"] == 0
    assert support["characteristic_band_support_ok"] is True


def test_ir_reference_band_context_prefers_validation_payload_and_keeps_source() -> None:
    context = _ir_reference_band_context(
        {
            "polymer_name": "PA6",
            "polymer_peaks_db": {
                "PA6": [
                    (3300.0, "fallback band", "strong", False),
                ]
            },
        },
        {
            "ir_reference_bands": {
                "source": "manual_reference",
                "bands": [
                    {
                        "wavenumber": 3298.0,
                        "assignment": "N-H stretch",
                        "intensity": "strong",
                        "crystallinity_sensitive": False,
                    }
                ],
            }
        },
    )

    assert context["polymer_name"] == "PA6"
    assert context["reference_band_source"] == "manual_reference"
    assert len(context["reference_band_records"]) == 1
    assert context["reference_band_records"][0]["ref_wavenumber"] == 3298.0
    assert context["reference_band_records"][0]["assignment"] == "N-H stretch"


def test_ir_match_reference_bands_returns_hits_and_missing_with_assignment_fallback() -> None:
    matches = _ir_match_reference_bands(
        [
            {"wavenumber": 3298.0, "assignment": "N-H stretch"},
            {"wavenumber": 1637.0, "assignment": "amide I"},
        ],
        [
            {"ref_wavenumber": 3298.0, "assignment": "N-H stretch", "crystallinity_sensitive": False},
            {"ref_wavenumber": 1541.0, "assignment": "amide II", "crystallinity_sensitive": False},
        ],
    )

    assert len(matches["key_band_hits"]) == 1
    assert matches["key_band_hits"][0]["observed_wavenumber"] == 3298.0
    assert matches["key_band_hits"][0]["assignment"] == "N-H stretch"
    assert len(matches["key_band_missing"]) == 1
    assert matches["key_band_missing"][0]["assignment"] == "amide II"


def test_ir_peak_observation_bundle_collects_peak_lists_and_assignment_counts() -> None:
    assert hasattr(analysis_evidence_ir, "_ir_peak_observation_bundle")

    bundle = analysis_evidence_ir._ir_peak_observation_bundle(
        [
            {
                "wavenumber": 3298.0,
                "height": 1.2,
                "prominence": 0.8,
                "fwhm_cm1": 18.0,
                "area": 10.0,
                "assignment": "N-H stretch",
                "ref_wavenumber": 3300.0,
            },
            {
                "wavenumber": 1637.0,
                "height": 0.0,
                "prominence": 0.4,
                "fwhm_cm1": 14.0,
                "area": 6.0,
                "assignment": "unknown",
                "ref_wavenumber": None,
            },
            {
                "wavenumber": None,
                "height": -0.3,
                "prominence": None,
                "fwhm_cm1": None,
                "area": None,
                "assignment": "",
                "ref_wavenumber": 1541.0,
            },
        ]
    )

    assert bundle["peak_positions"] == [3298.0, 1637.0]
    assert bundle["peak_heights"] == [1.2, 0.0, -0.3]
    assert bundle["peak_prominences"] == [0.8, 0.4]
    assert bundle["peak_widths"] == [18.0, 14.0]
    assert bundle["peak_assignments"] == ["N-H stretch", "unknown"]
    assert bundle["assigned_peak_count"] == 1
    assert bundle["matched_peak_count"] == 2
    assert bundle["peak_support_count"] == 1
    assert bundle["assigned_peaks"] == [
        {
            "wavenumber": 3298.0,
            "height": 1.2,
            "prominence": 0.8,
            "fwhm_cm1": 18.0,
            "area": 10.0,
            "assignment": "N-H stretch",
            "ref_wavenumber": 3300.0,
        }
    ]
    assert bundle["unassigned_peaks"] == [
        {
            "wavenumber": 1637.0,
            "height": 0.0,
            "prominence": 0.4,
            "fwhm_cm1": 14.0,
            "area": 6.0,
            "assignment": "unknown",
        },
        {
            "height": -0.3,
            "ref_wavenumber": 1541.0,
        },
    ]


def test_ir_processing_context_prefers_output_and_derives_span_and_distribution() -> None:
    assert hasattr(analysis_evidence_ir, "_ir_processing_context")

    context = analysis_evidence_ir._ir_processing_context(
        {
            "baseline_method": "als",
            "normalization_method": "area",
            "smooth_window": 13,
            "peak_distance": 9,
            "peak_fit_window_cm1": 22,
            "assignment_tolerance_cm1": 16,
            "wavenumber_min_cm1": 700,
            "wavenumber_max_cm1": 3600,
            "Xc_method": "band_ratio",
        },
        {
            "config_snapshot": {
                "baseline_method": "mute_zone",
                "normalization_method": "peak",
                "smooth_window": 21,
                "peak_distance": 15,
                "peak_fit_window_cm1": 40,
                "assignment_tolerance_cm1": 20,
            }
        },
        peak_positions=[3298.0, 1637.0],
        peak_prominences=[0.8, 0.4],
        peak_heights=[1.2, 0.0],
    )

    assert context["baseline_method"] == "als"
    assert context["normalization_method"] == "area"
    assert context["smooth_window"] == 13.0
    assert context["peak_distance"] == 9.0
    assert context["peak_fit_window"] == 22.0
    assert context["assignment_tolerance"] == 16.0
    assert context["wn_min"] == 700.0
    assert context["wn_max"] == 3600.0
    assert context["wn_span"] == 2900.0
    assert context["x_calibration_status"] == "uncalibrated_index"
    assert context["peak_prominence_distribution"] is not None
    assert context["peak_prominence_distribution"]["source"] == "prominence"


def test_ir_symptom_bridge_lines_surfaces_expected_followup_text() -> None:
    lines = _ir_symptom_bridge_lines(
        {
            "name": "baseline_sensitive_assignment",
            "target_params": ["baseline_method", "normalization_method"],
            "expected_evidence_change": ["baseline_method should settle on a stable choice"],
        },
        {"quality_flag": "WARN:low_confidence"},
    )

    assert lines[0].startswith("baseline_sensitive_assignment -> stabilize baseline_method")
    assert any("expected evidence change" in item for item in lines)
    assert any("current quality_flag" in item for item in lines)


def test_ir_symptoms_from_constraints_keeps_band_support_context() -> None:
    symptoms = _ir_symptoms_from_constraints(
        [
            {"name": "key_band_support_insufficient", "severity": "warning", "triggered": True},
            {"name": "noise_dominant", "severity": "warning", "triggered": False},
        ],
        {
            "polymer_name": "PA6",
            "assignment_confidence": 0.68,
            "peaks": [
                {"wavenumber": 3298, "assignment": "N-H stretch", "fwhm_cm1": 18.0},
                {"wavenumber": 1637, "assignment": "amide I", "fwhm_cm1": 14.0},
                {"wavenumber": 1541, "assignment": "unknown", "fwhm_cm1": 16.0},
            ],
        },
        {"residual_type": "peak_mismatch", "summary": "band mismatch remains"},
        {
            "ir_reference_bands": {
                "bands": [
                    {"wavenumber": 3298, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                    {"wavenumber": 1637, "assignment": "amide I", "crystallinity_sensitive": False},
                    {"wavenumber": 1541, "assignment": "amide II", "crystallinity_sensitive": False},
                ]
            }
        },
    )

    assert len(symptoms) == 1
    assert symptoms[0]["name"] == "key_band_support_insufficient"
    assert symptoms[0]["observed"]["reference_band_hit_count"] == 3
    assert symptoms[0]["observed"]["reference_band_missing_count"] == 0


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
    _require_external_real_data_file(str(data_file), technique="IR")
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


def test_ir_temperature_2d_feature_bundle_groups_sequence_matrix_and_band_tracking_sections() -> None:
    bundle = _ir_temperature_2d_feature_bundle(
        {
            "submodule_id": "ir.temperature_2d",
            "n_frames": 48,
            "n_bands_tracked": 6,
            "stage_counts": {"heating": 23, "hold": 3, "cooling": 22},
            "sequence_order_source": "filename_stage",
            "T_range_C": (35.0, 215.0),
            "temperature_min_C": 35.0,
            "temperature_max_C": 215.0,
            "temperature_missing_count": 0,
            "time_missing_count": 0,
            "time_estimated_count": 0,
            "dynamic_shape": (48, 256),
            "sync_shape": (256, 256),
            "async_shape": (256, 256),
            "matrix_shape": (48, 256),
            "dynamic_rms": 0.12,
            "dynamic_signal_rms": 0.11,
            "neg_fraction": 0.08,
            "nan_fraction": 0.0,
            "wavenumber_grid_consistent": True,
            "frame_intensity_scale_spread": 0.14,
            "max_sync_abs": 2.3,
            "max_async_abs": 1.7,
            "sync_cross_peak_count": 12,
            "async_cross_peak_count": 12,
            "cross_peak_count": 24,
            "assigned_cross_peak_count": 9,
            "unassigned_cross_peak_count": 15,
            "async_with_sync_support_count": 7,
            "top_sync_cross_peak_cm1": (1637.0, 1541.0),
            "top_async_cross_peak_cm1": (1263.0, 929.0),
            "top_sync_diagonal_distance_cm1": 22.0,
            "top_async_diagonal_distance_cm1": 31.0,
            "top_sync_assigned": True,
            "top_async_assigned": True,
            "top_async_has_sync_support": True,
            "noda_rule_interpretation_ready": True,
            "transition_count": 2,
            "transition_temperatures_C": [118.0, 162.0],
            "sequence_axis_ready": True,
            "matrix_shapes_consistent": True,
            "sequence_axis_score": 0.94,
            "matrix_quality_score": 0.81,
            "cos_signal_score": 0.78,
            "band_tracking_score": 0.74,
            "interpretation_ready": True,
            "paper_conclusion_ready": False,
            "band_index_series_count": 6,
            "band_index_transition_candidate_count": 2,
            "band_index_transition_support_band_count": 3,
            "band_index_transition_consensus_frame": 18,
            "band_index_transition_frame_spread": 1.2,
            "band_index_transition_support_ratio": 0.67,
            "band_index_transition_single_frame_only": False,
            "band_index_transition_reproducible": True,
            "band_index_transition_denominator_unstable": False,
            "band_index_transition_max_jump_cm1": 14.0,
            "band_index_transition_median_jump_cm1": 8.0,
            "band_index_transition_max_jump_ratio": 0.19,
            "band_tracking_missing_key_band": False,
            "band_index_transition_support_keys": ["amide_i", "amide_ii"],
            "low_confidence_frame_count": 2,
            "low_confidence_frame_ratio": 0.04,
            "frame_assignment_confidence_mean": 0.88,
            "frame_polymer_score_mean": 0.91,
            "frame_key_band_support_mean": 0.86,
        }
    )

    assert bundle["signal_evidence"]["n_frames"] == 48
    assert bundle["peak_evidence"]["matrix_shape"] == (48, 256)
    assert bundle["transform_evidence"]["sync_cross_peak_count"] == 12
    assert bundle["structure_evidence"]["interpretation_ready"] is True
    assert bundle["feature_evidence"]["band_tracking_evidence"]["band_index_transition_support_band_count"] == 3
    assert bundle["feature_evidence"]["temperature_2d_evidence"]["paper_conclusion_ready"] is False
    assert any(item["name"] == "sequence_axis_score" for item in bundle["confidence_signals"])


def test_ir_temperature_2d_symptoms_from_constraints_collects_triggered_items() -> None:
    assert hasattr(analysis_evidence_ir, "_ir_temperature_2d_symptoms_from_constraints")

    symptoms = analysis_evidence_ir._ir_temperature_2d_symptoms_from_constraints(
        [
            {"name": "negative_matrix_fraction_high", "triggered": True, "severity": "WARN"},
            {"name": "transition_candidate_present", "triggered": True, "severity": "INFO"},
            {"name": "wavenumber_grid_inconsistent", "triggered": False, "severity": "FAIL"},
        ],
        {
            "neg_fraction": 0.08,
            "nan_fraction": 0.0,
            "dynamic_rms": 0.12,
            "transition_count": 2,
            "transition_temperatures_C": [118.0, 162.0],
        },
    )

    names = [item["name"] for item in symptoms]
    assert names == ["negative_matrix_fraction_high", "transition_candidate_present"]
    assert symptoms[0]["source"] == "IR_temperature_2d"
    assert symptoms[0]["observed"]["neg_fraction"] == 0.08
    assert "baseline over-subtraction should weaken" in symptoms[0]["expected_evidence_change"]
    assert symptoms[1]["severity"] == "INFO"
    assert symptoms[1]["observed"]["transition_count"] == 2


def test_ir_temperature_2d_symptom_bridge_lines_include_expected_changes_and_status() -> None:
    assert hasattr(analysis_evidence_ir, "_ir_temperature_2d_symptom_bridge_lines")

    lines = analysis_evidence_ir._ir_temperature_2d_symptom_bridge_lines(
        {
            "name": "negative_matrix_fraction_high",
            "summary": "too many non-positive values",
            "target_params": ["baseline_method", "matrix_recovery"],
            "expected_evidence_change": [
                "baseline over-subtraction should weaken",
                "dynamic matrix sign balance should move toward a stable range",
            ],
        },
        {
            "quality_flag": "WARN:low_confidence",
            "validation_summary": "WARN: matrix still unstable",
        },
    )

    assert lines[0] == "negative_matrix_fraction_high -> reduce baseline over-subtraction before trusting the 2D map"
    assert "expected evidence change: baseline over-subtraction should weaken" in lines
    assert "expected evidence change: dynamic matrix sign balance should move toward a stable range" in lines
    assert "current quality_flag: WARN:low_confidence" in lines
    assert "current validation_summary: WARN: matrix still unstable" in lines


def test_analysis_evidence_reuses_ir_temperature_2d_helpers_from_ir_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._ir_temperature_2d_symptoms_from_constraints
        is analysis_evidence_ir._ir_temperature_2d_symptoms_from_constraints
    )
    assert (
        analysis_evidence_module._ir_temperature_2d_symptom_bridge_lines
        is analysis_evidence_ir._ir_temperature_2d_symptom_bridge_lines
    )


def test_analysis_evidence_ir_reuses_temperature_2d_helpers_from_ir_temperature_2d_module() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_temperature_2d")
    assert spec is not None

    analysis_evidence_ir_temperature_2d = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d"
    )

    assert (
        analysis_evidence_ir._ir_temperature_2d_feature_bundle
        is analysis_evidence_ir_temperature_2d._ir_temperature_2d_feature_bundle
    )
    assert (
        analysis_evidence_ir._ir_temperature_2d_constraint_rows
        is analysis_evidence_ir_temperature_2d._ir_temperature_2d_constraint_rows
    )
    assert (
        analysis_evidence_ir._ir_temperature_2d_symptoms_from_constraints
        is analysis_evidence_ir_temperature_2d._ir_temperature_2d_symptoms_from_constraints
    )
    assert (
        analysis_evidence_ir._ir_temperature_2d_symptom_bridge_lines
        is analysis_evidence_ir_temperature_2d._ir_temperature_2d_symptom_bridge_lines
    )
    assert (
        analysis_evidence_ir._ir_temperature_2d_summary_details
        is analysis_evidence_ir_temperature_2d._ir_temperature_2d_summary_details
    )


def test_analysis_evidence_ir_temperature_2d_reuses_post_helpers_from_dedicated_module() -> None:
    post_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_temperature_2d_post")
    assert post_spec is not None

    analysis_evidence_ir_temperature_2d = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d"
    )
    analysis_evidence_ir_temperature_2d_post = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post"
    )

    assert (
        analysis_evidence_ir_temperature_2d._ir_temperature_2d_symptoms_from_constraints
        is analysis_evidence_ir_temperature_2d_post._ir_temperature_2d_symptoms_from_constraints
    )
    assert (
        analysis_evidence_ir_temperature_2d._ir_temperature_2d_symptom_bridge_lines
        is analysis_evidence_ir_temperature_2d_post._ir_temperature_2d_symptom_bridge_lines
    )
    assert (
        analysis_evidence_ir_temperature_2d._ir_temperature_2d_summary_details
        is analysis_evidence_ir_temperature_2d_post._ir_temperature_2d_summary_details
    )


def test_analysis_evidence_ir_temperature_2d_post_reuses_summary_and_symptoms_modules() -> None:
    summary_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_summary"
    )
    symptoms_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptoms"
    )
    assert summary_spec is not None
    assert symptoms_spec is not None

    analysis_evidence_ir_temperature_2d_post = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post"
    )
    analysis_evidence_ir_temperature_2d_post_summary = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_summary"
    )
    analysis_evidence_ir_temperature_2d_post_symptoms = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptoms"
    )

    assert (
        analysis_evidence_ir_temperature_2d_post._ir_temperature_2d_summary_details
        is analysis_evidence_ir_temperature_2d_post_summary._ir_temperature_2d_summary_details
    )
    assert (
        analysis_evidence_ir_temperature_2d_post._ir_temperature_2d_symptoms_from_constraints
        is analysis_evidence_ir_temperature_2d_post_symptoms._ir_temperature_2d_symptoms_from_constraints
    )
    assert (
        analysis_evidence_ir_temperature_2d_post._ir_temperature_2d_symptom_bridge_lines
        is analysis_evidence_ir_temperature_2d_post_symptoms._ir_temperature_2d_symptom_bridge_lines
    )


def test_analysis_evidence_ir_temperature_2d_post_symptoms_reuse_bridge_sequence_interpretation_and_transition_modules() -> None:
    bridge_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_bridge"
    )
    sequence_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_sequence"
    )
    interpretation_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_interpretation"
    )
    transition_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_transition"
    )
    assert bridge_spec is not None
    assert sequence_spec is not None
    assert interpretation_spec is not None
    assert transition_spec is not None

    analysis_evidence_ir_temperature_2d_post_symptoms = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptoms"
    )
    analysis_evidence_ir_temperature_2d_post_symptom_bridge = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_bridge"
    )
    analysis_evidence_ir_temperature_2d_post_symptom_sequence = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_sequence"
    )
    analysis_evidence_ir_temperature_2d_post_symptom_interpretation = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_interpretation"
    )
    analysis_evidence_ir_temperature_2d_post_symptom_transition = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_post_symptom_transition"
    )

    assert (
        analysis_evidence_ir_temperature_2d_post_symptoms._ir_temperature_2d_symptom_bridge_lines
        is analysis_evidence_ir_temperature_2d_post_symptom_bridge._ir_temperature_2d_symptom_bridge_lines
    )
    assert (
        analysis_evidence_ir_temperature_2d_post_symptoms._ir_temperature_2d_sequence_constraint_symptoms
        is analysis_evidence_ir_temperature_2d_post_symptom_sequence._ir_temperature_2d_sequence_constraint_symptoms
    )
    assert (
        analysis_evidence_ir_temperature_2d_post_symptoms._ir_temperature_2d_interpretation_constraint_symptoms
        is analysis_evidence_ir_temperature_2d_post_symptom_interpretation._ir_temperature_2d_interpretation_constraint_symptoms
    )
    assert (
        analysis_evidence_ir_temperature_2d_post_symptoms._ir_temperature_2d_transition_constraint_symptoms
        is analysis_evidence_ir_temperature_2d_post_symptom_transition._ir_temperature_2d_transition_constraint_symptoms
    )


def test_analysis_evidence_ir_temperature_2d_reuses_feature_and_constraints_modules() -> None:
    feature_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_feature"
    )
    constraints_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraints"
    )
    assert feature_spec is not None
    assert constraints_spec is not None

    analysis_evidence_ir_temperature_2d = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d"
    )
    analysis_evidence_ir_temperature_2d_feature = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_feature"
    )
    analysis_evidence_ir_temperature_2d_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraints"
    )

    assert (
        analysis_evidence_ir_temperature_2d._ir_temperature_2d_feature_bundle
        is analysis_evidence_ir_temperature_2d_feature._ir_temperature_2d_feature_bundle
    )
    assert (
        analysis_evidence_ir_temperature_2d._ir_temperature_2d_constraint_rows
        is analysis_evidence_ir_temperature_2d_constraints._ir_temperature_2d_constraint_rows
    )


def test_analysis_evidence_ir_temperature_2d_constraints_reuse_sequence_matrix_and_interpretation_modules() -> None:
    sequence_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraint_sequence"
    )
    matrix_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraint_matrix"
    )
    interpretation_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraint_interpretation"
    )
    assert sequence_spec is not None
    assert matrix_spec is not None
    assert interpretation_spec is not None

    analysis_evidence_ir_temperature_2d_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraints"
    )
    analysis_evidence_ir_temperature_2d_constraint_sequence = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraint_sequence"
    )
    analysis_evidence_ir_temperature_2d_constraint_matrix = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraint_matrix"
    )
    analysis_evidence_ir_temperature_2d_constraint_interpretation = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_temperature_2d_constraint_interpretation"
    )

    assert (
        analysis_evidence_ir_temperature_2d_constraints._ir_temperature_2d_sequence_constraint_rows
        is analysis_evidence_ir_temperature_2d_constraint_sequence._ir_temperature_2d_sequence_constraint_rows
    )
    assert (
        analysis_evidence_ir_temperature_2d_constraints._ir_temperature_2d_matrix_constraint_rows
        is analysis_evidence_ir_temperature_2d_constraint_matrix._ir_temperature_2d_matrix_constraint_rows
    )
    assert (
        analysis_evidence_ir_temperature_2d_constraints._ir_temperature_2d_interpretation_constraint_rows
        is analysis_evidence_ir_temperature_2d_constraint_interpretation._ir_temperature_2d_interpretation_constraint_rows
    )


def test_analysis_evidence_ir_static_reuses_peak_reference_and_builder_modules() -> None:
    static_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static")
    peak_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_peak")
    reference_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_reference")
    builder_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_builder")
    assert static_spec is not None
    assert peak_spec is not None
    assert reference_spec is not None
    assert builder_spec is not None

    analysis_evidence_ir_static = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static"
    )
    analysis_evidence_ir_static_peak = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_peak"
    )
    analysis_evidence_ir_static_reference = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_reference"
    )
    analysis_evidence_ir_static_builder = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_builder"
    )

    assert (
        analysis_evidence_ir_static._numeric_distribution
        is analysis_evidence_ir_static_peak._numeric_distribution
    )
    assert analysis_evidence_ir_static._ir_peak_records is analysis_evidence_ir_static_peak._ir_peak_records
    assert (
        analysis_evidence_ir_static._ir_peak_observation_bundle
        is analysis_evidence_ir_static_peak._ir_peak_observation_bundle
    )
    assert (
        analysis_evidence_ir_static._ir_processing_context
        is analysis_evidence_ir_static_peak._ir_processing_context
    )
    assert (
        analysis_evidence_ir_static._ir_xc_calibration_status
        is analysis_evidence_ir_static_peak._ir_xc_calibration_status
    )
    assert (
        analysis_evidence_ir_static._ir_reference_band_context
        is analysis_evidence_ir_static_reference._ir_reference_band_context
    )
    assert (
        analysis_evidence_ir_static._ir_match_reference_bands
        is analysis_evidence_ir_static_reference._ir_match_reference_bands
    )
    assert (
        analysis_evidence_ir_static._ir_band_support_metrics
        is analysis_evidence_ir_static_reference._ir_band_support_metrics
    )
    assert (
        analysis_evidence_ir_static._ir_static_feature_bundle
        is analysis_evidence_ir_static_builder._ir_static_feature_bundle
    )
    assert (
        analysis_evidence_ir_static._ir_static_analysis_bundle
        is analysis_evidence_ir_static_builder._ir_static_analysis_bundle
    )
    assert (
        analysis_evidence_ir_static._ir_support_enrichment_bundle
        is analysis_evidence_ir_static_builder._ir_support_enrichment_bundle
    )


def test_analysis_evidence_ir_static_builder_reuses_feature_analysis_and_enrichment_modules() -> None:
    feature_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_static_builder_feature"
    )
    analysis_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_static_builder_analysis"
    )
    enrichment_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_static_builder_enrichment"
    )
    assert feature_spec is not None
    assert analysis_spec is not None
    assert enrichment_spec is not None

    analysis_evidence_ir_static_builder = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_builder"
    )
    analysis_evidence_ir_static_builder_feature = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_builder_feature"
    )
    analysis_evidence_ir_static_builder_analysis = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_builder_analysis"
    )
    analysis_evidence_ir_static_builder_enrichment = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_builder_enrichment"
    )

    assert (
        analysis_evidence_ir_static_builder._ir_static_feature_bundle
        is analysis_evidence_ir_static_builder_feature._ir_static_feature_bundle
    )
    assert (
        analysis_evidence_ir_static_builder._ir_static_analysis_bundle
        is analysis_evidence_ir_static_builder_analysis._ir_static_analysis_bundle
    )
    assert (
        analysis_evidence_ir_static_builder._ir_support_enrichment_bundle
        is analysis_evidence_ir_static_builder_enrichment._ir_support_enrichment_bundle
    )


def test_analysis_evidence_reuses_ir_temperature_2d_constraint_rows_from_ir_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._ir_temperature_2d_constraint_rows
        is analysis_evidence_ir._ir_temperature_2d_constraint_rows
    )


def test_analysis_evidence_reuses_ir_static_constraint_helper_from_ir_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._evaluate_ir_static_constraint
        is analysis_evidence_ir._evaluate_ir_static_constraint
    )


def test_analysis_evidence_ir_reuses_static_post_helpers_from_ir_static_post_module() -> None:
    spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_post")
    assert spec is not None

    analysis_evidence_ir_static_post = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post"
    )

    assert analysis_evidence_ir._IR_STATIC_CONSTRAINT_NAMES is analysis_evidence_ir_static_post._IR_STATIC_CONSTRAINT_NAMES
    assert (
        analysis_evidence_ir._evaluate_ir_static_constraint
        is analysis_evidence_ir_static_post._evaluate_ir_static_constraint
    )
    assert (
        analysis_evidence_ir._ir_symptom_bridge_lines
        is analysis_evidence_ir_static_post._ir_symptom_bridge_lines
    )
    assert (
        analysis_evidence_ir._ir_symptoms_from_constraints
        is analysis_evidence_ir_static_post._ir_symptoms_from_constraints
    )
    assert (
        analysis_evidence_ir._ir_summary_details
        is analysis_evidence_ir_static_post._ir_summary_details
    )


def test_analysis_evidence_ir_static_post_reuses_summary_rules_and_symptoms_modules() -> None:
    summary_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_post_summary")
    rules_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_post_rules")
    symptoms_spec = importlib.util.find_spec("polynexus.core.analysis_evidence_ir_static_post_symptoms")
    assert summary_spec is not None
    assert rules_spec is not None
    assert symptoms_spec is not None

    analysis_evidence_ir_static_post = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post"
    )
    analysis_evidence_ir_static_post_summary = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_summary"
    )
    analysis_evidence_ir_static_post_rules = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_rules"
    )
    analysis_evidence_ir_static_post_symptoms = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_symptoms"
    )

    assert (
        analysis_evidence_ir_static_post._ir_summary_details
        is analysis_evidence_ir_static_post_summary._ir_summary_details
    )
    assert (
        analysis_evidence_ir_static_post._IR_STATIC_CONSTRAINT_NAMES
        is analysis_evidence_ir_static_post_rules._IR_STATIC_CONSTRAINT_NAMES
    )
    assert (
        analysis_evidence_ir_static_post._evaluate_ir_static_constraint
        is analysis_evidence_ir_static_post_rules._evaluate_ir_static_constraint
    )
    assert (
        analysis_evidence_ir_static_post._ir_symptom_bridge_lines
        is analysis_evidence_ir_static_post_symptoms._ir_symptom_bridge_lines
    )
    assert (
        analysis_evidence_ir_static_post._ir_symptoms_from_constraints
        is analysis_evidence_ir_static_post_symptoms._ir_symptoms_from_constraints
    )


def test_analysis_evidence_ir_static_post_symptoms_reuses_bridge_support_and_residual_modules() -> None:
    bridge_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_static_post_symptom_bridge"
    )
    support_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_static_post_symptom_support"
    )
    residual_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_ir_static_post_symptom_residual"
    )
    assert bridge_spec is not None
    assert support_spec is not None
    assert residual_spec is not None

    analysis_evidence_ir_static_post_symptoms = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_symptoms"
    )
    analysis_evidence_ir_static_post_symptom_bridge = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_symptom_bridge"
    )
    analysis_evidence_ir_static_post_symptom_support = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_symptom_support"
    )
    analysis_evidence_ir_static_post_symptom_residual = importlib.import_module(
        "polynexus.core.analysis_evidence_ir_static_post_symptom_residual"
    )

    assert (
        analysis_evidence_ir_static_post_symptoms._ir_symptom_bridge_lines
        is analysis_evidence_ir_static_post_symptom_bridge._ir_symptom_bridge_lines
    )
    assert (
        analysis_evidence_ir_static_post_symptoms._ir_support_constraint_symptoms
        is analysis_evidence_ir_static_post_symptom_support._ir_support_constraint_symptoms
    )
    assert (
        analysis_evidence_ir_static_post_symptoms._ir_residual_constraint_symptoms
        is analysis_evidence_ir_static_post_symptom_residual._ir_residual_constraint_symptoms
    )


def test_ir_temperature_2d_constraint_rows_collect_expected_contracts() -> None:
    assert hasattr(analysis_evidence_ir, "_ir_temperature_2d_constraint_rows")

    rows = analysis_evidence_ir._ir_temperature_2d_constraint_rows(
        {
            "sequence_axis_ready": False,
            "matrix_shapes_consistent": False,
            "n_frames": 4,
            "temperature_missing_count": 1,
            "time_missing_count": 2,
            "hold_time_missing_count": 1,
            "hold_time_estimated_count": 1,
            "heating_monotonic": False,
            "cooling_monotonic": True,
            "hold_monotonic": False,
            "sequence_order_source": "guessed_order",
            "stage_counts": {"heating": 2, "hold": 1, "cooling": 1},
            "neg_fraction": 0.31,
            "nan_fraction": 0.02,
            "dynamic_rms": 0.004,
            "dynamic_signal_rms": 0.004,
            "frame_intensity_scale_spread": 0.9,
            "wavenumber_grid_consistent": False,
            "sync_cross_peak_count": 0,
            "async_cross_peak_count": 1,
            "cross_peak_count": 2,
            "assigned_cross_peak_count": 0,
            "unassigned_cross_peak_count": 2,
            "async_with_sync_support_count": 0,
            "top_sync_diagonal_distance_cm1": 30.0,
            "top_async_diagonal_distance_cm1": 40.0,
            "top_sync_assigned": False,
            "top_async_assigned": False,
            "top_async_has_sync_support": False,
            "noda_rule_interpretation_ready": False,
            "transition_count": 1,
            "transition_temperatures_C": [120.0],
            "matrix_shape": (4, 256),
            "dynamic_shape": (4, 256),
            "sync_shape": (256, 256),
            "async_shape": (256, 256),
        }
    )

    by_name = {item["name"]: item for item in rows}

    assert by_name["sequence_axis_incomplete"]["triggered"] is True
    assert by_name["sequence_axis_incomplete"]["severity"] == "ERROR"
    assert by_name["negative_matrix_fraction_high"]["triggered"] is True
    assert by_name["negative_matrix_fraction_high"]["observed"]["dynamic_rms"] == 0.004
    assert by_name["async_peak_without_sync_support"]["triggered"] is True
    assert by_name["transition_candidate_present"]["severity"] == "INFO"
    assert by_name["transition_candidate_present"]["observed"]["transition_temperatures_C"] == [120.0]


def test_evaluate_ir_static_constraint_keeps_peak_and_assignment_rules() -> None:
    assert hasattr(analysis_evidence_ir, "_evaluate_ir_static_constraint")

    crowded_triggered, crowded_observed = analysis_evidence_ir._evaluate_ir_static_constraint(
        "crowded_band_underfit",
        {
            "peak_count": 9,
            "assigned_peak_count": 3,
            "peak_width_spread": 0.5,
            "baseline_method": "als",
            "normalization_method": "area",
            "peak_distance": 8.0,
            "peak_fit_window_cm1": 55.0,
            "assignment_confidence": 0.72,
            "polymer_score": 0.8,
            "reference_band_count": 3,
            "reference_band_hit_count": 2,
            "reference_band_missing_count": 1,
            "Xc_pct": 31.0,
            "Xc_method": "band_ratio",
            "Xc_calibration_status": "uncalibrated_index",
        },
        "peak_mismatch",
        {"max_residual_region": "amide_i"},
    )

    calibration_triggered, calibration_observed = analysis_evidence_ir._evaluate_ir_static_constraint(
        "ir_xc_uncalibrated",
        {
            "Xc_pct": 31.0,
            "Xc_method": "band_ratio_uncalibrated",
            "Xc_calibration_status": "uncalibrated_index",
        },
        "random",
        {},
    )

    assert crowded_triggered is True
    assert crowded_observed["peak_count"] == 9.0
    assert crowded_observed["peak_fit_window_cm1"] == 55.0
    assert crowded_observed["peak_width_spread"] == 0.5
    assert calibration_triggered is True
    assert calibration_observed["Xc_calibration_status"] == "uncalibrated_index"
    assert calibration_observed["Xc_method"] == "band_ratio_uncalibrated"


def test_analysis_evidence_reuses_nmr_constraint_helper_from_nmr_module() -> None:
    analysis_evidence_module = importlib.import_module("polynexus.core.analysis_evidence")

    assert (
        analysis_evidence_module._evaluate_nmr_constraint
        is analysis_evidence_nmr._evaluate_nmr_constraint
    )


def test_analysis_evidence_nmr_reuses_constraint_and_symptom_helpers_from_dedicated_module() -> None:
    constraints_spec = importlib.util.find_spec(
        "polynexus.core.analysis_evidence_nmr_constraints"
    )
    assert constraints_spec is not None

    analysis_evidence_constraint_evaluator = importlib.import_module(
        "polynexus.core.analysis_evidence_constraint_evaluator"
    )
    analysis_evidence_postprocess = importlib.import_module(
        "polynexus.core.analysis_evidence_postprocess"
    )
    analysis_evidence_nmr_constraints = importlib.import_module(
        "polynexus.core.analysis_evidence_nmr_constraints"
    )

    assert (
        analysis_evidence_nmr._NMR_CONSTRAINT_NAMES
        is analysis_evidence_nmr_constraints._NMR_CONSTRAINT_NAMES
    )
    assert (
        analysis_evidence_nmr._evaluate_nmr_constraint
        is analysis_evidence_nmr_constraints._evaluate_nmr_constraint
    )
    assert (
        analysis_evidence_nmr._nmr_symptoms_from_constraints
        is analysis_evidence_nmr_constraints._nmr_symptoms_from_constraints
    )
    assert (
        analysis_evidence_nmr._nmr_symptom_bridge_lines
        is analysis_evidence_nmr_constraints._nmr_symptom_bridge_lines
    )
    assert (
        analysis_evidence_constraint_evaluator._evaluate_nmr_constraint
        is analysis_evidence_nmr_constraints._evaluate_nmr_constraint
    )
    assert (
        analysis_evidence_postprocess._nmr_symptoms_from_constraints
        is analysis_evidence_nmr_constraints._nmr_symptoms_from_constraints
    )
    assert (
        analysis_evidence_postprocess._nmr_symptom_bridge_lines
        is analysis_evidence_nmr_constraints._nmr_symptom_bridge_lines
    )


def test_evaluate_nmr_constraint_keeps_assignment_and_xc_rules() -> None:
    assert hasattr(analysis_evidence_nmr, "_evaluate_nmr_constraint")

    weak_assignment_triggered, weak_assignment_observed = analysis_evidence_nmr._evaluate_nmr_constraint(
        "nmr_weak_assignment",
        {
            "n_peaks": 3,
            "n_matches": 0,
            "peak_0_ppm": 1.2,
            "peak_0_assignment": "",
            "peak_0_phase": "",
            "peak_1_ppm": 2.4,
            "peak_1_assignment": "",
            "peak_1_phase": "",
        },
        None,
    )

    xc_missing_triggered, xc_missing_observed = analysis_evidence_nmr._evaluate_nmr_constraint(
        "nmr_xc_assignment_missing",
        {
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "peak_0_ppm": 1.2,
            "peak_0_assignment": "methine",
            "peak_0_phase": "c",
        },
        None,
    )

    assert weak_assignment_triggered is True
    assert weak_assignment_observed["assigned_peak_count"] == 0
    assert weak_assignment_observed["n_matches"] == 0.0
    assert weak_assignment_observed["n_peaks"] == 3.0
    assert xc_missing_triggered is True
    assert xc_missing_observed["Xc_method"] == "requires_crystalline_amorphous_assignment"
    assert xc_missing_observed["phases"] == ["c"]


def test_ir_static_feature_bundle_groups_peak_assignment_reference_and_structure_sections() -> None:
    bundle = _ir_static_feature_bundle(
        {
            "polymer_score": 0.74,
            "assignment_confidence": 0.68,
            "Xc_pct": 41.0,
            "Xc_method": "band_ratio",
        },
        polymer_name="PA6",
        reference_band_records=[
            {"ref_wavenumber": 3298.0, "assignment": "N-H stretch", "crystallinity_sensitive": False},
            {"ref_wavenumber": 1637.0, "assignment": "amide I", "crystallinity_sensitive": False},
            {"ref_wavenumber": 1541.0, "assignment": "amide II", "crystallinity_sensitive": False},
        ],
        reference_band_source="IRConfig.polymer_peaks_db",
        peak_positions=[3298.0, 1637.0, 1541.0],
        peak_heights=[1.2, 1.0, 0.8],
        peak_prominence_distribution={"count": 3, "mean": 0.7, "source": "prominence"},
        peak_widths=[18.0, 14.0, 16.0],
        peak_assignments=["N-H stretch", "amide I"],
        assigned_peaks=[
            {"wavenumber": 3298.0, "assignment": "N-H stretch"},
            {"wavenumber": 1637.0, "assignment": "amide I"},
        ],
        unassigned_peaks=[{"wavenumber": 1541.0, "assignment": "unknown"}],
        assigned_peak_count=2,
        matched_peak_count=3,
        peak_support_count=3,
        key_band_hits=[
            {"ref_wavenumber": 3298.0, "observed_wavenumber": 3298.0, "assignment": "N-H stretch", "delta_cm1": 0.0},
            {"ref_wavenumber": 1637.0, "observed_wavenumber": 1637.0, "assignment": "amide I", "delta_cm1": 0.0},
            {"ref_wavenumber": 1541.0, "observed_wavenumber": 1541.0, "assignment": "amide II", "delta_cm1": 0.0},
        ],
        key_band_missing=[],
        baseline_method="rubberband",
        normalization_method="minmax",
        smooth_window=7.0,
        peak_distance=18.0,
        peak_fit_window=35.0,
        assignment_tolerance=12.0,
        wn_min=600.0,
        wn_max=3600.0,
        wn_span=3000.0,
        x_calibration_status="uncalibrated_index",
    )

    assert bundle["signal_evidence"]["wavenumber_span_cm1"] == 3000.0
    assert bundle["peak_evidence"]["peak_count"] == 3
    assert bundle["peak_evidence"]["peak_width_spread"] is not None
    assert bundle["background_evidence"]["baseline_method"] == "rubberband"
    assert bundle["assignment_evidence"]["key_band_hit_count"] == 3
    assert bundle["reference_evidence"]["source"] == "IRConfig.polymer_peaks_db"
    assert bundle["phase_evidence"]["Xc_calibration_status"] == "uncalibrated_index"
    assert bundle["structure_evidence"]["characteristic_band_support_ok"] is True
    assert bundle["feature_evidence"]["classification_evidence"] == bundle["structure_evidence"]
    assert any(item["name"] == "peak_count" for item in bundle["confidence_signals"])
    assert any(item["name"] == "assignment_confidence" for item in bundle["confidence_signals"])


def test_ir_static_analysis_bundle_collects_feature_updates_and_sections() -> None:
    assert hasattr(analysis_evidence_ir, "_ir_static_analysis_bundle")

    bundle = analysis_evidence_ir._ir_static_analysis_bundle(
        {
            "polymer_name": "PA6",
            "polymer_score": 0.74,
            "assignment_confidence": 0.68,
            "Xc_pct": 41.0,
            "Xc_method": "band_ratio",
            "n_peaks": 3,
            "r_squared": 0.95,
            "baseline_method": "rubberband",
            "normalization_method": "minmax",
            "smooth_window": 7,
            "peak_distance": 18.0,
            "peak_fit_window_cm1": 35.0,
            "assignment_tolerance_cm1": 12.0,
            "wavenumber_min_cm1": 600.0,
            "wavenumber_max_cm1": 3600.0,
            "peaks": [
                {
                    "wavenumber": 3298.0,
                    "height": 1.2,
                    "prominence": 0.9,
                    "fwhm_cm1": 18.0,
                    "assignment": "N-H stretch",
                    "ref_wavenumber": 3298.0,
                },
                {
                    "wavenumber": 1637.0,
                    "height": 1.0,
                    "prominence": 0.7,
                    "fwhm_cm1": 14.0,
                    "assignment": "amide I",
                    "ref_wavenumber": 1637.0,
                },
                {
                    "wavenumber": 1541.0,
                    "height": 0.8,
                    "prominence": 0.5,
                    "fwhm_cm1": 16.0,
                    "assignment": "unknown",
                    "ref_wavenumber": 1541.0,
                },
            ],
        },
        {
            "ir_reference_bands": {
                "source": "IRConfig.polymer_peaks_db",
                "bands": [
                    {"wavenumber": 3298.0, "assignment": "N-H stretch", "crystallinity_sensitive": False},
                    {"wavenumber": 1637.0, "assignment": "amide I", "crystallinity_sensitive": False},
                    {"wavenumber": 1541.0, "assignment": "amide II", "crystallinity_sensitive": False},
                ],
            }
        },
    )

    assert bundle["feature_evidence"]["polymer_score"] == 0.74
    assert bundle["feature_evidence"]["n_peaks"] == 3
    assert bundle["signal_evidence"]["wavenumber_span_cm1"] == 3000.0
    assert bundle["peak_evidence"]["peak_count"] == 3
    assert bundle["background_evidence"]["baseline_method"] == "rubberband"
    assert bundle["assignment_evidence"]["key_band_hit_count"] == 3
    assert bundle["reference_evidence"]["source"] == "IRConfig.polymer_peaks_db"
    assert bundle["phase_evidence"]["Xc_calibration_status"] == "uncalibrated_index"
    assert bundle["structure_evidence"]["classification_basis"] == "peak_assignment"
    assert bundle["feature_evidence"]["classification_evidence"] == bundle["structure_evidence"]
    assert any(item["name"] == "polymer_score" for item in bundle["confidence_signals"])
    assert any(item["name"] == "assignment_confidence" for item in bundle["confidence_signals"])


def test_ir_support_enrichment_bundle_computes_scores_and_blocks_paper_ready_on_warning() -> None:
    bundle = _ir_support_enrichment_bundle(
        peak_evidence={
            "peak_count": 6,
            "assigned_peak_count": 6,
            "peak_widths": [18.0, 17.0, 19.0],
        },
        assignment_evidence={
            "assignment_confidence": 0.92,
            "polymer_score": 0.92,
            "key_band_hit_count": 6,
            "key_band_missing_count": 0,
        },
        reference_evidence={
            "band_count": 6,
            "hit_count": 6,
            "missing_count": 0,
        },
        background_evidence={
            "baseline_method": "rubberband",
            "normalization_method": "minmax",
            "smooth_window": 7.0,
            "peak_distance": 18.0,
            "peak_fit_window_cm1": 35.0,
        },
        structure_evidence={
            "paper_conclusion_candidate": True,
            "paper_conclusion_ready": True,
        },
        triggered_total=1,
        triggered_soft_warn={"ir_xc_uncalibrated"},
    )

    support = bundle["feature_evidence"]["ir_support_evidence"]
    assert support["assignment_confidence_score"] == 0.92
    assert support["key_band_support_score"] == 1.0
    assert support["peak_coverage_score"] == 1.0
    assert support["baseline_stability_score"] is not None
    assert bundle["assignment_evidence"]["unassigned_key_band_count"] == 0
    assert bundle["structure_evidence"]["paper_conclusion_ready"] is False
    assert bundle["feature_evidence"]["classification_evidence"] == bundle["structure_evidence"]
    assert any(
        item["name"] == "paper_conclusion_ready" and item["value"] == 0.0
        for item in bundle["confidence_signals"]
    )


def test_ir_summary_details_collects_peak_support_and_paper_ready_bits() -> None:
    details = _ir_summary_details(
        {
            "peak_count": 18,
        },
        {
            "assignment_confidence": 1.0,
            "key_band_support_score": 10 / 13,
            "peak_coverage_score": 0.56,
        },
        {
            "band_count": 13,
            "hit_count": 10,
        },
        {
            "baseline_stability_score": 0.67,
            "reference_band_missing_count": 3,
            "characteristic_band_support_ok": False,
            "paper_conclusion_ready": False,
        },
    )

    assert "peak_count=18" in details["summary_bits"]
    assert "assignment_confidence=1.0" in details["summary_bits"]
    assert "key_band_support=0.7692307692307693" in details["summary_bits"]
    assert "baseline_stability=0.67" in details["summary_bits"]
    assert "ref_bands=13" in details["summary_bits"]
    assert "ref_hits=10" in details["summary_bits"]
    assert "ref_missing=3" in details["summary_bits"]
    assert "band_support=False" in details["summary_bits"]
    assert "paper_ready=False" in details["summary_bits"]


def test_ir_temperature_2d_summary_details_collects_sequence_matrix_and_transition_bits() -> None:
    details = _ir_temperature_2d_summary_details(
        {
            "n_frames": 48,
            "T_range_C": (35.0, 215.0),
            "sequence_axis_score": 0.94,
            "matrix_quality_score": 0.81,
            "cos_signal_score": 0.78,
            "sync_cross_peak_count": 12,
            "async_cross_peak_count": 12,
            "transition_count": 2,
            "band_index_transition_support_band_count": 3,
            "band_index_transition_reproducible": True,
            "neg_fraction": 0.08,
            "interpretation_ready": True,
            "paper_conclusion_ready": False,
        }
    )

    assert "frames=48" in details["summary_bits"]
    assert "T_range=(35.0, 215.0)" in details["summary_bits"]
    assert "sequence_axis=0.94" in details["summary_bits"]
    assert "matrix_quality=0.81" in details["summary_bits"]
    assert "cos_signal=0.78" in details["summary_bits"]
    assert "sync_peaks=12" in details["summary_bits"]
    assert "async_peaks=12" in details["summary_bits"]
    assert "transitions=2" in details["summary_bits"]
    assert "band_support=3" in details["summary_bits"]
    assert "trend_reproducible=True" in details["summary_bits"]
    assert "neg_fraction=0.08" in details["summary_bits"]
    assert "interpretation_ready=True" in details["summary_bits"]
    assert "paper_ready=False" in details["summary_bits"]


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


def test_nmr_summary_details_collect_snr_peak_and_xc_bits() -> None:
    assert hasattr(analysis_evidence_nmr, "_nmr_summary_details")

    details = analysis_evidence_nmr._nmr_summary_details(
        {"median_snr": 9.5},
        {"peak_count": 4},
        {"Xc_assignment_status": "supported"},
    )

    assert details["summary_bits"] == [
        "nmr_snr=9.5",
        "nmr_peaks=4",
        "nmr_xc=supported",
    ]


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


def test_nmr_analysis_bundle_collects_sections_and_confidence_signals() -> None:
    assert hasattr(analysis_evidence_nmr, "_nmr_analysis_bundle")

    bundle = analysis_evidence_nmr._nmr_analysis_bundle(
        {
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 4,
            "median_snr": 9.5,
            "mean_fwhm_ppm": 1.8,
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
        }
    )

    assert bundle["feature_evidence"]["n_peaks"] == 4
    assert bundle["signal_evidence"]["median_snr"] == 9.5
    assert bundle["peak_evidence"]["peak_count"] == 4
    assert bundle["assignment_evidence"]["phase_assignment_count"] == 2
    assert bundle["assignment_evidence"]["assigned_peak_fraction"] > 0
    assert bundle["phase_evidence"]["crystalline_peak_count"] == 1
    assert bundle["phase_evidence"]["amorphous_peak_count"] == 1
    assert bundle["structure_evidence"]["Xc_assignment_status"] == "supported"
    assert bundle["structure_evidence"]["paper_conclusion_ready"] is True
    assert any(item["name"] == "median_snr" for item in bundle["confidence_signals"])


@pytest.mark.parametrize(
    ("status", "expected_class", "expected_allowed", "expected_reason"),
    [
        ("supported", "supported", True, "phase_assignment_supported"),
        ("assignment_limited", "assignment_limited", False, "phase_assignment_limited"),
        ("missing_assignment", "missing_assignment", False, "phase_assignment_missing"),
    ],
)
def test_nmr_solid_c_assignment_readiness_is_explicit(
    status: str,
    expected_class: str,
    expected_allowed: bool,
    expected_reason: str,
) -> None:
    bundle = analysis_evidence_nmr._nmr_analysis_bundle(
        {
            "nucleus": "13C",
            "sample_state": "solid",
            "Xc_pct": 47.0,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "Xc_assignment_status": status,
            "ppm_axis_source": "default_range",
            "ppm_axis_reason": "jeol_metadata_units_unconfirmed",
            "ppm_axis_units": "ppm",
            "ppm_axis_calibrated": False,
            "ppm_axis_range": [240.0, -20.0],
        }
    )

    readiness = bundle["structure_evidence"]["assignment_readiness"]
    assert readiness["class"] == expected_class
    assert readiness["allowed"] is expected_allowed
    assert readiness["reason"] == expected_reason
    assert bundle["assignment_evidence"]["readiness"] == readiness


def test_nmr_assignment_source_is_preserved_in_evidence() -> None:
    bundle = analysis_evidence_nmr._nmr_analysis_bundle(
        {
            "nucleus": "13C",
            "sample_state": "solid",
            "assignment_source": "generic_region",
            "Xc_assignment_status": "assignment_limited",
        }
    )

    assert bundle["assignment_evidence"]["assignment_source"] == "generic_region"

def test_nmr_assignment_library_score_supports_xc_evidence() -> None:
    evidence = build_analysis_evidence(
        "NMR",
        output_parameters={
            "nucleus": "13C",
            "sample_state": "solid",
            "n_peaks": 3,
            "median_snr": 11.0,
            "mean_fwhm_ppm": 2.2,
            "Xc_method": "requires_crystalline_amorphous_assignment",
            "library_match_fraction": 0.82,
            "assignment_confidence": 0.78,
            "phase_pair_support": True,
            "solvent_overlap_penalty": 0.0,
            "matched_library_count": 3,
            "assignment_library_source": "PA6",
        },
        residual_pattern={"residual_type": "noise", "summary": "library assignments are paired"},
    ).to_dict()

    assignment = evidence["assignment_evidence"]
    structure = evidence["structure_evidence"]

    assert assignment["library_match_fraction"] == 0.82
    assert assignment["assignment_confidence"] == 0.78
    assert assignment["phase_pair_support"] is True
    assert assignment["matched_library_count"] == 3
    assert structure["Xc_assignment_status"] == "supported"
    assert structure["paper_conclusion_ready"] is True


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
