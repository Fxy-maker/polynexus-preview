from types import SimpleNamespace

import pytest

from polynexus.gui.analysis_history_service import ControlledOptimizationReviewParts
from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.results_review_service import (
    ai_tuning_report_benchmark_text,
    ai_tuning_report_decision_text,
    ai_tuning_report_summary_text,
    build_result_review_panel_texts_from_window,
    build_result_review_summary_snapshot,
    build_result_review_summary_text_from_window,
    ResultReviewPanelTexts,
    result_review_analysis_evidence_card_text,
    result_review_dsc_support_block_text,
    result_review_ir_support_block_text,
    result_review_ir_temperature_2d_user_summary_lines,
    result_review_round_core_summary_text,
    result_review_round_support_summary_text,
    results_next_step_text,
    results_risk_summary_text,
    result_review_panel_texts,
    result_review_saxs_semantic_details,
    result_review_saxs_semantic_lines,
    result_review_saxs_trend_text,
    result_review_summary_text,
    result_review_waxs_core_text,
    result_review_waxs_support_text,
)


class _FakeReviewWindow:
    def __init__(self):
        self._current_technique = "ir"

    def _current_results_record(self):
        return {
            "parameters": {"L_nm": 12.0},
            "results_summary": {"validation_summary": "Validation note"},
        }

    def _current_analysis_evidence(self):
        return {
            "feature_evidence": {
                "temperature_2d_evidence": {
                    "sequence_axis_score": 0.89,
                    "matrix_quality_score": 0.72,
                    "cos_signal_score": 0.76,
                    "interpretation_ready": True,
                    "paper_conclusion_ready": False,
                },
                "sequence_evidence": {
                    "stage_counts": {"heating": 23, "hold": 3, "cooling": 22}
                },
                "single_frame_evidence": {
                    "low_confidence_frame_ratio": 0.25,
                    "frame_assignment_confidence_mean": 0.82,
                    "frame_key_band_support_mean": 0.79,
                },
            }
        }

    def _history_result_metrics(self, current):
        return {"r_squared": 0.91}

    def _measured_result_summary_text(self, current):
        return "Sample A"

    def _current_result_origin_label(self):
        return "Manual run"

    def _is_current_result_confirmed(self):
        return True

    def _result_comparison_summary(self):
        return "Comparison note"

    def _result_source_summary_text(self, current):
        return "Source note"

    def _saxs_strain_evidence_snapshot(self, params, analysis_evidence):
        return {}

    def _current_result_history_context(self, current):
        return {}

    def _current_result_tuning_context(self, current):
        return {}

    def _joint_ai_context(self):
        return {}

    def _joint_ai_reminder_text(self, joint_context=None):
        return ""

    def _current_result_origin(self):
        return "manual_run"

    def _ai_tuning_goal_label(self, goal):
        return goal

    def _fallback_evidence_summary_text(self, analysis_evidence):
        return ""

    def _waxs_result_semantic_lines(self, current_metrics=None, analysis_evidence=None):
        return []

    def _saxs_strain_summary_text(self, params, analysis_evidence):
        return ""

    def _responsibility_boundary_summary(self):
        return "Boundary"


def test_results_risk_summary_text_prefers_saxs_mask_warning():
    previous = get_language()
    set_language("en")
    try:
        result = SimpleNamespace(
            validation_summary="",
            mask_truncated=True,
            beam_stop_contaminated=True,
            effective_q_min="0.1234",
        )

        text = results_risk_summary_text(
            {"batch_frames": 1},
            result,
            technique="saxs",
            analysis_evidence={},
        )

        assert text == tr("RESULTS_SUMMARY_RISK_MASK_AND_BEAMSTOP", "0.123")
    finally:
        set_language(previous)


