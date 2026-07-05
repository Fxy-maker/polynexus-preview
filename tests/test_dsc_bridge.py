from __future__ import annotations

from pathlib import Path

from polynexus.config_bridge import DSC_PARAM_MAP, apply_changes
from polynexus.core.dsc_engine.config import DSCConfig
from polynexus.core.dsc_action_registry import actions_for_symptoms, allowed_changes_for_actions
from polynexus.orchestrator import ParameterOrchestrator


def test_dsc_param_map_and_apply_changes_update_config() -> None:
    config = DSCConfig(
        exo_up=True,
        baseline_corr="auto",
        Tg_search_low_C=20.0,
        Tg_search_high_C=120.0,
    )

    ok, error = apply_changes(
        config,
        {
            "exo_up": False,
            "baseline_type": "spline",
            "tg_search_low_C": 30.0,
            "tg_search_high_C": 140.0,
        },
        technique="dsc",
    )

    assert ok is True
    assert error == ""
    assert config.exo_up is False
    assert config.baseline_corr == "spline"
    assert config.Tg_search_low_C == 30.0
    assert config.Tg_search_high_C == 140.0
    assert {"exo_up", "baseline_type", "tg_search_low_C", "tg_search_high_C"} <= set(DSC_PARAM_MAP)


def test_dsc_action_registry_maps_symptoms_to_controlled_actions() -> None:
    actions = actions_for_symptoms(
        [
            {"name": "baseline_sensitive_result"},
            {"name": "Tg_without_DCp_step"},
            {"name": "event_polarity_conflict"},
            {"name": "melting_peak_shift"},
            {"name": "cold_crystallization_overlap"},
        ],
        technique="DSC",
    )

    names = [item["name"] for item in actions]
    assert "stabilize_baseline" in names
    assert "restore_tg_support" in names
    assert "align_polarity" in names
    assert "tighten_melting_window" in names
    assert "separate_cold_crystallization" in names

    allowed = allowed_changes_for_actions(actions, technique="DSC")
    assert "baseline_type" in allowed
    assert "smooth_window" in allowed
    assert "exo_up" in allowed
    assert "tg_search_low_C" in allowed
    assert "tg_search_high_C" in allowed
    assert "tm_search_low_C" in allowed
    assert "tm_search_high_C" in allowed


def test_dsc_orchestrator_maps_symptoms_to_actions() -> None:
    orchestrator = ParameterOrchestrator(
        technique="dsc",
        data_file="dummy.dsc",
        polymer_name="PA6",
        project_root=Path("."),
    )

    symptoms = [
        {"name": "baseline_sensitive_result"},
        {"name": "Tg_without_DCp_step"},
        {"name": "event_polarity_conflict"},
        {"name": "melting_peak_shift"},
        {"name": "cold_crystallization_overlap"},
    ]
    actions = orchestrator._allowed_actions(symptoms)
    allowed_changes = orchestrator._allowed_changes(actions)

    names = [item["name"] for item in actions]
    assert "stabilize_baseline" in names
    assert "restore_tg_support" in names
    assert "align_polarity" in names
    assert "tighten_melting_window" in names
    assert "separate_cold_crystallization" in names
    assert "exo_up" in allowed_changes
    assert "tg_search_low_C" in allowed_changes
    assert "tg_search_high_C" in allowed_changes
    assert "tm_search_low_C" in allowed_changes
    assert "tm_search_high_C" in allowed_changes


def test_dsc_orchestrator_builds_executable_candidate_plans() -> None:
    orchestrator = ParameterOrchestrator(
        technique="dsc",
        data_file="dummy.dsc",
        polymer_name="PA6",
        project_root=Path("."),
    )

    advice = {
        "target_symptom": "baseline_sensitive_result",
        "recommended_actions": [
            {"name": "stabilize_baseline", "reason": "baseline drift remains visible"},
            {"name": "align_polarity", "reason": "sign convention is uncertain"},
        ],
        "changes": {},
    }
    state = {
        "current_config": {
            "baseline_corr": "auto",
            "exo_up": True,
            "smooth_window": 11,
            "Tg_search_low_C": 20.0,
            "Tg_search_high_C": 120.0,
            "Tm_search_low_C": 100.0,
            "Tm_search_high_C": 300.0,
            "Tc_search_low_C": 50.0,
            "Tc_search_high_C": 250.0,
            "peak_prominence_ratio": 0.03,
            "min_event_enthalpy_Jg": 0.05,
            "max_melting_peak_width_C": 50.0,
        },
        "allowed_actions": actions_for_symptoms(
            [{"name": "baseline_sensitive_result"}, {"name": "event_polarity_conflict"}],
            technique="DSC",
        ),
        "allowed_changes": allowed_changes_for_actions(
            actions_for_symptoms(
                [{"name": "baseline_sensitive_result"}, {"name": "event_polarity_conflict"}],
                technique="DSC",
            ),
            technique="DSC",
        ),
        "symptom_names": ["baseline_sensitive_result", "event_polarity_conflict"],
    }

    plans = orchestrator._expand_technique_candidates(advice, state)
    executable = [plan for plan in plans if plan.get("executable")]
    names = [plan["action_name"] for plan in plans]

    assert "stabilize_baseline" in names
    assert "align_polarity" in names
    assert executable
    assert any("baseline_type" in plan.get("changes", {}) for plan in executable)
    assert any("exo_up" in plan.get("changes", {}) for plan in executable)
