from __future__ import annotations

from pathlib import Path

from polynexus.core.saxs_action_registry import actions_for_symptoms, allowed_changes_for_actions
from polynexus.core.waxs_temperature_action_registry import (
    actions_for_symptoms as waxs_temperature_actions_for_symptoms,
    allowed_changes_for_actions as waxs_temperature_allowed_changes_for_actions,
)
from polynexus.orchestrator import ParameterOrchestrator


def test_saxs_action_registry_matches_condition_recovery_actions() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "condition_axis_missing"},
            {"name": "condition_axis_unstable"},
        ]
    )

    names = {item["name"] for item in actions}
    assert "rerun_condition_recovery" in names
    assert "adjust_q_crop" in names


def test_saxs_action_registry_matches_strain_axis_recovery_actions() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "strain_axis_low_confidence"},
            {"name": "low_q_void_dominant"},
        ]
    )

    names = {item["name"] for item in actions}
    assert "rerun_condition_recovery" in names
    assert "adjust_q_crop" in names


def test_saxs_action_registry_exposes_allowed_changes_for_peak_actions() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "peak_window_mismatch"},
            {"name": "multi_method_disagreement"},
        ]
    )

    allowed = allowed_changes_for_actions(actions)

    assert "q_bragg_min" in allowed
    assert "q_bragg_max" in allowed
    assert "q_corr_min" in allowed
    assert "lorentz_fit_method" in allowed or "savgol_window" in allowed


def test_saxs_action_registry_routes_temperature_fallback_symptoms() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "temperature_calibration_fallback_active"},
            {"name": "batch_summary_conflicts_with_frame_evidence"},
            {"name": "thickness_chain_unreliable"},
        ]
    )

    names = {item["name"] for item in actions}
    assert "rerun_condition_recovery" in names
    assert "adjust_q_crop" in names
    assert "adjust_corr_window" in names
    ordered = [item["name"] for item in actions]
    assert ordered.index("adjust_q_crop") < ordered.index("switch_lorentz_method") if "switch_lorentz_method" in ordered else True


def test_saxs_action_registry_routes_strain_void_conflicts() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "low_q_void_dominant"},
            {"name": "strain_void_lamellar_conflict"},
            {"name": "qstar_rel_without_lamellar_support"},
        ]
    )

    names = {item["name"] for item in actions}
    assert "adjust_q_crop" in names
    assert "adjust_corr_window" in names

    allowed = allowed_changes_for_actions(actions)
    assert "q_bragg_min" in allowed
    assert "q_corr_min" in allowed


def test_waxs_action_registry_routes_waxs_symptoms() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "peak_position_bias"},
            {"name": "peak_count_insufficient"},
            {"name": "offset_sensitive_solution"},
        ],
        technique="WAXS",
    )

    names = {item["name"] for item in actions}
    assert "adjust_peak_position" in names
    assert "increase_peak_capacity" in names

    allowed = allowed_changes_for_actions(actions, technique="WAXS")
    assert "two_theta_offset" in allowed
    assert "max_peaks" in allowed or "peak_distance" in allowed


def test_waxs_temperature_action_registry_routes_sequence_symptoms() -> None:
    actions = waxs_temperature_actions_for_symptoms(
        [
            {"name": "temperature_axis_missing"},
            {"name": "peak_family_track_fragmented"},
            {"name": "scherrer_dominated_by_peak_width_noise"},
        ],
        technique="WAXS.TEMPERATURE",
    )

    names = {item["name"] for item in actions}
    assert "recover_temperature_axis" in names
    assert "stabilize_peak_family_tracking" in names
    assert "stabilize_temperature_peak_shape" in names

    allowed = waxs_temperature_allowed_changes_for_actions(actions, technique="WAXS.TEMPERATURE")
    assert set(allowed) == {"peak_distance", "peak_function", "smooth_window"}


def test_waxs_temperature_orchestrator_uses_temperature_action_registry() -> None:
    orchestrator = ParameterOrchestrator(
        technique="waxs",
        data_file=str(Path("测试数据") / "waxs" / "原位变温广角" / "PA6-250-170-W_0_00002.edf"),
        polymer_name="PA6",
        project_root=Path("."),
    )

    actions = orchestrator._allowed_actions(
        [
            {"name": "temperature_axis_missing"},
            {"name": "peak_family_track_fragmented"},
            {"name": "scherrer_unphysical_temperature_trend"},
        ]
    )

    names = {item["name"] for item in actions}
    assert "recover_temperature_axis" in names
    assert "stabilize_peak_family_tracking" in names
    assert "stabilize_temperature_peak_shape" in names