def test_results_risk_summary_text_prefers_condition_axis_warning_for_batch_saxs():
    previous = get_language()
    set_language("en")
    try:
        result = SimpleNamespace(validation_summary="", mask_truncated=False, beam_stop_contaminated=False)

        text = results_risk_summary_text(
            {
                "batch_frames": 4,
                "condition_source": "header",
                "condition_confidence": 0.7,
                "condition_missing_frames": 1,
                "condition_continuity_score": 0.5,
            },
            result,
            technique="saxs",
            analysis_evidence={},
        )

        assert text == tr("RESULTS_SUMMARY_RISK_CONDITION_AXIS", "header", "0.70", "1", "0.50")
    finally:
        set_language(previous)


def test_results_next_step_text_prefers_saxs_strain_next_step_over_generic_single_result():
    previous = get_language()
    set_language("en")
    try:
        result = SimpleNamespace(validation_summary="", mask_truncated=False, beam_stop_contaminated=False)

        text = results_next_step_text(
            {"batch_frames": 2},
            result,
            mode="",
            technique="saxs",
            analysis_evidence={
                "feature_evidence": {
                    "condition_evidence": {"condition_label": "strain"},
                    "strain_structure_evidence": {"Q_star_rel_mean": 0.1},
                }
            },
        )

        assert text == "Next step | align the strain axis, low-q coverage, void evidence, and long-period anchor before deciding whether to tune again"
    finally:
        set_language(previous)


def test_results_next_step_text_prefers_fallback_conflict_before_strain():
    previous = get_language()
    set_language("en")
    try:
        result = SimpleNamespace(validation_summary="", mask_truncated=False, beam_stop_contaminated=False)

        text = results_next_step_text(
            {"batch_frames": 2},
            result,
            mode="",
            technique="saxs",
            analysis_evidence={
                "symptoms": [
                    {"name": "temperature_calibration_fallback_active"},
                    {"name": "batch_summary_conflicts_with_frame_evidence"},
                    {"name": "low_q_void_dominant"},
                ],
                "feature_evidence": {
                    "condition_evidence": {"condition_label": "strain"},
                    "strain_structure_evidence": {"Q_star_rel_mean": 0.1},
                },
                "batch_evidence": {
                    "batch_calibration_summary": {"fallback_ratio": 0.25, "raw_snapshot_rows": 7},
                },
            },
        )

        assert text == tr("RESULTS_SUMMARY_NEXT_FALLBACK_CONFLICT")
    finally:
        set_language(previous)


def test_result_review_summary_text_joins_core_and_saxs_sections_in_order():
    previous = get_language()
    set_language("en")
    try:
        summary = result_review_summary_text(
            {
                "current": {"results_summary": {"validation_summary": ""}},
                "technique": "saxs",
                "measured_text": "Sample A",
                "origin_label": "Manual run",
                "confirmed_label": "Confirmed",
                "validation_summary": "Validation note",
                "comparison_summary": "Comparison note",
                "metric_summary": "r_squared=0.91",
                "source_summary": "Source note",
                "saxs_semantic_lines": ["Interpretation line", "Window line"],
                "saxs_strain_text": "strain axis=confidence=0.88",
                "saxs_method_bits": ["lc_method=raw", "calibration_skipped_reason=missing"],
                "fallback_text": "Batch evidence | fallback",
                "responsibility_boundary": "Boundary | core provides evidence",
            }
        )

        expected = " | ".join(
            [
                tr("RESULTS_REVIEW_MEASURED", "Sample A"),
                "Manual run",
                "Confirmed",
                "Validation note",
                "Comparison note",
                tr("RESULTS_REVIEW_METRICS", "r_squared=0.91"),
                "Source note",
                "Interpretation line",
                "Window line",
                "SAXS | strain axis=confidence=0.88",
                "SAXS | lc_method=raw, calibration_skipped_reason=missing",
                "Batch evidence | fallback",
                "Boundary | core provides evidence",
            ]
        )
        assert summary == expected
    finally:
        set_language(previous)


