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
            "frame_values": {"L_nm": [10.0, 10.02, 9.98, 10.01]},
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
            "frame_values": {"Q_star": [2.0, 2.01, 2.02, 2.03]},
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


def test_multi_dimension_plateau_rejects_line_with_insufficient_numeric_spread() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.12, "q_max": 1.6},
        domains=(
            ParameterDomain("q_min", 0.10, 0.14),
            ParameterDomain("q_max", 1.50, 1.70),
        ),
        global_trials=1,
        active_trials=6,
        confirmation_trials=6,
        min_plateau_points=3,
        bootstrap_replicates=16,
        allow_auto_accept=False,
    )

    def evaluate(config: dict[str, float]) -> dict[str, object]:
        eligible = config["q_max"] == request.baseline_config["q_max"]
        return {
            "score": 1.0,
            "physical_passed": eligible,
            "quality_passed": eligible,
            "frame_values": {"L_nm": [10.0, 10.0, 10.0, 10.0]},
        }

    report = run_stability_study(request, evaluate)

    assert report.plateau.connected is False
    assert report.plateau.active_dimensions == ("q_min", "q_max")
    assert report.plateau.spread_dimensions == ("q_min",)
    assert report.plateau.to_dict()["spread_dimensions"] == ["q_min"]
    assert "stable_plateau_dimension_spread_insufficient" in report.reason_codes


def test_categorical_change_does_not_count_as_numeric_plateau_spread() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        StabilityTrial,
        _plateau,
    )

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1, "method": "a"},
        domains=(
            ParameterDomain("q_min", 0.09, 0.11),
            ParameterDomain("method", values=("a", "b")),
        ),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        min_plateau_points=2,
        neighbor_radius=1.0,
        bootstrap_replicates=16,
    )
    trials = tuple(
        StabilityTrial(
            index=index,
            config={"q_min": 0.1, "method": method},
            score=1.0,
            physical_passed=True,
            quality_passed=True,
            continuity_passed=True,
        )
        for index, method in enumerate(("a", "b"))
    )

    plateau = _plateau(trials, request)

    assert plateau.connected is False
    assert plateau.active_dimensions == ("q_min", "method")
    assert plateau.spread_dimensions == ()


def test_categorical_mismatch_cannot_be_diluted_by_ten_dimension_rms() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        StabilityTrial,
        _plateau,
    )

    numeric_domains = tuple(
        ParameterDomain(f"x{index}", 0.0, 1.0) for index in range(9)
    )
    request = StabilityStudyRequest(
        baseline_config={
            **{domain.name: 0.5 for domain in numeric_domains},
            "method": "a",
        },
        domains=(
            *numeric_domains,
            ParameterDomain("method", values=("a", "b")),
        ),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        min_plateau_points=2,
        neighbor_radius=1.0,
        bootstrap_replicates=16,
    )
    first_config = dict(request.baseline_config)
    second_config = {
        **request.baseline_config,
        "x0": 0.51,
        "x1": 0.51,
        "method": "b",
    }
    trials = tuple(
        StabilityTrial(
            index=index,
            config=config,
            score=1.0,
            physical_passed=True,
            quality_passed=True,
            continuity_passed=True,
        )
        for index, config in enumerate((first_config, second_config))
    )

    plateau = _plateau(trials, request)

    assert plateau.connected is False
    assert plateau.trial_indices == (0,)


def test_same_categorical_value_uses_only_numeric_neighbor_dimensions() -> None:
    import math

    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        _normalised_distance,
    )

    numeric_domains = tuple(
        ParameterDomain(f"x{index}", 0.0, 1.0) for index in range(9)
    )
    request = StabilityStudyRequest(
        baseline_config={
            **{domain.name: 0.5 for domain in numeric_domains},
            "method": "a",
        },
        domains=(
            *numeric_domains,
            ParameterDomain("method", values=("a", "b")),
        ),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        bootstrap_replicates=16,
    )
    first = dict(request.baseline_config)
    second = {**first, "x0": 0.6, "x1": 0.7}

    assert _normalised_distance(first, second, request) == pytest.approx(
        math.sqrt((0.1**2 + 0.2**2) / 9.0)
    )


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
            "frame_values": {"L_nm": [10.0, 10.0, 10.0, 10.0]},
        },
    )

    assert report.trials
    assert all(
        isinstance(trial.config["orientation_mask_dilation_px"], tuple)
        for trial in report.trials
    )


