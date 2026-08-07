from __future__ import annotations

import pytest


def _run_mode_stability_bridge(monkeypatch, *, experiment_type: str, submodule: str | None):
    from types import SimpleNamespace

    import polynexus.orchestrator_preprocess as preprocess_module
    import polynexus.orchestrator_stability as stability_module

    observed_modes: list[str] = []

    monkeypatch.setattr(
        stability_module,
        "assess_saxs_confirmed_rerun",
        lambda _engine, *, mode: observed_modes.append(mode)
        or {
            "physical_gate_status": "passed",
            "quality_gate_status": "passed",
            "reason_codes": [],
        },
    )
    monkeypatch.setattr(
        preprocess_module,
        "_new_trial_engine",
        lambda _self, _engine, trial_config: SimpleNamespace(cfg=trial_config),
    )
    monkeypatch.setattr(
        preprocess_module,
        "_run_trial_pipeline",
        lambda _self, _engine: (True, ""),
    )

    class Harness:
        technique = "saxs"
        workspace_context = {"stability_mode": "quick"}
        submodule_override = submodule
        _last_stability_report: dict[str, object] = {}

        @staticmethod
        def _engine_config(engine):
            return engine.cfg

        @staticmethod
        def _config_to_dict(config):
            return dict(vars(config))

        @staticmethod
        def _output_parameters(_engine):
            return {"L_nm": 10.0}

        @staticmethod
        def _residual_pattern(_engine):
            return {}

        @staticmethod
        def _analysis_evidence(_output, _residuals):
            return {}

        @staticmethod
        def _score_snapshot(_output, _residuals, _evidence):
            return {"objective_score": 1.0}

        def _public_submodule(self):
            return self.submodule_override or "saxs.static"

    harness = Harness()
    report = stability_module._run_saxs_stability_study(
        harness,
        SimpleNamespace(
            cfg=SimpleNamespace(
                experiment_type=experiment_type,
                q_min=0.1,
                q_max=3.0,
            )
        ),
    )
    return report, observed_modes

def test_stability_study_is_deterministic_and_reuses_cached_trials() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    calls: list[dict[str, float]] = []

    def evaluate(config: dict[str, float]) -> dict[str, object]:
        calls.append(dict(config))
        distance = abs(config["q_min"] - 0.12) + abs(config["q_max"] - 1.6)
        return {
            "score": 1.0 - distance,
            "physical_passed": distance < 0.2,
            "quality_passed": distance < 0.2,
            "metrics": {"L_nm": 10.0 + config["q_min"]},
            "frame_values": {"L_nm": [10.0, 10.02, 9.98]},
        }

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1, "q_max": 1.5},
        domains=(
            ParameterDomain("q_min", 0.08, 0.16),
            ParameterDomain("q_max", 1.4, 1.8),
        ),
        seed=7,
        global_trials=8,
        active_trials=4,
        confirmation_trials=4,
        min_plateau_points=2,
        decision_mode="strict",
    )

    first = run_stability_study(request, evaluate)
    first_call_count = len(calls)
    second = run_stability_study(request, evaluate)

    assert first.to_dict() == second.to_dict()
    assert len(calls) == first_call_count * 2
    assert first.trial_count <= request.max_trials
    assert first.plateau.parameter_bounds["q_min"][0] <= first.plateau.parameter_bounds["q_min"][1]
    assert first.bootstrap["score"].lower <= first.bootstrap["score"].upper


def test_stability_study_requires_connected_multi_dimension_platform_for_auto_accept() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    def evaluate(config: dict[str, float]) -> dict[str, object]:
        distance = abs(config["q_min"] - 0.12) + abs(config["q_max"] - 1.6)
        return {
            "score": 0.95 - distance,
            "physical_passed": distance < 0.06,
            "quality_passed": distance < 0.06,
            "metrics": {"Q_star": 2.0},
            "frame_values": {"Q_star": [2.0, 2.01, 1.99]},
        }

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.12, "q_max": 1.6},
        domains=(ParameterDomain("q_min", 0.1, 0.14), ParameterDomain("q_max", 1.5, 1.7)),
        seed=3,
        global_trials=12,
        active_trials=8,
        confirmation_trials=9,
        min_plateau_points=3,
        decision_mode="strict",
    )

    report = run_stability_study(request, evaluate)

    assert report.decision in {"auto_accept", "request_confirmation"}
    assert report.plateau.connected is True
    assert report.continuity.passed is True
    assert report.physics_gate_passed is True
    assert report.quality_gate_passed is True