def test_result_review_waxs_text_helpers_surface_core_and_support_bits():
    core_text = result_review_waxs_core_text({"n_peaks": 2, "Xc_pct": 69.6, "D_Scherrer_nm": 8.3})
    support_text = result_review_waxs_support_text(
        {
            "peak_support_score": 0.82,
            "background_stability_score": 0.74,
            "phase_support_score": 0.88,
            "size_support_score": 0.79,
            "waxs_support_score": 0.81,
            "feature_evidence": {
                "scherrer_trend_evidence": {
                    "D_trend_support_score": 0.77,
                }
            },
        }
    )

    assert core_text == "n_peaks=2, Xc_pct=69.6, D_Scherrer_nm=8.3"
    assert support_text == (
        "peak=0.820 | background=0.740 | phase=0.880 | size=0.790 | D_trend=0.770 | "
        "waxs_support_score=0.810"
    )


def test_result_review_saxs_semantic_helpers_surface_interpretation_window_and_boundary():
    previous = get_language()
    set_language("en")
    try:
        params = {
            "batch_frames": 3,
            "calibrated_fallback_active": True,
            "calibration_skipped_reason": "temperature_batch_lc_calibration",
            "batch_structure_summary": {
                "batch_rows": 3,
                "diagnostic_only_rows": 1,
                "low_confidence_rows": 1,
                "usable_rows": 1,
                "near_onset_rows": 1,
                "dominant_lc_reliability_status": "diagnostic_only",
                "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
                "dominant_melting_window_status": "near_onset",
            },
        }
        analysis_evidence = {
            "batch_evidence": {
                "batch_structure_summary": {
                    "batch_rows": 3,
                    "diagnostic_only_rows": 1,
                    "low_confidence_rows": 1,
                    "usable_rows": 1,
                    "near_onset_rows": 1,
                    "dominant_lc_reliability_status": "diagnostic_only",
                    "dominant_lc_reliability_reason": "low_lc_confidence|near_melting_onset",
                    "dominant_melting_window_status": "near_onset",
                }
            },
            "symptoms": [
                {"name": "diagnostic_lc_frames_present"},
                {"name": "temperature_sequence_near_melting_window"},
                {"name": "lc_unreliable_without_melting_proof"},
            ],
        }

        details = result_review_saxs_semantic_details(params, analysis_evidence, language="en")
        lines = result_review_saxs_semantic_lines(params, analysis_evidence, language="en")
        trend_text = result_review_saxs_trend_text(params, analysis_evidence, language="en")

        assert "diagnostic-only for lc" in details["interpretation"]
        assert details["status"] == "strain status: diagnostic-only"
        assert "near the SAXS-derived melting onset" in details["window"]
        assert "calibrated_fallback_active=True" in details["calibration"]
        assert "do not call this melting yet" in details["boundary"]
        assert lines == [
            tr("RESULTS_REVIEW_SAXS_INTERPRETATION", details["interpretation"]),
            tr("RESULTS_REVIEW_SAXS_WINDOW", details["window"]),
            tr("RESULTS_REVIEW_SAXS_CALIBRATION", details["calibration"]),
            tr("RESULTS_REVIEW_SAXS_BOUNDARY", details["boundary"]),
        ]
        assert "diagnostic-only for lc" in trend_text
        assert "near the SAXS-derived melting onset" in trend_text
        assert "temperature_batch_lc_calibration" in trend_text
        assert "do not call this melting yet" in trend_text
    finally:
        set_language(previous)


