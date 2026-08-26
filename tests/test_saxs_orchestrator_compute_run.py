from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from polynexus.core.compute import ComputeRunService
from polynexus.core.engine import AnalysisResult
from polynexus.orchestrator import ParameterOrchestrator
from polynexus.orchestrator_session import _execute_candidate_trial
from polynexus.orchestrator_session import _merge_saxs_recovery_context


class _Engine:
    def __init__(self) -> None:
        self.cfg = SimpleNamespace(condition_context={})
        self.result = AnalysisResult(technique="saxs")
        self.pipeline_calls = 0

    def run_pipeline(self, _path: str, output_dir: str = "", **_options: Any) -> AnalysisResult:
        self.pipeline_calls += 1
        self.result.parameters = {"r_squared": 0.9}
        self.result.figures = {}
        self.result.metadata = {}
        return self.result

    def get_parameters(self) -> dict[str, Any]:
        return dict(self.result.parameters)


def _recovery_advice() -> dict[str, Any]:
    return {
        "candidate_plan": {
            "action_name": "rerun_condition_recovery",
            "recovery_context": {"batch": {"condition_values": {"temperature": 120.0}}},
        },
        "changes": {},
    }


def _recovery_orchestrator(source: Path) -> ParameterOrchestrator:
    orchestrator = ParameterOrchestrator.__new__(ParameterOrchestrator)
    orchestrator.technique = "saxs"
    orchestrator.data_file = str(source)
    orchestrator.submodule_override = None
    orchestrator._compute_run = None
    orchestrator._resolve_data_file = lambda value: Path(value)
    orchestrator._engine_config = lambda engine: engine.cfg
    orchestrator._submodule_id = lambda: "saxs.static"
    orchestrator._to_plain_value = lambda value: value
    orchestrator._advice_rollback_detail = lambda _advice: ""
    orchestrator._advice_target_symptom = lambda _advice, _evidence: "condition_axis_missing"
    orchestrator._decision_summary = lambda accepted, *_args: "accepted" if accepted else "rejected"
    orchestrator._quality_guard = lambda _record: (True, "")
    orchestrator._evaluate_candidate = lambda *_args: (True, "", {})
    orchestrator._record_round = lambda *_args, **_kwargs: SimpleNamespace(
        llm_advice={},
        analysis_evidence={},
        accepted=True,
        target_symptom="",
        rollback_detail="",
        decision_summary="",
        r_squared=0.9,
        eval_score=0.9,
        changes={},
    )
    return orchestrator


def test_recovery_reuses_shared_service_for_real_source(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("q,I\n0.1,1\n0.2,2\n", encoding="utf-8")
    engine = _Engine()
    initial = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="saxs", path=source, output_dir="", engine=engine
    )
    assert initial.status == "completed"
    orchestrator = _recovery_orchestrator(source)
    orchestrator._compute_run = initial
    calls: list[dict[str, Any]] = []
    real_service = ComputeRunService(lambda *args, **kwargs: engine)

    class _SpyService:
        def __init__(self, _factory):
            pass

        def run_direct(self, **kwargs: Any):
            calls.append(kwargs)
            return real_service.run_direct(**kwargs)

    monkeypatch.setattr("polynexus.orchestrator_session.ComputeRunService", _SpyService, raising=False)
    outcome = _execute_candidate_trial(
        orchestrator,
        engine,
        1,
        SimpleNamespace(r_squared=0.0, eval_score=0.0),
        _recovery_advice(),
        {},
        "",
    )

    assert outcome["status"] == "accepted"
    assert len(calls) == 1
    assert calls[0]["canonical_template"].content_hash == initial.canonical_template.content_hash
    assert outcome["compute_run"].status == "completed"
    assert orchestrator._compute_run is initial


def test_recovery_keeps_provider_fallback_for_synthetic_source(monkeypatch) -> None:
    engine = _Engine()
    orchestrator = _recovery_orchestrator(Path("dummy.dat"))

    class _FailingService:
        def __init__(self, _factory):
            pass

        def run_direct(self, **_kwargs: Any):
            raise AssertionError("synthetic recovery must not use ComputeRunService")

    monkeypatch.setattr("polynexus.orchestrator_session.ComputeRunService", _FailingService, raising=False)
    outcome = _execute_candidate_trial(
        orchestrator,
        engine,
        1,
        SimpleNamespace(r_squared=0.0, eval_score=0.0),
        _recovery_advice(),
        {},
        "",
    )

    assert outcome["status"] == "accepted"
    assert engine.pipeline_calls == 1


def test_recovery_service_failure_keeps_baseline_run(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("q,I\n0.1,1\n0.2,2\n", encoding="utf-8")
    engine = _Engine()
    initial = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="saxs", path=source, output_dir="", engine=engine
    )
    orchestrator = _recovery_orchestrator(source)
    orchestrator._compute_run = initial

    class _NeedsInputRun:
        status = "needs_input"
        reasons = ("canonical_template_mismatch",)
        legacy_result = None

    class _FailingService:
        def __init__(self, _factory):
            pass

        def run_direct(self, **_kwargs: Any):
            return _NeedsInputRun()

    monkeypatch.setattr("polynexus.orchestrator_session.ComputeRunService", _FailingService)
    outcome = _execute_candidate_trial(
        orchestrator,
        engine,
        1,
        SimpleNamespace(r_squared=0.0, eval_score=0.0),
        _recovery_advice(),
        {},
        "",
    )

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "canonical_template_mismatch"
    assert orchestrator._compute_run is initial
    assert engine.pipeline_calls == 1


def test_recovery_context_merge_is_replayable_after_baseline_restore() -> None:
    config = SimpleNamespace(
        condition_context={"sample_id": "S-01", "batch": {"existing": True}}
    )

    _merge_saxs_recovery_context(
        config,
        {"batch": {"condition_values": {"temperature": 120.0}}},
    )

    assert config.condition_context == {
        "sample_id": "S-01",
        "batch": {
            "existing": True,
            "condition_values": {"temperature": 120.0},
        },
    }
