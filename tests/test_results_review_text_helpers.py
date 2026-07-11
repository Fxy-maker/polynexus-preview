from __future__ import annotations

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.results_review_text_helpers import (
    ai_tuning_report_benchmark_text,
    ai_tuning_report_decision_text,
    ai_tuning_report_summary_text,
    evidence_symptom_names,
    result_review_ir_temperature_2d_user_summary_lines,
    result_review_waxs_support_text,
)


def test_evidence_symptom_names_deduplicates_named_symptoms() -> None:
    assert evidence_symptom_names(
        {
            "symptoms": [
                {"name": "alpha"},
                {"name": "alpha"},
                {"name": "beta"},
                {"name": ""},
                None,
            ]
        }
    ) == {"alpha", "beta"}


def test_ai_tuning_report_text_helpers_format_expected_strings() -> None:
    previous = get_language()
    set_language("en")
    try:
        report = {
            "rounds": 3,
            "best_r_squared": 0.987,
            "improvement": {"r_squared_abs": 0.012},
            "convergence_reason": "plateau",
            "history": [
                {"round_num": 1, "accepted": True},
                {
                    "round_num": 2,
                    "accepted": False,
                    "llm_advice": {"rollback_reason": "constraint drift"},
                },
            ],
            "benchmark_summary": {
                "average_objective_delta": 0.015,
                "acceptance_rate": 0.5,
                "rejection_rate": 0.5,
                "constraint_hit_rate": 0.25,
                "symptom_fix_rate": 0.75,
            },
        }

        assert "plateau" in ai_tuning_report_summary_text(report)
        assert "constraint drift" in ai_tuning_report_decision_text(report)
        assert "0.015" in ai_tuning_report_benchmark_text(
            report,
            delta_text_fn=lambda value: f"{float(value):.3f}",
            rate_text_fn=lambda value: f"{float(value):.0%}",
        )
    finally:
        set_language(previous)


def test_result_review_ir_temperature_2d_user_summary_lines_surface_key_statuses() -> None:
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
                }
            }
        )

        assert len(lines) == 5
        assert lines[0].startswith("Sequence axis")
        assert lines[1].startswith("Figure status")
        assert lines[-1].startswith("Sequence trust")
    finally:
        set_language(previous)


def test_result_review_waxs_support_text_includes_scores() -> None:
    previous = get_language()
    set_language("en")
    try:
        text = result_review_waxs_support_text(
            {
                "feature_evidence": {
                    "scherrer_trend_evidence": {"D_trend_support_score": 0.61},
                    "peak_support_score": 0.71,
                    "background_stability_score": 0.62,
                    "phase_support_score": 0.53,
                    "size_support_score": 0.44,
                    "waxs_support_score": 0.5,
                }
            }
        )

        assert "peak=0.710" in text
        assert "D_trend=0.610" in text
        assert text == "peak=0.710 | background=0.620 | phase=0.530 | size=0.440 | D_trend=0.610"
    finally:
        set_language(previous)