def test_result_review_analysis_evidence_card_text_surfaces_waxs_support_and_constraints():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_analysis_evidence_card_text(
            {
                "peak_evidence": {
                    "peak_count": 4,
                    "peak_gap_spread": 0.23,
                    "peak_width_spread": 0.11,
                },
                "background_evidence": {
                    "two_theta_offset": 0.02,
                    "background_method": "polyfit",
                    "amorphous_subtraction": True,
                },
                "phase_evidence": {
                    "Xc_pct": 61.2,
                    "crystallinity_method": "deconvolution",
                    "D_Scherrer_nm": 7.8,
                },
                "feature_evidence": {
                    "scherrer_trend_evidence": {
                        "D_trend_support_score": 0.77,
                        "D_trend_monotonicity": "decreasing",
                        "D_support_peak_count": 5,
                        "instrument_broadening_present": True,
                    }
                },
                "peak_support_score": 0.82,
                "background_stability_score": 0.74,
                "phase_support_score": 0.88,
                "size_support_score": 0.79,
                "waxs_support_score": 0.81,
                "constraint_summary": {
                    "status": "soft_warn",
                    "triggered_counts": {"hard_fail": 0, "soft_warn": 2, "evidence_only": 1},
                    "triggered_names": {"soft_warn": ["peak_shape"], "evidence_only": ["background_model"]},
                },
            },
            technique="waxs",
            language="en",
        )

        assert text.startswith("WAXS | peak=n=4")
        assert "background=offset=0.02, method=polyfit, halo=True" in text
        assert "phase=Xc=61.2, method=deconvolution, D=7.8" in text
        assert "trend=score=0.77, mode=decreasing, support=5, instrument_broadening=True" in text
        assert "Support | peak=0.820 | background=0.740 | phase=0.880 | size=0.790 | D_trend=0.770 | waxs_support_score=0.810" in text
        assert "constraints=status=soft_warn | hard_fail=0 | soft_warn=2 | evidence_only=1; Triggered: peak_shape, background_model" in text
    finally:
        set_language(previous)


def test_result_review_analysis_evidence_card_text_surfaces_ir_branch():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_analysis_evidence_card_text(
            {
                "feature_evidence": {
                    "reference_evidence": {"band_count": 6, "hit_count": 5, "missing_count": 1},
                    "assignment_evidence": {"assignment_confidence": 0.91},
                    "structure_evidence": {
                        "classification_basis": "peak_assignment",
                        "characteristic_band_support_ok": True,
                        "paper_conclusion_ready": True,
                    },
                }
            },
            technique="ir",
            language="en",
        )

        assert text == (
            "IR | Reference bands | total=6 | hit=5 | missing=1 ; "
            "Assignment confidence | 0.910 ; "
            "Decision basis | peak assignment ; "
            "Support chain | complete ; "
            "Conclusion state | usable as a conclusion candidate"
        )
    finally:
        set_language(previous)


def test_result_review_analysis_evidence_card_text_surfaces_dsc_branch():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_analysis_evidence_card_text(
            {
                "feature_evidence": {
                    "thermal_event_evidence": {
                        "Tg_C": 52.1,
                        "Tm_peak_C": 221.4,
                        "DHm_Jg": 45.6,
                        "scan_mode": "heating",
                        "exo_up": False,
                    },
                    "event_support_evidence": {
                        "event_support_score": 0.84,
                        "baseline_stability_score": 0.76,
                        "thermodynamic_consistency_score": 0.81,
                        "supported_event_fraction": 3,
                    },
                    "baseline_evidence": {
                        "baseline_corr": "adaptive",
                        "residual_type": "smooth",
                    },
                    "structure_evidence": {
                        "paper_conclusion_candidate": True,
                        "paper_conclusion_ready": False,
                    },
                }
            },
            technique="dsc",
            language="en",
        )

        assert text == (
            "DSC | Measured thermal events | Tg_C=52.1, Tm_peak_C=221.4, DHm_Jg=45.6 | "
            "Support chain | event=0.840 | baseline=0.760 | thermo=0.810 | fraction=3 | "
            "Conclusion state | paper-ready candidate | "
            "Key context | paper_candidate=True | paper_ready=False | scan=heating | exo=False"
        )
    finally:
        set_language(previous)


def test_result_review_ir_support_block_text_surfaces_source_summary_sections():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_ir_support_block_text(
            {
                "feature_evidence": {
                    "reference_evidence": {"band_count": 3, "hit_count": 2, "missing_count": 1},
                    "assignment_evidence": {"assignment_confidence": 0.68},
                    "structure_evidence": {
                        "classification_basis": "peak_assignment",
                        "characteristic_band_support_ok": True,
                        "paper_conclusion_ready": False,
                    },
                }
            }
        )

        assert text == (
            "Detected bands | band_count=3, hit_count=2, missing_count=1 | "
            "Assignment confidence | 0.680 | "
            "Decision basis | peak assignment | "
            "Support chain | complete | "
            "Conclusion state | pending review | "
            "Main risk | missing=1"
        )
    finally:
        set_language(previous)


