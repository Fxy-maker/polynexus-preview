from __future__ import annotations

from collections import UserDict

import pytest

from polynexus.core.preprocess_optimization import stable_config_hash
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


def saxs_stability_report(
    decision: str = "request_confirmation",
    *,
    complete_contract: bool = True,
    include_orientation_axis: bool = True,
):
    candidate_id = "saxs-stability-1"
    original_config = {"q_min": 0.01}
    selected_config = {"q_min": 0.02}
    frame_values = {
        "f_herman_raw": [0.10, 0.20, 0.30, 0.40, 0.50],
        "orientation_strength": [0.2, 0.3, 0.4, 0.5, 0.6],
    }
    finite_counts = {
        "f_herman_raw": 5,
        "orientation_strength": 5,
    }
    if include_orientation_axis:
        frame_values["orientation_axis_deg"] = [2.0, 3.0, None, 5.0, 6.0]
        finite_counts["orientation_axis_deg"] = 4
    reason_codes = [] if include_orientation_axis else ["orientation_axis_unavailable"]
    report = {
        "technique": "SAXS",
        "mode": "strain",
        "preprocess_decision": {
            "decision": decision,
            "simulated_decision": decision,
            "confidence_band": "medium",
            "reason_codes": reason_codes,
            "hard_guard_results": {
                "stability_plateau": True,
                "physical_gate": True,
                "quality_gate": True,
                "cross_frame_continuity": True,
            },
        },
        "selected_candidate_id": candidate_id,
        "original_preprocess_config": original_config,
        "selected_preprocess_config": selected_config,
        "preprocess_candidates": [
            {
                "candidate_id": candidate_id,
                "base_config_hash": stable_config_hash(original_config),
                "config_delta": selected_config,
            }
        ],
        "stability_report": {
            "mode": "strain",
            "decision": decision,
            "complete": True,
            "plateau": {
                "connected": True,
                "trial_indices": [1, 2, 3, 4],
                "coverage_fraction": 0.8,
                "parameter_bounds": {"q_min": [0.01, 0.03]},
                "active_dimensions": ["q_min", "chi_halfwidth"],
                "spread_dimensions": ["q_min", "chi_halfwidth"],
            },
            "active_dimensions": ["q_min", "chi_halfwidth"],
            "excluded_dimensions": {"bg_scale_value": "manual_background_inactive"},
            "continuity": {
                "status": "passed",
                "passed": True,
                "frame_count": 5,
                "metric_finite_frame_count": finite_counts,
            },
            "physics_gate_passed": True,
            "quality_gate_passed": True,
            "reason_codes": reason_codes,
            "perturbation_intervals": {
                "score": {"lower": 0.71, "median": 0.82, "upper": 0.90, "replicates": 100}
            },
            "bootstrap": {"legacy_only": {"median": -1.0}},
            "trials": [
                {
                    "index": 4,
                    "frame_values": frame_values,
                    "reason_codes": reason_codes,
                }
            ],
        },
    }
    if not complete_contract:
        report["selected_candidate_id"] = ""
        report["preprocess_candidates"] = []
    return report


def test_confirmation_exposes_selected_metrics_and_apply() -> None:
    view = build_preprocess_ui_decision(report_with("request_confirmation", "medium"))

    assert view.mode == "confirm"
    assert view.apply_enabled is True
    assert view.undo_enabled is False
    assert "weak_peak_retention" in view.metric_rows
    assert view.evidence_kind == "generic"
    assert "protected metrics available" in view.summary


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


def test_saxs_stability_projects_platform_continuity_and_intervals() -> None:
    view = build_preprocess_ui_decision(saxs_stability_report())

    assert view.evidence_kind == "saxs_stability"
    assert view.metric_rows["platform_points"] == 4
    assert view.metric_rows["platform_coverage"] == 0.8
    assert view.metric_rows["platform_bounds"] == {"q_min": [0.01, 0.03]}
    assert view.metric_rows["active_dimensions"] == ["q_min", "chi_halfwidth"]
    assert view.metric_rows["excluded_dimensions"] == {
        "bg_scale_value": "manual_background_inactive"
    }
    assert view.metric_rows["continuity_status"] == "passed"
    assert view.metric_rows["continuity_frame_count"] == 5
    assert view.metric_rows["physics_gate_passed"] is True
    assert view.metric_rows["quality_gate_passed"] is True
    assert view.metric_rows["stability_decision"] == "request_confirmation"
    assert view.metric_rows["perturbation_intervals"] == {
        "score": {"lower": 0.71, "median": 0.82, "upper": 0.90, "replicates": 100}
    }
    assert "protected metrics available" not in view.summary
    assert "platform" in view.summary.lower()