def test_parameter_domain_rejects_zero_width_numeric_range() -> None:
    from polynexus.core.preprocess_optimization.stability import ParameterDomain

    with pytest.raises(ValueError, match="minimum.*maximum|exceeds"):
        ParameterDomain("q_min", 0.1, 0.1)


def test_stability_request_requires_baseline_value_for_every_active_domain() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
    )

    with pytest.raises(ValueError, match="baseline_config.*q_max"):
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(
                ParameterDomain("q_min", 0.09, 0.11),
                ParameterDomain("q_max", 1.0, 2.0),
            ),
            bootstrap_replicates=16,
        )


def test_cached_categorical_duplicates_do_not_create_platform_points() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"method": "only"},
            domains=(ParameterDomain("method", values=("only",)),),
            global_trials=5,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=2,
            min_plateau_fraction=0.5,
            bootstrap_replicates=16,
            continuity_required=False,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
        },
    )

    assert report.trial_count == 1
    assert report.plateau.connected is False
    assert report.plateau.coverage_fraction == 1.0


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
            "frame_values": {"L_nm": [10.0, 10.0, 10.0, 10.0]},
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
            "frame_values": {"L_nm": [10.0, 11.0, 30.0, 31.0]},
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
            "frame_values": {"L_nm": [level, level, level, level]},
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


def test_stability_continuity_allows_large_smooth_curved_response() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            min_plateau_fraction=0.5,
            bootstrap_replicates=16,
            allow_auto_accept=False,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 12.0, 15.0, 19.0, 24.0]},
        },
    )

    assert report.decision == "request_confirmation"
    assert report.continuity.passed is True
    assert report.continuity.status == "passed"
    assert report.continuity.metric_median_increment["L_nm"] == 3.5
    assert report.continuity.frame_count == 5
    serialized = report.to_dict()["continuity"]
    assert serialized["passed"] is True
    assert serialized["status"] == "passed"
    assert serialized["metric_median_increment"] == {"L_nm": 3.5}


def test_stability_continuity_rejects_isolated_jump_with_typed_reason() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 11.0, 30.0, 31.0, 32.0]},
        },
    )

    assert report.decision == "keep_original"
    assert all(trial.continuity_passed is False for trial in report.trials)
    assert all(
        "continuity_jump:L_nm" in trial.reason_codes for trial in report.trials
    )
    assert report.continuity.passed is False
    assert report.continuity.status == "failed"
    assert "continuity_jump:L_nm" in report.continuity.reason_codes
    assert report.continuity.frame_count == 5


@pytest.mark.parametrize(
    "sequence",
    (
        [10.0, 11.0, 15.0, 16.0],
        [1.0e9, 1.0e9 + 1.0, 1.0e9 + 1.0e6, 1.0e9 + 1.0e6 + 1.0],
    ),
)
def test_stability_continuity_jump_gate_is_offset_invariant(sequence) -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": sequence},
        },
    )

    assert report.decision == "keep_original"
    assert all(
        "continuity_jump:L_nm" in trial.reason_codes for trial in report.trials
    )


def test_stability_continuity_marks_short_sequence_insufficient() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 10.1, 10.2]},
        },
    )

    assert report.decision == "keep_original"
    assert report.continuity.passed is False
    assert report.continuity.status == "insufficient"
    assert report.continuity.frame_count == 3
    assert "continuity_insufficient:L_nm" in report.continuity.reason_codes
    assert all(
        "continuity_insufficient:L_nm" in trial.reason_codes
        for trial in report.trials
    )