def test_result_review_ir_temperature_2d_user_summary_lines_surface_key_statuses():
    previous = get_language()
    set_language("en")
    try:
        lines = result_review_ir_temperature_2d_user_summary_lines(
            {
                "feature_evidence": {
                    "temperature_2d_evidence": {
                        "sequence_axis_score": 0.89,
                        "matrix_quality_score": 0.72,
                        "cos_signal_score": 0.76,
                        "interpretation_ready": True,
                        "paper_conclusion_ready": False,
                    },
                    "sequence_evidence": {
                        "stage_counts": {"heating": 23, "hold": 3, "cooling": 22}
                    },
                    "single_frame_evidence": {
                        "low_confidence_frame_ratio": 0.25,
                        "frame_assignment_confidence_mean": 0.82,
                        "frame_key_band_support_mean": 0.79,
                    },
                    "transform_evidence": {"noda_rule_interpretation_ready": True},
                }
            }
        )

        assert "Sequence axis" in lines[0]
        assert "Figure status" in lines[1]
        assert "Interpretation status" in lines[2]
        assert "Frame quality" in lines[3]
    finally:
        set_language(previous)


def test_build_result_review_summary_text_from_window_joins_ir_sections():
    previous = get_language()
    set_language("en")
    try:
        text = build_result_review_summary_text_from_window(_FakeReviewWindow())

        assert "Sample A" in text
        assert "Manual run" in text
        assert "Validation note" in text
        assert "Comparison note" in text
        assert "r_squared=0.91" in text
        assert "Source note" in text
        assert "Sequence axis" in text
        assert "Figure status" in text
        assert "Interpretation status" in text
        assert "Frame quality" in text
        assert "Boundary" in text
    finally:
        set_language(previous)


def test_ai_tuning_report_text_helpers_render_summary_decision_and_benchmark():
    previous = get_language()
    set_language("en")
    try:
        report = {
            "rounds": 4,
            "best_r_squared": 0.93,
            "convergence_reason": "plateau",
            "improvement": {"r_squared_abs": 0.02},
            "history": [
                {"round_num": 1, "accepted": True},
                {"round_num": 2, "accepted": False, "llm_advice": {"rollback_reason": "constraint drift"}},
            ],
            "benchmark_summary": {
                "average_objective_delta": 0.015,
                "acceptance_rate": 0.5,
                "rejection_rate": 0.25,
                "constraint_hit_rate": 0.75,
                "symptom_fix_rate": 0.2,
            },
        }

        assert "plateau" in ai_tuning_report_summary_text(report)
        assert "constraint drift" in ai_tuning_report_decision_text(report)
        assert "0.015" in ai_tuning_report_benchmark_text(
            report,
            delta_text_fn=lambda value: f"{float(value):.3f}",
            rate_text_fn=lambda value: f"{float(value) * 100:.1f}%",
        )
    finally:
        set_language(previous)


def test_result_review_dsc_support_block_text_surfaces_source_summary_sections():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_dsc_support_block_text(
            {
                "feature_evidence": {
                    "thermal_event_evidence": {
                        "scan_mode": "heating",
                        "exo_up": True,
                    },
                    "event_support_evidence": {
                        "event_support_score": 0.84,
                        "baseline_stability_score": 0.76,
                        "thermodynamic_consistency_score": 0.81,
                        "supported_event_fraction": 0.67,
                        "scan_r_squared_median": 0.93,
                    },
                    "baseline_evidence": {
                        "baseline_corr": "poly",
                        "residual_type": "random",
                    },
                    "structure_evidence": {
                        "paper_conclusion_candidate": True,
                        "paper_conclusion_ready": False,
                    },
                }
            },
            include_measurement=False,
        )

        assert text == (
            "Support chain | event=0.840 | baseline=0.760 | thermo=0.810 | fraction=0.67 | scan=0.930 | "
            "Conclusion state | paper-ready candidate | "
            "Key context | paper_candidate=True | paper_ready=False | scan=heating | exo=True"
        )
    finally:
        set_language(previous)