def test_saxs_stability_projects_only_observed_orientation_coverage() -> None:
    observed = build_preprocess_ui_decision(saxs_stability_report())
    missing_axis = build_preprocess_ui_decision(
        saxs_stability_report(include_orientation_axis=False)
    )

    assert observed.metric_rows["orientation_status"] == "partial"
    assert observed.metric_rows["orientation_coverage"]["orientation_axis_deg"] == {
        "finite_frames": 4,
        "frame_count": 5,
        "fraction": 0.8,
    }
    assert missing_axis.metric_rows["orientation_status"] == "partial"
    assert "orientation_axis_deg" not in missing_axis.metric_rows["orientation_coverage"]
    assert missing_axis.metric_rows["orientation_coverage"]["f_herman_raw"]["fraction"] == 1.0


def test_saxs_stability_uses_bootstrap_only_as_legacy_interval_fallback() -> None:
    report = saxs_stability_report()
    report["stability_report"].pop("perturbation_intervals")

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["perturbation_intervals"] == {
        "legacy_only": {"median": -1.0}
    }


def test_saxs_evidence_does_not_enable_incomplete_confirmation_contract() -> None:
    view = build_preprocess_ui_decision(
        saxs_stability_report(complete_contract=False)
    )

    assert view.evidence_kind == "saxs_stability"
    assert view.mode == "confirm"
    assert view.apply_enabled is False


def test_static_not_applicable_continuity_is_a_complete_ui_contract() -> None:
    report = saxs_stability_report()
    report["mode"] = "static"
    report["stability_report"]["mode"] = "static"
    report["stability_report"]["continuity"] = {
        "passed": False,
        "status": "not_applicable",
        "frame_count": 0,
    }
    report["preprocess_decision"]["hard_guard_results"][
        "cross_frame_continuity"
    ] = True

    view = build_preprocess_ui_decision(report)

    assert view.mode == "confirm"
    assert view.apply_enabled is True
    assert view.metric_rows["continuity_status"] == "not_applicable"


def test_nonstatic_failed_or_insufficient_continuity_disables_apply() -> None:
    for status in ("failed", "insufficient"):
        report = saxs_stability_report()
        report["stability_report"]["continuity"].update(
            {"passed": False, "status": status}
        )
        report["preprocess_decision"]["hard_guard_results"][
            "cross_frame_continuity"
        ] = False

        view = build_preprocess_ui_decision(report)

        assert view.apply_enabled is False


def test_wrong_nonempty_candidate_base_hash_disables_apply() -> None:
    report = saxs_stability_report()
    report["preprocess_candidates"][0]["base_config_hash"] = "wrong-nonempty-hash"

    view = build_preprocess_ui_decision(report)

    assert view.apply_enabled is False


def test_orientation_all_nonfinite_is_unavailable() -> None:
    report = saxs_stability_report()
    report["stability_report"]["continuity"].pop("metric_finite_frame_count")
    report["stability_report"]["trials"][0]["frame_values"] = {
        "f_herman_raw": [None] * 5,
        "orientation_axis_deg": [float("nan")] * 5,
    }

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "unavailable"
    assert all(
        row["finite_frames"] == 0
        for row in view.metric_rows["orientation_coverage"].values()
    )


def test_aggregate_orientation_counts_are_authoritative_and_zero_is_partial() -> None:
    report = saxs_stability_report()
    report["stability_report"]["continuity"]["metric_finite_frame_count"] = {
        "orientation_axis_deg": 5,
        "f_herman_raw": 0,
    }
    report["stability_report"]["trials"][0]["frame_values"] = {
        "orientation_axis_deg": [1.0, 2.0, 3.0, 4.0, 5.0],
        "f_herman_raw": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    }

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "partial"
    assert view.metric_rows["orientation_coverage"]["f_herman_raw"] == {
        "finite_frames": 0,
        "frame_count": 5,
        "fraction": 0.0,
    }