def test_stability_study_preserves_tuple_categorical_candidates() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    request = StabilityStudyRequest(
        baseline_config={"orientation_mask_dilation_px": (1,)},
        domains=(
            ParameterDomain(
                "orientation_mask_dilation_px",
                values=((1,), (2,)),
            ),
        ),
        global_trials=3,
        active_trials=0,
        confirmation_trials=0,
        min_plateau_points=1,
        min_plateau_fraction=0.25,
        acceptance_score=0.5,
        bootstrap_replicates=16,
    )

    report = run_stability_study(
        request,
        lambda config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 10.0]},
        },
    )

    assert report.trials
    assert all(
        isinstance(trial.config["orientation_mask_dilation_px"], tuple)
        for trial in report.trials
    )


def test_saxs_stability_policy_requires_confirmation_even_at_auto_accept_score() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1},
        domains=(ParameterDomain("q_min", 0.09, 0.11),),
        global_trials=3,
        active_trials=0,
        confirmation_trials=0,
        min_plateau_points=2,
        allow_auto_accept=False,
    )
    report = run_stability_study(
        request,
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 10.0]},
        },
    )

    assert report.decision == "request_confirmation"


def test_stability_study_keeps_original_when_physics_or_continuity_fails() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    def evaluate(_config: dict[str, float]) -> dict[str, object]:
        return {
            "score": 0.99,
            "physical_passed": False,
            "quality_passed": True,
            "metrics": {"L_nm": 10.0},
            "frame_values": {"L_nm": [10.0, 13.0, 7.0]},
        }

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1},
        domains=(ParameterDomain("q_min", 0.08, 0.12),),
        seed=1,
        global_trials=4,
        active_trials=2,
        confirmation_trials=2,
        min_plateau_points=2,
    )

    report = run_stability_study(request, evaluate)

    assert report.decision == "keep_original"
    assert report.physics_gate_passed is False
    assert report.continuity.passed is False
    assert "physical_gate_failed" in report.reason_codes


def test_stability_continuity_does_not_compare_independent_trial_boundaries() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    def evaluate(config: dict[str, float]) -> dict[str, object]:
        level = 10.0 if config["q_min"] < 0.1 else 100.0
        return {
            "score": 0.95,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [level, level]},
        }

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.05, 0.15),),
            seed=4,
            global_trials=3,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=2,
        ),
        evaluate,
    )

    assert report.continuity.passed is True


def test_stability_report_uses_existing_confirmation_contract_without_mutation() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {}
    stability = {
        "decision": "request_confirmation",
        "baseline_config": {"q_min": 0.10, "q_max": 1.5},
        "selected_config": {"q_min": 0.12, "q_max": 1.5},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": [],
    }

    _attach_stability_confirmation_contract(report, stability)

    assert report["preprocess_decision"]["decision"] == "request_confirmation"
    assert report["selected_preprocess_config"] == {"q_min": 0.12}
    assert report["original_preprocess_config"] == {"q_min": 0.10}
    assert report["preprocess_candidates"][0]["config_delta"] == {"q_min": 0.12}


def test_keep_original_stability_diagnostic_never_exposes_confirmation_authority() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {}
    stability = {
        "mode": "strain",
        "decision": "keep_original",
        "complete": True,
        "baseline_config": {"q_min": 0.10},
        "selected_config": {"q_min": 0.12},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": ["stable_plateau_insufficient"],
    }

    _attach_stability_confirmation_contract(report, stability)

    assert report["selected_preprocess_config"] == {}
    assert report["original_preprocess_config"] == {}
    assert report["preprocess_candidates"] == []
    assert report["selected_candidate_id"] == ""
    assert report["preprocess_decision"]["decision"] == "keep_original"


def test_empty_or_unchanged_stability_selection_never_exposes_confirmation_authority() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    for selected in ({}, {"q_min": 0.10}):
        report: dict[str, object] = {}
        stability = {
            "mode": "static",
            "decision": "request_confirmation",
            "complete": True,
            "baseline_config": {"q_min": 0.10},
            "selected_config": selected,
            "plateau": {"connected": True},
            "continuity": {"passed": True},
            "physics_gate_passed": True,
            "quality_gate_passed": True,
            "reason_codes": [],
        }

        _attach_stability_confirmation_contract(report, stability)

        assert report["selected_preprocess_config"] == {}
        assert report["original_preprocess_config"] == {}
        assert report["preprocess_candidates"] == []
        assert report["selected_candidate_id"] == ""
        assert report["preprocess_decision"]["decision"] == "keep_original"