def test_stability_continuity_preserves_nonfinite_frame_alignment() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 11.0, float("nan"), 12.0, 13.0]},
        },
    )

    assert report.continuity.status == "insufficient"
    assert report.continuity.frame_count == 5
    assert all(len(trial.frame_values["L_nm"]) == 5 for trial in report.trials)
    assert all(
        "continuity_nonfinite:L_nm" in trial.reason_codes
        for trial in report.trials
    )


def test_static_stability_continuity_is_not_applicable() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
            allow_auto_accept=False,
            continuity_required=False,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
        },
    )

    assert report.decision == "request_confirmation"
    assert report.continuity.passed is False
    assert report.continuity.status == "not_applicable"
    assert report.continuity.frame_count == 0


def test_frame_values_omits_phantom_metrics_without_finite_observations() -> None:
    from types import SimpleNamespace

    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )
    from polynexus.orchestrator_stability import _frame_values

    points = [
        SimpleNamespace(L_nm=value, invariant_Q=float("nan"), phi_c=None)
        for value in (10.0, 12.0, 15.0, 19.0, 24.0)
    ]
    frame_values = _frame_values(
        SimpleNamespace(
            _temperature_result=SimpleNamespace(temp_points=points),
            _strain_result=None,
        ),
        {},
    )

    assert frame_values == {"L_nm": [10.0, 12.0, 15.0, 19.0, 24.0]}

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
            allow_auto_accept=False,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": frame_values,
        },
    )

    assert report.continuity.status == "passed"
    assert report.decision == "request_confirmation"


def test_frame_values_excludes_scalar_aggregates_from_real_sequence() -> None:
    from types import SimpleNamespace

    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )
    from polynexus.orchestrator_stability import _frame_values, _stability_metrics

    points = [
        SimpleNamespace(L_nm=value, invariant_Q=float("nan"), phi_c=None)
        for value in (10.0, 12.0, 15.0, 19.0, 24.0)
    ]
    output = {
        "L_nm": 16.0,
        "Kp": 3.5,
        "Rg": 2.2,
        "invariant_Q": float("nan"),
        "phi_c": float("inf"),
    }
    frame_values = _frame_values(
        SimpleNamespace(
            _temperature_result=SimpleNamespace(temp_points=points),
            _strain_result=None,
        ),
        output,
    )
    metrics = _stability_metrics(output)

    assert frame_values == {"L_nm": [10.0, 12.0, 15.0, 19.0, 24.0]}
    assert metrics == {"L_nm": 16.0, "Kp": 3.5, "Rg": 2.2}

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
            allow_auto_accept=False,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "metrics": metrics,
            "frame_values": frame_values,
        },
    )

    assert report.continuity.status == "passed"
    assert report.decision == "request_confirmation"


def test_frame_values_transports_strain_orientation_sequences_with_missing_slots() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _frame_values

    points = [
        SimpleNamespace(
            f_herman=effective,
            f_herman_raw=raw,
            orientation_fit_evidence=SimpleNamespace(
                orientation_axis_deg=axis,
                orientation_axis_strength=strength,
                orientation_harmonic_significance=significance,
            ),
        )
        for effective, raw, axis, strength, significance in (
            (0.10, 0.12, 2.0, 0.2, 1.0),
            (0.35, 0.37, 3.0, 0.4, 2.0),
            (0.60, 0.62, 4.0, 0.7, 3.0),
        )
    ]

    values = _frame_values(
        SimpleNamespace(
            _temperature_result=None,
            _strain_result=SimpleNamespace(strain_points=points),
        ),
        {},
    )

    assert values["f_herman"] == [0.10, 0.35, 0.60]
    assert values["f_herman_raw"] == [0.12, 0.37, 0.62]
    assert values["orientation_axis_deg"] == [2.0, 3.0, 4.0]
    assert values["orientation_strength"] == [0.2, 0.4, 0.7]

    missing = SimpleNamespace(
        f_herman=float("nan"),
        f_herman_raw=float("nan"),
        orientation_fit_evidence={
            "orientation_axis_deg": float("nan"),
            "orientation_axis_strength": float("nan"),
        },
    )
    with_gap = _frame_values(
        SimpleNamespace(
            _temperature_result=None,
            _strain_result=SimpleNamespace(
                strain_points=[points[0], missing, *points[1:]],
            ),
        ),
        {},
    )
    assert all(len(sequence) == 4 for sequence in with_gap.values())
    assert all(sequence[1] != sequence[1] for sequence in with_gap.values())