def test_result_review_round_core_summary_text_uses_waxs_key_order():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_round_core_summary_text(
            {
                "n_peaks": 4,
                "Xc_pct": 61.2,
                "D_Scherrer_nm": 7.8,
                "quality_score": 0.99,
            },
            technique="waxs",
        )

        assert text == "n_peaks=4 | Xc_pct=61.2 | D_Scherrer_nm=7.8"
    finally:
        set_language(previous)


def test_result_review_round_support_summary_text_surfaces_ir_branch_without_prefix():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_round_support_summary_text(
            {
                "feature_evidence": {
                    "reference_evidence": {"band_count": 3, "hit_count": 2, "missing_count": 1},
                    "assignment_evidence": {"assignment_confidence": 0.68},
                    "structure_evidence": {
                        "classification_basis": "peak_assignment",
                        "characteristic_band_support_ok": False,
                        "paper_conclusion_ready": False,
                    },
                }
            },
            technique="ir",
            language="en",
        )

        assert text == (
            "Reference bands | total=3 | hit=2 | missing=1 | "
            "Assignment confidence | 0.680 | "
            "Decision basis | peak assignment | "
            "Support chain | pending | "
            "Conclusion state | pending review"
        )
    finally:
        set_language(previous)


def test_result_review_round_support_summary_text_surfaces_generic_stability_and_constraints():
    previous = get_language()
    set_language("en")
    try:
        text = result_review_round_support_summary_text(
            {
                "stability_evidence": {
                    "stability_score": 0.91,
                    "parameter_stability_score": 0.82,
                    "method_agreement_score": 0.73,
                    "batch_continuity_score": 0.64,
                    "stability_flags": ["drift", "noise"],
                },
                "constraint_summary": {
                    "status": "soft_warn",
                    "triggered_counts": {"hard_fail": 0, "soft_warn": 1, "evidence_only": 0},
                    "triggered_names": {"soft_warn": ["fit_floor"]},
                },
            },
            technique="nmr",
            language="en",
        )

        assert text == (
            "score=0.910 | param=0.820 | method=0.730 | batch=0.640 | flags=drift, noise | "
            "status=soft_warn | hard_fail=0 | soft_warn=1 | evidence_only=0; Triggered: fit_floor"
        )
    finally:
        set_language(previous)