def test_stability_confirmation_projects_report_mode_without_static_fallback() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {"submodule": "saxs.strain"}
    stability = {
        "mode": "strain",
        "decision": "request_confirmation",
        "complete": True,
        "baseline_config": {"q_min": 0.10},
        "selected_config": {"q_min": 0.12},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": [],
    }

    _attach_stability_confirmation_contract(report, stability)

    assert report["mode"] == "strain"


def test_stability_confirmation_accepts_explicit_compatible_mode() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {"submodule": "saxs.temperature"}
    stability = {
        "decision": "request_confirmation",
        "baseline_config": {"q_min": 0.10},
        "selected_config": {"q_min": 0.12},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": [],
    }

    _attach_stability_confirmation_contract(report, stability, mode="temperature")

    assert report["mode"] == "temperature"


def test_stability_confirmation_normalizes_stability_report_alias() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {}
    stability = {
        "mode": "heating",
        "decision": "request_confirmation",
        "complete": True,
        "baseline_config": {"q_min": 0.10},
        "selected_config": {"q_min": 0.12},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": [],
    }

    _attach_stability_confirmation_contract(report, stability)

    assert report["mode"] == "temperature"
    assert report["selected_preprocess_config"] == {"q_min": 0.12}


def test_stability_confirmation_normalizes_explicit_qualified_alias() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {}
    stability = {
        "decision": "request_confirmation",
        "complete": True,
        "baseline_config": {"q_min": 0.10},
        "selected_config": {"q_min": 0.12},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": [],
    }

    _attach_stability_confirmation_contract(report, stability, mode="saxs.heating")

    assert report["mode"] == "temperature"
    assert report["selected_preprocess_config"] == {"q_min": 0.12}


def test_stability_confirmation_normalizes_existing_report_mode_case() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {"mode": "SAXS.TEMPERATURE"}
    stability = {
        "decision": "request_confirmation",
        "complete": True,
        "baseline_config": {"q_min": 0.10},
        "selected_config": {"q_min": 0.12},
        "plateau": {"connected": True},
        "continuity": {"passed": True},
        "physics_gate_passed": True,
        "quality_gate_passed": True,
        "reason_codes": [],
    }

    _attach_stability_confirmation_contract(report, stability)

    assert report["mode"] == "temperature"
    assert report["selected_preprocess_config"] == {"q_min": 0.12}


def test_stability_confirmation_keeps_unsupported_mode_non_applicable() -> None:
    from polynexus.orchestrator_session import _attach_stability_confirmation_contract

    report: dict[str, object] = {"submodule": "saxs.dynamic"}
    stability = {
        "mode": None,
        "decision": "keep_original",
        "complete": False,
        "baseline_config": {"q_min": 0.10},
        "selected_config": {},
        "plateau": {"connected": False},
        "continuity": {"passed": False},
        "physics_gate_passed": False,
        "quality_gate_passed": False,
        "reason_codes": ["unsupported_saxs_stability_mode"],
    }

    _attach_stability_confirmation_contract(report, stability)

    assert report["mode"] is None
    assert report["selected_preprocess_config"] == {}
    assert report["preprocess_candidates"] == []
    assert report["preprocess_decision"]["decision"] == "keep_original"


def test_stability_report_contract_serializes_optional_mode() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ContinuityEvidence,
        PlateauSummary,
        StabilityReport,
    )

    report = StabilityReport(
        schema_version="saxs-stability-v1",
        decision="keep_original",
        complete=False,
        baseline_config={},
        selected_config={},
        trials=(),
        plateau=PlateauSummary(connected=False),
        bootstrap={},
        continuity=ContinuityEvidence(passed=False),
        physics_gate_passed=False,
        quality_gate_passed=False,
        mode="temperature",
        active_dimensions=("q_min", "q_max"),
        excluded_dimensions={"bg_scale_value": "manual_background_inactive"},
    )

    payload = report.to_dict()
    assert payload["mode"] == "temperature"
    assert payload["active_dimensions"] == ["q_min", "q_max"]
    assert payload["excluded_dimensions"] == {
        "bg_scale_value": "manual_background_inactive"
    }