def test_frame_values_keeps_raw_orientation_diagnostic_without_tensile_axis() -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _frame_values

    mapping_evidence = {
        "fit_evidence": {
            "f_herman_raw": 0.42,
            "orientation_axis_deg": 11.0,
            "orientation_axis_strength": 0.3,
        },
        "reason_codes": (
            "legacy_orientation_unavailable",
            "tensile_axis_unknown",
        ),
    }
    object_evidence = SimpleNamespace(
        fit_evidence=SimpleNamespace(
            f_herman_raw=0.52,
        ),
        reason_codes=("tensile_axis_unknown",),
    )
    points = (
        SimpleNamespace(
            f_herman=0.41,
            orientation_evidence=mapping_evidence,
        ),
        SimpleNamespace(
            f_herman=0.51,
            orientation_evidence=object_evidence,
        ),
    )

    values = _frame_values(
        SimpleNamespace(
            _temperature_result=None,
            _strain_result=SimpleNamespace(strain_points=points),
        ),
        {},
    )

    assert "f_herman" not in values
    assert values["f_herman_raw"] == [0.42, 0.52]


def test_saxs_bridge_aggregates_missing_tensile_axis_diagnostic(monkeypatch) -> None:
    from types import SimpleNamespace

    import polynexus.orchestrator_preprocess as preprocess_module
    import polynexus.orchestrator_stability as stability_module

    legacy_reason = "tensile_axis_unknown"
    canonical_reason = "orientation_tensile_axis_missing"
    points = [
        SimpleNamespace(
            L_nm=10.0,
            f_herman=0.4,
            orientation_evidence={
                "fit_evidence": {"f_herman_raw": 0.42},
                "reason_codes": (
                    "legacy_orientation_unavailable",
                    legacy_reason,
                ),
            },
        )
        for _ in range(4)
    ]

    monkeypatch.setattr(
        preprocess_module,
        "_new_trial_engine",
        lambda _self, _engine, trial_config: SimpleNamespace(
            cfg=trial_config,
            _temperature_result=None,
            _strain_result=SimpleNamespace(strain_points=points),
        ),
    )
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
            "reason_codes": "assessment_reason",
        },
    )

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
        **_activity_domain_config(),
    )
    engine = SimpleNamespace(
        cfg=config,
        _img=[[1.0, 2.0], [3.0, 4.0]],
        _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
    )

    report = stability_module._run_saxs_stability_study(Harness(), engine)

    assert report["trials"]
    assert all(
        legacy_reason in trial["reason_codes"]
        and canonical_reason in trial["reason_codes"]
        and "assessment_reason" in trial["reason_codes"]
        for trial in report["trials"]
    )
    assert all("a" not in trial["reason_codes"] for trial in report["trials"])
    assert legacy_reason in report["reason_codes"]
    assert canonical_reason in report["reason_codes"]


