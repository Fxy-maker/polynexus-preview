from __future__ import annotations

from polynexus.gui.preprocess_decision_service import build_preprocess_ui_decision


def report_with(decision: str, confidence: str, simulated: str | None = None):
    return {
        "preprocess_decision": {
            "decision": decision,
            "simulated_decision": simulated or decision,
            "confidence_band": confidence,
            "reason_codes": ["noise_reduced"],
        },
        "selected_preprocess_config": {"smooth_window": 15},
        "preprocess_evidence": [
            {
                "candidate_id": "c1",
                "noise_reduction": 0.25,
                "peak_shift": 0.01,
                "fwhm_change": 0.02,
                "integrated_area_change": 0.01,
                "weak_peak_retention": 1.0,
                "physical_parameter_drift": 0.01,
            }
        ],
    }


def test_confirmation_exposes_selected_metrics_and_apply() -> None:
    view = build_preprocess_ui_decision(report_with("request_confirmation", "medium"))

    assert view.mode == "confirm"
    assert view.apply_enabled is True
    assert view.undo_enabled is False
    assert "weak_peak_retention" in view.metric_rows


def test_auto_accept_exposes_undo_without_reapplying() -> None:
    view = build_preprocess_ui_decision(report_with("auto_accept", "high"))

    assert view.mode == "auto_apply"
    assert view.apply_enabled is False
    assert view.undo_enabled is True


def test_shadow_and_invalid_reports_are_informational() -> None:
    shadow = build_preprocess_ui_decision(
        report_with("keep_original", "high", simulated="auto_accept")
    )
    invalid = build_preprocess_ui_decision({"preprocess_decision": "invalid"})

    assert shadow.mode == "shadow"
    assert shadow.apply_enabled is False
    assert invalid.mode == "keep_original"
    assert invalid.apply_enabled is False
    assert invalid.undo_enabled is False


def test_selected_candidate_controls_evidence_projection() -> None:
    report = report_with("request_confirmation", "medium")
    report["selected_candidate_id"] = "selected"
    report["preprocess_evidence"] = [
        {"candidate_id": "other", "weak_peak_retention": 0.0},
        {"candidate_id": "selected", "weak_peak_retention": 1.0},
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["weak_peak_retention"] == 1.0