def test_trial_orientation_coverage_uses_selected_plateau_minimum() -> None:
    report = saxs_stability_report()
    report["stability_report"]["continuity"].pop("metric_finite_frame_count")
    report["stability_report"]["plateau"]["trial_indices"] = [4, 5]
    report["stability_report"]["trials"] = [
        {
            "index": 4,
            "frame_values": {"orientation_axis_deg": [1.0, 2.0, 3.0, 4.0, 5.0]},
            "reason_codes": [],
        },
        {
            "index": 5,
            "frame_values": {"orientation_axis_deg": [1.0, None, 3.0, None, 5.0]},
            "reason_codes": [],
        },
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "partial"
    assert view.metric_rows["orientation_coverage"]["orientation_axis_deg"] == {
        "finite_frames": 3,
        "frame_count": 5,
        "fraction": 0.6,
    }


def test_trial_orientation_coverage_counts_missing_selected_metric_as_zero() -> None:
    report = saxs_stability_report()
    report["stability_report"]["continuity"].pop("metric_finite_frame_count")
    report["stability_report"]["plateau"]["trial_indices"] = [4, 5]
    report["stability_report"]["trials"] = [
        {
            "index": 4,
            "frame_values": {"orientation_axis_deg": [1.0, 2.0, 3.0, 4.0, 5.0]},
            "reason_codes": [],
        },
        {
            "index": 5,
            "frame_values": {"f_herman_raw": [0.1, 0.2, 0.3, 0.4, 0.5]},
            "reason_codes": [],
        },
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "unavailable"
    assert view.metric_rows["orientation_coverage"]["orientation_axis_deg"][
        "finite_frames"
    ] == 0
    assert view.metric_rows["orientation_coverage"]["f_herman_raw"][
        "finite_frames"
    ] == 0


def test_mask_only_orientation_dimension_is_visible_without_metrics() -> None:
    report = saxs_stability_report(include_orientation_axis=False)
    report["stability_report"]["active_dimensions"] = ["mask_dilation_px"]
    report["stability_report"]["continuity"].pop("metric_finite_frame_count")
    report["stability_report"]["trials"] = []
    report["stability_report"]["reason_codes"] = []
    report["preprocess_decision"]["reason_codes"] = []

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "unavailable"
    assert view.metric_rows["orientation_coverage"] == {}


def test_legacy_unknown_orientation_reason_downgrades_finite_evidence() -> None:
    report = saxs_stability_report(include_orientation_axis=False)
    report["stability_report"]["reason_codes"] = ["tensile_axis_unknown"]
    report["preprocess_decision"]["reason_codes"] = ["tensile_axis_unknown"]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "partial"


def test_empty_stability_mapping_is_saxs_evidence_and_fails_closed() -> None:
    report = report_with("request_confirmation", "medium")
    report["stability_report"] = {}

    view = build_preprocess_ui_decision(report)

    assert view.evidence_kind == "saxs_stability"
    assert view.metric_rows["platform_points"] == 0
    assert view.apply_enabled is False
    assert "protected metrics available" not in view.summary


def test_malformed_stability_numbers_and_indices_fail_closed_without_raising() -> None:
    report = saxs_stability_report()
    report["stability_report"]["plateau"].update(
        {
            "point_count": float("nan"),
            "coverage_fraction": float("inf"),
            "trial_indices": [[], {"bad": "index"}],
        }
    )
    report["stability_report"]["continuity"].update(
        {
            "frame_count": -5,
            "metric_finite_frame_count": {
                "orientation_axis_deg": float("inf"),
                "f_herman_raw": -3,
            },
        }
    )
    report["stability_report"]["trials"] = [
        {
            "index": [],
            "frame_values": {"orientation_axis_deg": [1.0, 2.0]},
            "reason_codes": [],
        }
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["platform_points"] == 0
    assert view.metric_rows["platform_coverage"] == 0.0
    assert view.metric_rows["continuity_frame_count"] == 0
    assert view.metric_rows["orientation_status"] == "unavailable"
    assert all(
        row["finite_frames"] >= 0
        and row["frame_count"] >= 0
        and 0.0 <= row["fraction"] <= 1.0
        for row in view.metric_rows["orientation_coverage"].values()
    )


def test_confirmation_validator_allows_subset_delta_and_mapping_configs() -> None:
    report = saxs_stability_report()
    original = UserDict({"q_min": 0.01, "q_max": 0.30})
    selected = UserDict({"q_min": 0.02, "q_max": 0.30})
    report["mode"] = "SAXS.Strain"
    report["stability_report"]["mode"] = "SAXS.Strain"
    report["original_preprocess_config"] = original
    report["selected_preprocess_config"] = selected
    report["preprocess_candidates"][0].update(
        {
            "base_config_hash": stable_config_hash(dict(original)),
            "config_delta": {"q_min": 0.02},
        }
    )

    view = build_preprocess_ui_decision(report)

    assert view.mode == "confirm"
    assert view.apply_enabled is True
    assert view.selected_config == {"q_min": 0.02, "q_max": 0.30}


def test_static_alias_uses_canonical_mode_for_not_applicable_continuity() -> None:
    report = saxs_stability_report()
    report["mode"] = "SAXS.Static"
    report["stability_report"]["mode"] = "SAXS.Static"
    report["stability_report"]["continuity"] = {
        "passed": False,
        "status": "not_applicable",
        "frame_count": 0,
    }
    report["preprocess_decision"]["hard_guard_results"][
        "cross_frame_continuity"
    ] = True

    view = build_preprocess_ui_decision(report)

    assert view.apply_enabled is True


def test_stability_auto_accept_is_explicit_confirmation_not_auto_apply() -> None:
    complete = build_preprocess_ui_decision(saxs_stability_report("auto_accept"))
    failed_report = saxs_stability_report("auto_accept")
    failed_report["stability_report"]["quality_gate_passed"] = False
    failed_report["preprocess_decision"]["hard_guard_results"]["quality_gate"] = False
    failed = build_preprocess_ui_decision(failed_report)

    assert complete.mode == "confirm"
    assert complete.apply_enabled is True
    assert complete.undo_enabled is False
    assert failed.mode == "confirm"
    assert failed.apply_enabled is False
    assert failed.undo_enabled is False


def test_empty_plateau_does_not_project_rejected_trial_orientation() -> None:
    report = saxs_stability_report()
    report["stability_report"]["plateau"]["trial_indices"] = []
    report["stability_report"]["active_dimensions"] = ["mask_dilation_px"]
    report["stability_report"]["continuity"].pop("metric_finite_frame_count")
    report["stability_report"]["trials"] = [
        {
            "index": 9,
            "frame_values": {"orientation_axis_deg": [1.0, 2.0, 3.0, 4.0, 5.0]},
            "reason_codes": [],
        }
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["orientation_status"] == "unavailable"
    assert view.metric_rows["orientation_coverage"] == {}


def test_invalid_trial_indices_never_select_orientation_evidence() -> None:
    report = saxs_stability_report()
    report["stability_report"]["plateau"]["trial_indices"] = [
        -1,
        float("nan"),
        float("inf"),
        "bad",
        [],
    ]
    report["stability_report"]["active_dimensions"] = ["mask_dilation_px"]
    report["stability_report"]["continuity"].pop("metric_finite_frame_count")
    report["stability_report"]["trials"] = [
        {
            "index": -1,
            "frame_values": {"orientation_axis_deg": [1.0, 2.0, 3.0, 4.0, 5.0]},
            "reason_codes": [],
        }
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["platform_points"] == 0
    assert view.metric_rows["orientation_status"] == "unavailable"
    assert view.metric_rows["orientation_coverage"] == {}


def test_missing_or_invalid_plateau_never_selects_trial_orientation() -> None:
    for plateau in (None, [], {}, {"connected": False}):
        report = saxs_stability_report()
        report["stability_report"]["plateau"] = plateau
        report["stability_report"]["active_dimensions"] = ["mask_dilation_px"]
        report["stability_report"]["continuity"].pop("metric_finite_frame_count")
        report["stability_report"]["trials"] = [
            {
                "index": 0,
                "frame_values": {
                    "orientation_axis_deg": [1.0, 2.0, 3.0, 4.0, 5.0]
                },
                "reason_codes": [],
            }
        ]

        view = build_preprocess_ui_decision(report)

        assert view.metric_rows["platform_points"] == 0
        assert view.metric_rows["orientation_status"] == "unavailable"
        assert view.metric_rows["orientation_coverage"] == {}


def test_extreme_integer_evidence_fails_closed_to_zero() -> None:
    huge = 10**400
    report = saxs_stability_report()
    report["stability_report"]["plateau"].update(
        {"point_count": huge, "trial_indices": [huge]}
    )
    report["stability_report"]["continuity"].update(
        {
            "frame_count": huge,
            "metric_finite_frame_count": {"orientation_axis_deg": huge},
        }
    )
    report["stability_report"]["trials"] = [
        {
            "index": huge,
            "frame_values": {"orientation_axis_deg": [huge]},
            "reason_codes": [],
        }
    ]

    view = build_preprocess_ui_decision(report)

    assert view.metric_rows["platform_points"] == 0
    assert view.metric_rows["continuity_frame_count"] == 0
    assert view.metric_rows["orientation_coverage"]["orientation_axis_deg"] == {
        "finite_frames": 0,
        "frame_count": 0,
        "fraction": 0.0,
    }


def test_canonical_interval_key_never_falls_back_when_payload_is_invalid() -> None:
    for canonical in (None, ["bad"], "bad"):
        report = saxs_stability_report()
        report["stability_report"]["perturbation_intervals"] = canonical
        report["stability_report"]["bootstrap"] = {
            "stale": {"lower": -1.0, "median": -0.8, "upper": -0.5}
        }

        view = build_preprocess_ui_decision(report)

        assert view.metric_rows["perturbation_intervals"] == {}


def test_reason_and_dimension_lists_ignore_objects_without_stringifying() -> None:
    class Unprintable:
        calls = 0

        def __str__(self):
            type(self).calls += 1
            raise RuntimeError("no string")

        def __repr__(self):
            type(self).calls += 1
            raise RuntimeError("no repr")

    report = saxs_stability_report()
    report["preprocess_decision"]["reason_codes"] = [
        Unprintable(),
        " valid_reason ",
        "",
    ]
    report["stability_report"]["reason_codes"] = [Unprintable()]
    report["stability_report"]["active_dimensions"] = [
        " q_min ",
        Unprintable(),
        "",
    ]

    view = build_preprocess_ui_decision(report)

    assert Unprintable.calls == 0
    assert view.reason_codes == ("valid_reason",)
    assert view.metric_rows["active_dimensions"] == ["q_min"]


@pytest.mark.parametrize(
    "field",
    (
        "decision",
        "simulated_decision",
        "confidence_band",
        "continuity_status",
        "stability_decision",
        "mode",
        "candidate_id",
    ),
)
def test_contract_strings_ignore_objects_without_stringifying(field: str) -> None:
    class Unprintable:
        calls = 0

        def __str__(self):
            type(self).calls += 1
            raise RuntimeError("no string")

        def __repr__(self):
            type(self).calls += 1
            raise RuntimeError("no repr")

    value = Unprintable()
    if field == "candidate_id":
        report = report_with("keep_original", "low")
        report["selected_candidate_id"] = value
        report["preprocess_evidence"][0]["candidate_id"] = value
    else:
        report = saxs_stability_report()
        if field == "decision":
            report["preprocess_decision"]["decision"] = value
            report["preprocess_decision"].pop("simulated_decision")
        elif field == "simulated_decision":
            report["preprocess_decision"]["decision"] = "keep_original"
            report["preprocess_decision"]["simulated_decision"] = value
        elif field == "confidence_band":
            report["preprocess_decision"]["confidence_band"] = value
        elif field == "continuity_status":
            report["stability_report"]["continuity"]["status"] = value
        elif field == "stability_decision":
            report["stability_report"]["decision"] = value
        elif field == "mode":
            report["mode"] = value
            report["stability_report"]["mode"] = value

    view = build_preprocess_ui_decision(report)

    assert Unprintable.calls == 0
    if field in {"decision", "simulated_decision"}:
        assert view.mode == "keep_original"
    elif field == "confidence_band":
        assert "confidence: low" in view.summary
    elif field == "continuity_status":
        assert view.metric_rows["continuity_status"] == "passed"
    elif field == "stability_decision":
        assert view.metric_rows["stability_decision"] == "keep_original"
        assert view.apply_enabled is False
    elif field == "mode":
        assert view.apply_enabled is False
    else:
        assert view.metric_rows["weak_peak_retention"] == 1.0