@pytest.mark.parametrize(
    ("plateau_indices", "expects_diagnostic"),
    [((0,), False), ((), True)],
)
def test_saxs_bridge_limits_orientation_diagnostics_to_selected_plateau(
    monkeypatch,
    plateau_indices,
    expects_diagnostic,
) -> None:
    from types import SimpleNamespace

    import polynexus.orchestrator_stability as stability_module
    from polynexus.core.preprocess_optimization.stability import (
        ContinuityEvidence,
        PlateauSummary,
        StabilityReport,
        StabilityTrial,
    )

    canonical_reason = "orientation_tensile_axis_missing"
    legacy_reason = "tensile_axis_unknown"
    trials = (
        StabilityTrial(
            index=0,
            config={"q_min": 0.1},
            score=1.0,
            physical_passed=True,
            quality_passed=True,
            continuity_passed=True,
        ),
        StabilityTrial(
            index=1,
            config={"q_min": 0.2},
            score=0.1,
            physical_passed=False,
            quality_passed=False,
            continuity_passed=True,
            reason_codes=(legacy_reason, canonical_reason),
        ),
    )

    monkeypatch.setattr(
        stability_module,
        "run_stability_study",
        lambda _request, _evaluator: StabilityReport(
            schema_version="saxs-stability-v1",
            decision="request_confirmation" if plateau_indices else "keep_original",
            complete=True,
            baseline_config={"q_min": 0.1},
            selected_config={"q_min": 0.1} if plateau_indices else {},
            trials=trials,
            plateau=PlateauSummary(
                connected=bool(plateau_indices),
                trial_indices=plateau_indices,
            ),
            perturbation_intervals={},
            continuity=ContinuityEvidence(passed=True),
            physics_gate_passed=bool(plateau_indices),
            quality_gate_passed=bool(plateau_indices),
            reason_codes=(
                "existing_report_reason",
                legacy_reason,
                canonical_reason,
            ),
        ),
    )

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

    config = SimpleNamespace(
        experiment_type="strain",
        **_activity_domain_config(),
    )
    report = stability_module._run_saxs_stability_study(
        Harness(),
        SimpleNamespace(
            cfg=config,
            _img=[[1.0, 2.0], [3.0, 4.0]],
            _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
        ),
    )

    assert (canonical_reason in report["reason_codes"]) is expects_diagnostic
    assert (legacy_reason in report["reason_codes"]) is expects_diagnostic
    assert "existing_report_reason" in report["reason_codes"]
    assert canonical_reason in report["trials"][1]["reason_codes"]


def test_orientation_axis_continuity_wraps_first_differences_at_180_degrees() -> None:
    from types import SimpleNamespace

    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        StabilityTrial,
        _continuity_for_trials,
    )
    from polynexus.orchestrator_stability import _frame_values

    points = [
        SimpleNamespace(
            f_herman_raw=0.2 + 0.1 * index,
            orientation_fit_evidence={
                "orientation_axis_deg": axis,
                "orientation_axis_strength": 0.5,
            },
        )
        for index, axis in enumerate((179.0, 1.0, 3.0, 5.0, 7.0))
    ]
    values = _frame_values(
        SimpleNamespace(
            _temperature_result=None,
            _strain_result=SimpleNamespace(strain_points=points),
        ),
        {},
    )
    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1},
        domains=(ParameterDomain("q_min", 0.09, 0.11),),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        bootstrap_replicates=16,
    )
    continuity = _continuity_for_trials(
        (
            StabilityTrial(
                index=0,
                config={"q_min": 0.1},
                score=1.0,
                physical_passed=True,
                quality_passed=True,
                continuity_passed=True,
                frame_values={
                    name: tuple(sequence) for name, sequence in values.items()
                },
            ),
        ),
        request,
    )

    assert continuity.status == "passed"
    assert continuity.metric_median_increment["orientation_axis_deg"] == 2.0


def test_normalise_trial_drops_all_nonfinite_metric_sequence() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.09, 0.11),),
            global_trials=1,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=1,
            bootstrap_replicates=16,
            allow_auto_accept=False,
        ),
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {
                "L_nm": [10.0, 12.0, 15.0, 19.0, 24.0],
                "Kp": [float("nan")] * 5,
            },
        },
    )

    assert all("Kp" not in trial.frame_values for trial in report.trials)
    assert report.continuity.status == "passed"
    assert report.decision == "request_confirmation"