def test_stability_bridge_uses_active_mode_for_every_trial(monkeypatch) -> None:
    cases = (
        ("static", "saxs.static", "static"),
        ("strain", "saxs.strain", "strain"),
        ("temperature", "saxs.temperature", "temperature"),
        ("heating", "saxs.temperature", "temperature"),
        ("cooling", "saxs.temperature", "temperature"),
        ("isothermal", "saxs.temperature", "temperature"),
    )
    for experiment_type, submodule, expected in cases:
        report, observed_modes = _run_mode_stability_bridge(
            monkeypatch,
            experiment_type=experiment_type,
            submodule=submodule,
        )
        assert observed_modes
        assert observed_modes == [expected] * len(observed_modes)
        assert report["mode"] == expected
        assert report["decision"] != "auto_accept"


def test_stability_bridge_fails_closed_for_unsupported_mode(monkeypatch) -> None:
    report, observed_modes = _run_mode_stability_bridge(
        monkeypatch,
        experiment_type="dynamic",
        submodule="saxs.dynamic",
    )

    assert observed_modes == []
    assert report["mode"] is None
    assert report["complete"] is False
    assert report["decision"] == "keep_original"
    assert report["selected_config"] == {}
    assert isinstance(report["active_dimensions"], list)
    assert isinstance(report["excluded_dimensions"], dict)
    assert "unsupported_saxs_stability_mode" in report["reason_codes"]


def test_stability_bridge_fails_closed_for_conflicting_modes(monkeypatch) -> None:
    report, observed_modes = _run_mode_stability_bridge(
        monkeypatch,
        experiment_type="strain",
        submodule="saxs.temperature",
    )

    assert observed_modes == []
    assert report["mode"] is None
    assert report["complete"] is False
    assert report["decision"] == "keep_original"
    assert report["selected_config"] == {}
    assert "conflicting_saxs_stability_mode" in report["reason_codes"]


def _activity_domain_config(**overrides):
    config = {
        "q_min": 0.1,
        "q_max": 2.0,
        "q_corr_min": 0.05,
        "q_corr_max": 2.0,
        "q_porod_min": 1.0,
        "q_porod_max": 2.0,
        "do_porod": True,
        "guinier_q_max_factor": 1.3,
        "background_file": "",
        "bg_scale_method": "transmission",
        "bg_scale_value": 1.0,
        "beam_center_offset_x_px": 0.5,
        "beam_center_offset_y_px": -0.5,
        "chi_halfwidth": 15.0,
        "chi_halfwidth_authoritative": False,
        "is_isotropic": False,
        "mask_dilation_px": 0,
        "orientation_mask_dilation_px": (1, 2),
    }
    config.update(overrides)
    return config


def test_saxs_stability_domains_include_only_active_2d_perturbations() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(),
        mode="strain",
        engine=SimpleNamespace(
            _img=[[1.0, 2.0], [3.0, 4.0]],
            _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
        ),
    )

    by_name = {domain.name: domain for domain in result}
    assert "guinier_q_max_factor" in by_name
    assert "bg_scale_value" not in by_name
    assert by_name["beam_center_offset_x_px"].minimum == -1.5
    assert by_name["beam_center_offset_x_px"].maximum == 2.5
    assert by_name["beam_center_offset_y_px"].minimum == -2.5
    assert by_name["beam_center_offset_y_px"].maximum == 1.5
    assert by_name["mask_dilation_px"].values == (0, 1)
    assert "orientation_mask_dilation_px" not in by_name
    assert result.excluded_dimensions["orientation_mask_dilation_px"] == (
        "reliability_sensitivity_only"
    )
    assert result.excluded_dimensions["bg_scale_value"] == (
        "manual_background_inactive"
    )


@pytest.mark.parametrize(
    ("current", "expected"),
    [(10, (9, 10, 11)), (50, (49, 50, 51)), (100, (99, 100))],
)
def test_mask_dilation_domain_is_local_bounded_and_includes_current(
    current, expected
) -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(mask_dilation_px=current),
        mode="strain",
        engine=SimpleNamespace(
            _img=[[1.0, 2.0], [3.0, 4.0]],
            _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
        ),
    )

    by_name = {domain.name: domain for domain in result}
    assert by_name["mask_dilation_px"].values == expected