def test_result_review_panel_texts_compose_controlled_rerun_sections():
    previous = get_language()
    set_language("en")
    try:
        parts = result_review_panel_texts(
            {
                "current": {"results_summary": {"validation_summary": ""}},
                "technique": "waxs",
                "current_origin": "controlled_optimization_rerun",
                "current_label": "Sample A",
                "current_origin_label": "Manual run",
                "current_confirmed_label": "Confirmed reference",
                "measured_text": "Measured result | Sample A",
                "validation_summary": "Validation note",
                "comparison_summary": "Comparison note",
                "analysis_evidence": {
                    "symptoms": [{"name": "temperature_calibration_fallback_active"}],
                    "batch_evidence": {
                        "batch_calibration_summary": {
                            "fallback_ratio": 0.25,
                            "raw_snapshot_rows": 7,
                        }
                    },
                },
                "history_context": {
                    "benchmark_summary": {"average_objective_delta": 0.018},
                    "stop_reason": "stop here",
                    "remaining_risks": "keep checking",
                    "next_goal": "recheck",
                    "tuning_goal": "focus this round",
                },
                "tuning_context": {
                    "history": [
                        {"round_num": 1, "accepted": True, "r_squared_after": 0.92},
                    ],
                    "benchmark_summary": {"average_objective_delta": 0.018},
                    "tuning_goal": "focus this round",
                },
                "joint_context": {
                    "summary": "Cross-tech consistency",
                    "issue_count": 1,
                    "issue_families": ["phi_c inconsistency"],
                },
                "responsibility_boundary": "Boundary | core provides evidence",
                "fallback_next_text": "Fallback next",
                "trend_text": "axis=0.940",
                "is_controlled_rerun": True,
            },
            benchmark_summary_text_fn=lambda summary: "Benchmark summary",
            benchmark_delta_text_fn=lambda value: f"{float(value):+.3f}",
            tuning_goal_label_fn=lambda value: f"Goal: {value}",
            family_label_fn=lambda value: str(value).replace("_", " ").title(),
        )

        assert isinstance(parts, ResultReviewPanelTexts)
        assert "Sample A" in parts.meta_text
        assert "Manual run" in parts.meta_text
        assert "Confirmed reference" in parts.meta_text
        assert "Goal: focus this round" in parts.meta_text
        assert "Measured result" in parts.benchmark_text
        assert "Benchmark summary" in parts.benchmark_text
        assert "baseline delta +0.018" in parts.chain_text
        assert "accepted 1 rounds" in parts.chain_text
        assert "WAXS trend" in parts.trend_text
        assert "axis=0.940" in parts.trend_text
        assert "Boundary | core provides evidence" in parts.boundary_text
        assert "Batch evidence" in parts.boundary_text
        assert parts.joint_visible is True
        assert "Cross-tech consistency" in parts.joint_text
        assert "Phi C Inconsistency" in parts.joint_text
        assert "Validation note" in parts.risk_text
        assert "stop here" in parts.risk_text
        assert "keep checking" in parts.risk_text
        assert "recheck" in parts.next_text
        assert parts.title_text == tr("RESULTS_REVIEW_TITLE_CONFIRMED")
    finally:
        set_language(previous)


def test_result_review_summary_text_appends_controlled_optimization_tail():
    previous = get_language()
    set_language("en")
    try:
        summary = result_review_summary_text(
            {
                "current": {"results_summary": {"validation_summary": ""}},
                "technique": "saxs",
                "measured_text": "",
                "origin_label": "",
                "confirmed_label": "Confirmed",
                "validation_summary": "",
                "comparison_summary": "",
                "metric_summary": "",
                "current_result_origin": "controlled_optimization_rerun",
                "optimization_parts": ControlledOptimizationReviewParts(
                    tuning_goal="Focus this round",
                    benchmark_text="",
                    stop_reason="",
                    remaining_risks="",
                    next_goal="",
                ),
                "chain_text": "Run trace | Step 1",
                "joint_summary": "Cross-tech consistency",
                "joint_reminder_text": "Joint check | focus on families",
                "responsibility_boundary": "Boundary | core provides evidence",
            }
        )

        expected = " | ".join(
            [
                "Confirmed",
                tr("RESULTS_REVIEW_TUNING_GOAL", "Focus this round"),
                tr("RESULTS_REVIEW_NO_BENCHMARK"),
                tr("RESULTS_REVIEW_NO_RISK"),
                "Run trace | Step 1",
                "Cross-tech consistency | Joint check | focus on families",
                "Boundary | core provides evidence",
            ]
        )
        assert summary == expected
    finally:
        set_language(previous)