@pytest.mark.parametrize(
    ("raw_reasons", "expected"),
    [
        ("whole_reason", ("whole_reason",)),
        (None, ()),
        (["", " first ", None, "first", "second"], ("first", "second")),
    ],
)
def test_normalise_trial_reason_codes_are_atomic_and_deduplicated(
    raw_reasons,
    expected,
) -> None:
    from polynexus.core.preprocess_optimization.stability import _normalise_trial

    trial = _normalise_trial(
        0,
        {"q_min": 0.1},
        {"reason_codes": raw_reasons},
        cached=False,
    )

    assert trial.reason_codes == expected


def test_orientation_frame_summaries_feed_periodic_perturbation_intervals() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        _bootstrap,
        _normalise_trial,
    )

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1},
        domains=(ParameterDomain("q_min", 0.09, 0.11),),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        bootstrap_replicates=32,
        allow_auto_accept=False,
    )

    def orientation_trial(index: int, axis: float):
        return _normalise_trial(
            index,
            {"q_min": 0.09 + 0.02 * index},
            {
                "score": 1.0,
                "physical_passed": True,
                "quality_passed": True,
                "frame_values": {
                    "f_herman": [0.1, float("nan"), 0.3, 0.4],
                    "f_herman_raw": [0.2, 0.3, 0.4, 0.5],
                    "orientation_axis_deg": [axis] * 4,
                    "orientation_strength": [0.2, 0.4, 0.6, 0.8],
                },
            },
            cached=False,
        )

    boundary_trials = (
        orientation_trial(0, 179.0),
        orientation_trial(1, 1.0),
    )

    assert boundary_trials[0].metrics["f_herman"] == pytest.approx(
        (0.1 + 0.3 + 0.4) / 3.0
    )
    assert boundary_trials[0].metrics["f_herman_raw"] == pytest.approx(0.35)
    assert boundary_trials[0].metrics["orientation_strength"] == pytest.approx(0.5)
    assert boundary_trials[0].metrics["orientation_axis_deg"] == pytest.approx(
        179.0
    )

    boundary_intervals = _bootstrap(boundary_trials, request, seed=19)
    assert {
        "f_herman",
        "f_herman_raw",
        "orientation_axis_deg",
        "orientation_strength",
    }.issubset(boundary_intervals)
    boundary_axis = boundary_intervals["orientation_axis_deg"]
    assert boundary_axis.upper - boundary_axis.lower < 5.0

    wide_intervals = _bootstrap(
        (orientation_trial(0, 0.0), orientation_trial(1, 80.0)),
        request,
        seed=19,
    )
    wide_axis = wide_intervals["orientation_axis_deg"]
    assert wide_axis.upper - wide_axis.lower > 60.0


def test_continuity_median_increment_is_order_invariant_across_trials() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        StabilityTrial,
        _continuity_for_trials,
    )

    request = StabilityStudyRequest(
        baseline_config={"q_min": 0.1},
        domains=(ParameterDomain("q_min", 0.09, 0.11),),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        bootstrap_replicates=16,
    )
    trials = (
        StabilityTrial(
            index=0,
            config={"q_min": 0.09},
            score=1.0,
            physical_passed=True,
            quality_passed=True,
            continuity_passed=True,
            frame_values={"L_nm": (10.0, 11.0, 12.0, 13.0)},
        ),
        StabilityTrial(
            index=1,
            config={"q_min": 0.11},
            score=1.0,
            physical_passed=True,
            quality_passed=True,
            continuity_passed=True,
            frame_values={"L_nm": (10.0, 13.0, 16.0, 19.0)},
        ),
    )

    forward = _continuity_for_trials(trials, request)
    reverse = _continuity_for_trials(tuple(reversed(trials)), request)

    assert forward.to_dict() == reverse.to_dict()
    assert forward.metric_median_increment == {"L_nm": 2.0}