def test_mask_dilation_domain_rejects_value_above_gui_limit() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(mask_dilation_px=101),
        mode="strain",
        engine=SimpleNamespace(
            _img=[[1.0, 2.0], [3.0, 4.0]],
            _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
        ),
    )

    assert "mask_dilation_px" not in {domain.name for domain in result}
    assert result.excluded_dimensions["mask_dilation_px"] == "consumer_config_invalid"


def test_isotropic_config_excludes_chi_halfwidth_even_with_raw_detector() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(is_isotropic=True),
        mode="static",
        engine=SimpleNamespace(
            _img=[[1.0, 2.0], [3.0, 4.0]],
            _sector_data_list=[],
        ),
    )

    assert "chi_halfwidth" not in {domain.name for domain in result}
    assert result.excluded_dimensions["chi_halfwidth"] == "sector_integration_inactive"


def test_changed_chi_candidate_executes_and_reports_explicit_authority(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    import polynexus.orchestrator_preprocess as preprocess_module
    import polynexus.orchestrator_stability as stability_module
    from polynexus.core.preprocess_optimization.stability import (
        ContinuityEvidence,
        PlateauSummary,
        StabilityReport,
        StabilityTrial,
    )

    executed_configs = []

    def create_trial(_self, _engine, trial_config):
        executed_configs.append(trial_config)
        return SimpleNamespace(cfg=trial_config)

    monkeypatch.setattr(preprocess_module, "_new_trial_engine", create_trial)
    monkeypatch.setattr(
        preprocess_module,
        "_run_trial_pipeline",
        lambda _self, _engine: (True, ""),
    )
    monkeypatch.setattr(
        stability_module,
        "assess_saxs_confirmed_rerun",
        lambda _engine, *, mode: {
            "physical_gate_status": "passed",
            "quality_gate_status": "passed",
            "reason_codes": [],
        },
    )

    def run_one_candidate(request, evaluator):
        candidate = dict(request.baseline_config)
        candidate["chi_halfwidth"] = 21.0
        result = evaluator(candidate)
        trial = StabilityTrial(
            index=0,
            config=candidate,
            score=float(result["score"]),
            physical_passed=True,
            quality_passed=True,
            continuity_passed=True,
        )
        return StabilityReport(
            schema_version="saxs-stability-v1",
            decision="request_confirmation",
            complete=True,
            baseline_config=dict(request.baseline_config),
            selected_config=candidate,
            trials=(trial,),
            plateau=PlateauSummary(connected=True, trial_indices=(0,)),
            bootstrap={},
            continuity=ContinuityEvidence(passed=True),
            physics_gate_passed=True,
            quality_gate_passed=True,
        )

    monkeypatch.setattr(stability_module, "run_stability_study", run_one_candidate)

    class Harness:
        technique = "saxs"
        workspace_context = {"stability_mode": "quick"}
        submodule_override = "saxs.strain"
        _last_stability_report = {}

        @staticmethod
        def _engine_config(engine):
            return engine.cfg

        @staticmethod
        def _config_to_dict(config):
            return dict(vars(config))

        @staticmethod
        def _output_parameters(_engine):
            return {"L_nm": 10.0}

        @staticmethod
        def _residual_pattern(_engine):
            return {}

        @staticmethod
        def _analysis_evidence(_output, _residuals):
            return {}

        @staticmethod
        def _score_snapshot(_output, _residuals, _evidence):
            return {"objective_score": 1.0}

    config = SimpleNamespace(
        experiment_type="strain",
        chi_merid_range=(62.0, 118.0),
        chi_equat_range=(-8.0, 12.0),
        **_activity_domain_config(),
    )
    engine = SimpleNamespace(
        cfg=config,
        _img=[[1.0, 2.0], [3.0, 4.0]],
        _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
    )

    report = stability_module._run_saxs_stability_study(Harness(), engine)

    assert config.chi_halfwidth_authoritative is False
    assert executed_configs
    assert executed_configs[0].chi_halfwidth_authoritative is True
    assert report["selected_config"]["chi_halfwidth_authoritative"] is True
    assert report["trials"][0]["config"]["chi_halfwidth_authoritative"] is True


def test_sector_only_evidence_excludes_beam_offsets_but_keeps_orientation_domains() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(),
        mode="strain",
        engine=SimpleNamespace(
            _img=None,
            _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
        ),
    )

    names = {domain.name for domain in result}
    assert "chi_halfwidth" in names
    assert "mask_dilation_px" not in names
    assert "orientation_mask_dilation_px" not in names
    assert "beam_center_offset_x_px" not in names
    assert "beam_center_offset_y_px" not in names
    assert result.excluded_dimensions["beam_center_offset_x_px"] == (
        "raw_detector_2d_evidence_missing"
    )
    assert result.excluded_dimensions["beam_center_offset_y_px"] == (
        "raw_detector_2d_evidence_missing"
    )
    assert result.excluded_dimensions["mask_dilation_px"] == (
        "raw_detector_2d_evidence_missing"
    )