def test_result_review_summary_text_propagates_effective_q_float_errors():
    class BrokenFloat:
        def __float__(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        results_risk_summary_text(
            params={},
            result=SimpleNamespace(mask_truncated=True, beam_stop_contaminated=True, effective_q_min=BrokenFloat()),
            technique="saxs",
            analysis_evidence={},
        )


def test_result_review_summary_text_propagates_batch_frames_int_errors():
    class BrokenInt:
        def __int__(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        results_risk_summary_text(
            params={"batch_frames": BrokenInt()},
            result=None,
            technique="saxs",
            analysis_evidence={},
        )


def test_build_result_review_panel_texts_from_window_uses_window_state():
    previous = get_language()
    set_language("en")
    try:
        class _Label:
            def __init__(self, text):
                self._text = text

            def text(self):
                return self._text

        class _FakePanelWindow:
            _current_technique = "saxs"
            _results_summary_risk_label = _Label("Risk label")
            _results_summary_next_label = _Label("Fallback next")

            def _current_results_record(self):
                return {
                    "parameters": {"lc_method": "normalize"},
                    "results_summary": {"validation_summary": ""},
                }

            def _current_analysis_evidence(self):
                return {"symptoms": []}

            def _current_result_history_context(self, current):
                return {"next_goal": "history next"}

            def _current_result_tuning_context(self, current):
                return {"tuning_goal": "risk", "history": []}

            def _joint_ai_context(self):
                return {"summary": "Joint summary"}

            def _current_result_origin(self):
                return "controlled_optimization_rerun"

            def _current_result_label_for_confirmation(self):
                return "Sample A"

            def _current_result_origin_label(self):
                return "Recommended rerun"

            def _measured_result_summary_text(self, current):
                return "Measured result | Sample A"

            def _responsibility_boundary_summary(self):
                return "Boundary summary"

            def _is_current_result_confirmed(self):
                return True

            def _ai_tuning_goal_label(self, value):
                return f"Goal: {value}"

            def _benchmark_summary_text(self, summary):
                return "Benchmark summary"

            def _benchmark_delta_text(self, value):
                return f"{float(value):+.3f}"

            def _joint_issue_family_label(self, value):
                return str(value)

        parts = build_result_review_panel_texts_from_window(_FakePanelWindow())

        assert isinstance(parts, ResultReviewPanelTexts)
        assert "Sample A" in parts.meta_text
        assert "Goal: risk" in parts.meta_text
        assert "Measured result | Sample A" in parts.benchmark_text
        assert "Risk label" in parts.risk_text
        assert "history next" in parts.next_text
    finally:
        set_language(previous)


def test_build_result_review_summary_snapshot_populates_controlled_optimization_parts():
    previous = get_language()
    set_language("en")
    try:
        snapshot = build_result_review_summary_snapshot(
            current={"results_summary": {"validation_summary": ""}},
            technique="waxs",
            measured_text="Measured result | Sample A",
            origin_label="Manual run",
            confirmed_label="Confirmed reference",
            validation_summary="Validation note",
            comparison_summary="Comparison note",
            current_metrics={"r_squared": 0.91},
            source_summary="Source note",
            fallback_text="Fallback note",
            current_origin="controlled_optimization_rerun",
            tuning_context={
                "tuning_goal": "focus this round",
                "benchmark_text": "Benchmark summary",
                "history": [{"round_num": 1, "accepted": True, "r_squared_after": 0.92}],
            },
            history_context={
                "benchmark_summary": {"average_objective_delta": 0.018},
                "stop_reason": "stop here",
                "remaining_risks": "keep checking",
                "next_goal": "recheck",
                "tuning_goal": "focus this round",
            },
            tuning_goal_label_fn=lambda value: f"Goal: {value}",
            benchmark_summary_text_fn=lambda summary: "Benchmark summary",
            chain_text="baseline delta +0.018",
            joint_summary="Cross-tech consistency",
            joint_reminder_text="Review phi_c inconsistency",
            responsibility_boundary="Boundary | core provides evidence",
            waxs_core_text="n_peaks=4",
            waxs_support_text="peak=0.820",
            waxs_semantic_lines=["WAXS | trend"],
        )

        assert snapshot["current"] == {"results_summary": {"validation_summary": ""}}
        assert snapshot["technique"] == "waxs"
        assert snapshot["optimization_parts"].tuning_goal == "Goal: focus this round"
        assert snapshot["optimization_parts"].benchmark_text == "Benchmark summary"
        assert snapshot["chain_text"] == "baseline delta +0.018"
        assert snapshot["joint_summary"] == "Cross-tech consistency"
        assert snapshot["responsibility_boundary"] == "Boundary | core provides evidence"
        assert snapshot["waxs_semantic_lines"] == ["WAXS | trend"]
    finally:
        set_language(previous)