def test_static_stability_without_active_domains_reports_not_applicable(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from polynexus.orchestrator_stability import _run_saxs_stability_study

    class Harness:
        technique = "saxs"
        workspace_context = {"stability_mode": "quick"}
        submodule_override = "saxs.static"
        _last_stability_report: dict[str, object] = {}

        @staticmethod
        def _engine_config(engine):
            return engine.cfg

        @staticmethod
        def _config_to_dict(config):
            return dict(vars(config))

    report = _run_saxs_stability_study(
        Harness(),
        SimpleNamespace(
            cfg=SimpleNamespace(experiment_type="static"),
            _img=None,
            _sector_data_list=[],
        ),
    )

    assert report["decision"] == "keep_original"
    assert report["mode"] == "static"
    assert report["continuity"]["passed"] is False
    assert report["continuity"]["status"] == "not_applicable"
    assert report["continuity"]["frame_count"] == 0


def test_rejected_trial_discontinuity_does_not_poison_selected_plateau() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        ParameterDomain,
        StabilityStudyRequest,
        run_stability_study,
    )

    def evaluate(config: dict[str, float]) -> dict[str, object]:
        rejected = config["q_min"] < 0.08
        return {
            "score": 0.1 if rejected else 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {
                "L_nm": (
                    [10.0, 11.0, 30.0, 31.0, 32.0]
                    if rejected
                    else [10.0, 12.0, 15.0, 19.0, 24.0]
                )
            },
        }

    report = run_stability_study(
        StabilityStudyRequest(
            baseline_config={"q_min": 0.1},
            domains=(ParameterDomain("q_min", 0.05, 0.15),),
            seed=4,
            global_trials=6,
            active_trials=0,
            confirmation_trials=0,
            min_plateau_points=2,
            min_plateau_fraction=0.5,
            bootstrap_replicates=16,
            allow_auto_accept=False,
        ),
        evaluate,
    )

    assert any(
        "continuity_jump:L_nm" in trial.reason_codes for trial in report.trials
    )
    assert report.plateau.connected is True
    assert report.continuity.status == "passed"
    assert report.decision == "request_confirmation"


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


def test_stability_report_serializes_parameter_perturbation_interval_contract() -> None:
    import json

    from polynexus.core.preprocess_optimization.stability import (
        BootstrapInterval,
        ContinuityEvidence,
        PlateauSummary,
        StabilityReport,
    )

    interval = BootstrapInterval(
        lower=0.82,
        median=0.90,
        upper=0.96,
        replicates=32,
    )
    report = StabilityReport(
        schema_version="saxs-stability-v1",
        decision="request_confirmation",
        complete=True,
        baseline_config={"q_min": 0.1},
        selected_config={"q_min": 0.11},
        trials=(),
        plateau=PlateauSummary(connected=True),
        bootstrap={"score": interval},
        continuity=ContinuityEvidence(passed=True),
        physics_gate_passed=True,
        quality_gate_passed=True,
    )

    assert report.perturbation_intervals == report.bootstrap

    payload = json.loads(json.dumps(report.to_dict()))

    assert payload["interval_semantics"] == "parameter_perturbation"
    assert payload["perturbation_intervals"] == payload["bootstrap"]
    legacy_persisted = {"bootstrap": payload["bootstrap"]}
    assert legacy_persisted.get(
        "perturbation_intervals",
        legacy_persisted["bootstrap"],
    ) == payload["perturbation_intervals"]

    restored = StabilityReport(
        schema_version="saxs-stability-v1",
        decision="request_confirmation",
        complete=True,
        baseline_config={"q_min": 0.1},
        selected_config={"q_min": 0.11},
        trials=(),
        plateau=PlateauSummary(connected=True),
        perturbation_intervals={"score": interval},
        continuity=ContinuityEvidence(passed=True),
        physics_gate_passed=True,
        quality_gate_passed=True,
    )
    assert restored.perturbation_intervals == restored.bootstrap == {
        "score": interval
    }

    legacy_positional = StabilityReport(
        "saxs-stability-v1",
        "request_confirmation",
        True,
        {"q_min": 0.1},
        {"q_min": 0.11},
        (),
        PlateauSummary(connected=True),
        {"score": interval},
        ContinuityEvidence(passed=True),
        True,
        True,
    )
    assert legacy_positional.perturbation_intervals == legacy_positional.bootstrap == {
        "score": interval
    }

    with pytest.raises(ValueError, match="inconsistent"):
        StabilityReport(
            schema_version="saxs-stability-v1",
            decision="request_confirmation",
            complete=True,
            baseline_config={"q_min": 0.1},
            selected_config={"q_min": 0.11},
            trials=(),
            plateau=PlateauSummary(connected=True),
            perturbation_intervals={},
            bootstrap={"score": interval},
            continuity=ContinuityEvidence(passed=True),
            physics_gate_passed=True,
            quality_gate_passed=True,
        )