def test_saxs_stability_domains_include_manual_background_with_real_file() -> None:
    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(
            background_file="C:/data/background.edf",
            bg_scale_method="manual",
        )
    )

    assert "bg_scale_value" in {domain.name for domain in result}


def test_saxs_stability_domains_exclude_detector_dimensions_for_1d_profile() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(),
        mode="static",
        engine=SimpleNamespace(_img=None, _sector_data_list=[]),
    )

    names = {domain.name for domain in result}
    detector_dimensions = {
        "beam_center_offset_x_px",
        "beam_center_offset_y_px",
        "chi_halfwidth",
        "mask_dilation_px",
    }
    assert names.isdisjoint(detector_dimensions)
    assert {
        result.excluded_dimensions[name] for name in detector_dimensions
    } == {"detector_2d_evidence_missing"}
    assert result.excluded_dimensions["orientation_mask_dilation_px"] == (
        "reliability_sensitivity_only"
    )


def test_disabled_porod_consumer_does_not_invalidate_stale_porod_window() -> None:
    from polynexus.orchestrator_stability import _valid_saxs_windows

    config = _activity_domain_config(
        do_porod=False,
        q_porod_min=3.0,
        q_porod_max=1.0,
    )

    assert _valid_saxs_windows(config) is True


def test_nonfinite_manual_background_scale_is_excluded_without_raising() -> None:
    from polynexus.orchestrator_stability import _saxs_stability_domains

    result = _saxs_stability_domains(
        _activity_domain_config(
            background_file="C:/data/background.edf",
            bg_scale_method="manual",
            bg_scale_value=float("inf"),
        )
    )

    assert "bg_scale_value" not in {domain.name for domain in result}
    assert result.excluded_dimensions["bg_scale_value"] == "consumer_config_invalid"


def test_invalid_coupled_q_window_fails_before_trial_engine_creation(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    import polynexus.orchestrator_preprocess as preprocess_module
    import polynexus.orchestrator_stability as stability_module

    created: list[object] = []

    def create_trial(*args):
        created.append(args)
        raise AssertionError("trial engine must not be created")

    monkeypatch.setattr(preprocess_module, "_new_trial_engine", create_trial)

    class Harness:
        technique = "saxs"
        workspace_context = {"stability_mode": "quick"}
        submodule_override = "saxs.strain"
        _last_stability_report: dict[str, object] = {}

        @staticmethod
        def _engine_config(engine):
            return engine.cfg

        @staticmethod
        def _config_to_dict(config):
            return dict(vars(config))

        def _public_submodule(self):
            return self.submodule_override

    config = SimpleNamespace(
        experiment_type="strain",
        **_activity_domain_config(q_min=2.0, q_max=1.0),
    )
    engine = SimpleNamespace(
        cfg=config,
        _img=[[1.0, 2.0], [3.0, 4.0]],
        _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
    )

    report = stability_module._run_saxs_stability_study(Harness(), engine)

    assert created == []
    assert report["trials"]
    assert all(
        "invalid_coupled_q_window" in trial["reason_codes"]
        for trial in report["trials"]
    )
    assert report["decision"] == "keep_original"
    assert report["selected_config"] == {}


def test_guinier_q_max_factor_controls_the_low_q_window() -> None:
    import numpy as np
    from polynexus.core.saxs_engine.saxs_physical_helpers import guinier_analysis

    q = np.linspace(0.01, 1.0, 100)
    intensity = 4.0 * np.exp(-(q**2) * 3.0 / 3.0)
    _, _, default_q, _ = guinier_analysis(q, intensity, q_max_factor=1.3)
    _, _, wider_q, _ = guinier_analysis(q, intensity, q_max_factor=2.0)

    assert len(default_q) == 20
    assert len(wider_q) > len(default_q)
