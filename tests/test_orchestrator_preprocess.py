from __future__ import annotations

from copy import deepcopy
from types import MethodType

from polynexus.orchestrator import RoundRecord
from polynexus.orchestrator_run_round_preprocess_handler import (
    _handle_preprocess_intent_round,
)
from tests.preprocess_orchestrator_fakes import (
    build_fake_dsc_orchestrator,
    preprocess_intent,
)


def test_shadow_trial_records_candidate_but_restores_control() -> None:
    orchestrator = build_fake_dsc_orchestrator()

    report = orchestrator.run_preprocess_intent(preprocess_intent("smoothing"))

    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert report["preprocess_decision"]["simulated_decision"] in {
        "auto_accept",
        "request_confirmation",
        "keep_original",
    }
    assert orchestrator._engine_config(orchestrator._engine).smooth_window == 11
    assert report["preprocess_candidates"]
    assert orchestrator.created_trial_engines


def test_hard_guard_candidate_is_never_selected() -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.destroy_candidate_enthalpy = True

    report = orchestrator.run_preprocess_intent(preprocess_intent("smoothing"))

    assert report["preprocess_decision"]["confidence_band"] == "low"
    assert "integrated_area_change" in report["preprocess_decision"]["reason_codes"]
    assert orchestrator._engine_config(orchestrator._engine).smooth_window == 11


def test_both_intent_runs_smoothing_only_after_guard_passing_baseline() -> None:
    orchestrator = build_fake_dsc_orchestrator()

    report = orchestrator.run_preprocess_intent(preprocess_intent("both"))

    stages = [item["stage"] for item in report["preprocess_candidates"]]
    assert "baseline" in stages
    assert "smoothing" in stages
    assert stages.index("smoothing") > stages.index("baseline")


def test_invalid_intent_fails_closed_without_mutating_control() -> None:
    orchestrator = build_fake_dsc_orchestrator()
    before = deepcopy(orchestrator._config_to_dict(orchestrator._best_config))
    payload = preprocess_intent()
    payload["smooth_window"] = 99

    report = orchestrator.run_preprocess_intent(payload)

    assert report["preprocess_decision"]["decision"] == "keep_original"
    assert report["preprocess_decision"]["confidence_band"] == "low"
    assert report["preprocess_candidates"] == []
    assert orchestrator._config_to_dict(orchestrator._best_config) == before


def test_round_record_preprocess_fields_are_backward_compatible_defaults() -> None:
    record = RoundRecord(
        round_num=0,
        config_snapshot={},
        output_parameters={},
        residuals_pattern={},
        analysis_evidence={},
        polymer_knowledge={},
        r_squared=0.0,
        eval_score=0.0,
        llm_advice=None,
    )

    assert record.preprocess_intent == {}
    assert record.preprocess_candidates == []
    assert record.preprocess_evidence == []
    assert record.preprocess_decision == {}


def test_preprocess_round_populates_record_and_does_not_use_generic_candidates() -> None:
    orchestrator = build_fake_dsc_orchestrator()
    orchestrator.history = []
    previous = RoundRecord(
        round_num=0,
        config_snapshot=orchestrator._config_to_dict(orchestrator._best_config),
        output_parameters=deepcopy(orchestrator._best_output),
        residuals_pattern={"rmse": 1.0},
        analysis_evidence={},
        polymer_knowledge={},
        r_squared=0.0,
        eval_score=0.0,
        llm_advice=None,
    )
    orchestrator._record_round = MethodType(
        lambda self, engine, round_num, advice, **kwargs: RoundRecord(
            round_num=round_num,
            config_snapshot=self._config_to_dict(self._engine_config(engine)),
            output_parameters=self._output_parameters(engine),
            residuals_pattern=self._residual_pattern(engine),
            analysis_evidence={},
            polymer_knowledge={},
            r_squared=0.0,
            eval_score=0.0,
            llm_advice=advice,
        ),
        orchestrator,
    )
    orchestrator._emit_progress = MethodType(lambda self, *args, **kwargs: None, orchestrator)

    outcome = _handle_preprocess_intent_round(
        orchestrator,
        orchestrator._engine,
        1,
        {"preprocess_intent": preprocess_intent("smoothing"), "changes": {}},
        previous,
        "prompt",
    )

    assert outcome["stop"] is True
    assert len(orchestrator.history) == 1
    assert orchestrator.history[0].preprocess_intent["target"] == "smoothing"
    assert orchestrator.history[0].preprocess_candidates
    assert orchestrator._last_preprocess_report["preprocess_decision"]