def test_stability_report_bootstrap_alias_is_read_only() -> None:
    from polynexus.core.preprocess_optimization.stability import (
        BootstrapInterval,
        ContinuityEvidence,
        PlateauSummary,
        StabilityReport,
    )

    interval = BootstrapInterval(0.82, 0.90, 0.96, 32)
    report = StabilityReport(
        schema_version="saxs-stability-v1",
        decision="request_confirmation",
        complete=True,
        baseline_config={"q_min": 0.1},
        selected_config={"q_min": 0.11},
        trials=(),
        plateau=PlateauSummary(connected=True),
        perturbation_intervals={"score": interval},
        continuity=ContinuityEvidence(passed=True),
        physics_gate_passed=True,
        quality_gate_passed=True,
    )

    alias = report.bootstrap
    with pytest.raises(TypeError):
        alias["score"] = BootstrapInterval(0.0, 0.0, 0.0, 16)
    with pytest.raises(AttributeError):
        alias.clear()
    assert report.perturbation_intervals == {"score": interval}


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
        if expected == "static":
            assert report["continuity"]["passed"] is False
            assert report["continuity"]["status"] == "not_applicable"


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


def test_active_orientation_domains_require_any_orientation_metric() -> None:
    from types import SimpleNamespace

    from polynexus.core.preprocess_optimization.stability import (
        StabilityStudyRequest,
        run_stability_study,
    )
    from polynexus.orchestrator_stability import _saxs_stability_domains

    domains = _saxs_stability_domains(
        _activity_domain_config(),
        mode="strain",
        engine=SimpleNamespace(
            _img=[[1.0, 2.0], [3.0, 4.0]],
            _sector_data_list=[{"chi_centers_deg": [0.0, 90.0]}],
        ),
    )
    by_name = {domain.name: domain for domain in domains}
    required = (
        "f_herman_raw",
        "orientation_axis_deg",
        "orientation_strength",
    )

    assert by_name["chi_halfwidth"].required_metrics == required
    assert by_name["mask_dilation_px"].required_metrics == required
    assert by_name["q_min"].required_metrics == ()

    request = StabilityStudyRequest(
        baseline_config={"chi_halfwidth": 15.0},
        domains=(by_name["chi_halfwidth"],),
        global_trials=1,
        active_trials=0,
        confirmation_trials=0,
        min_plateau_points=1,
        min_plateau_fraction=0.5,
        bootstrap_replicates=16,
        allow_auto_accept=False,
    )
    missing = run_stability_study(
        request,
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"L_nm": [10.0, 10.0, 10.0, 10.0]},
        },
    )

    assert missing.plateau.connected is False
    assert all(
        "active_dimension_evidence_missing:chi_halfwidth" in trial.reason_codes
        for trial in missing.trials
    )

    present = run_stability_study(
        request,
        lambda _config: {
            "score": 1.0,
            "physical_passed": True,
            "quality_passed": True,
            "frame_values": {"f_herman_raw": [0.2, 0.2, 0.2, 0.2]},
        },
    )

    assert present.plateau.connected is True
    assert all(
        not any(
            reason.startswith("active_dimension_evidence_missing:")
            for reason in trial.reason_codes
        )
        for trial in present.trials
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
