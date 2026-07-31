from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from polynexus.orchestrator import ParameterOrchestrator


def _frame(*, source_index: int, condition_key: str, condition_value: float) -> SimpleNamespace:
    return SimpleNamespace(
        source_index=source_index,
        **{condition_key: condition_value},
        data_quality_report={"level": "Trend", "reason_codes": ["frame_review"]},
        guinier_evidence={"level": "Quantitative", "rg_nm": 4.2},
        metric_evidence={"guinier": {"level": "Quantitative"}},
    )


def _orchestrator(technique: str = "saxs") -> ParameterOrchestrator:
    orchestrator = ParameterOrchestrator(
        technique=technique,
        data_file="dummy.edf",
        polymer_name="PA6",
        project_root=Path("."),
    )
    orchestrator._output_parameters = lambda _engine: {"r_squared": 0.8}  # type: ignore[method-assign]
    orchestrator._config_snapshot = lambda _engine: {}  # type: ignore[method-assign]
    orchestrator._residual_pattern = lambda _engine: {}  # type: ignore[method-assign]
    orchestrator._analysis_evidence = lambda _output, _residual: {"symptoms": []}  # type: ignore[method-assign]
    orchestrator._score_snapshot = lambda _output, _residual, _evidence: {"objective_score": 0.8}  # type: ignore[method-assign]
    orchestrator._ir_reference_bands = lambda _engine: {}  # type: ignore[method-assign]
    return orchestrator


def _engine(*, result: Any, temperature: Any = None, strain: Any = None) -> SimpleNamespace:
    return SimpleNamespace(
        result=result,
        _temperature_result=temperature,
        _strain_result=strain,
    )


def test_live_static_state_carries_summary_only_saxs_context() -> None:
    raw_result = SimpleNamespace(
        data_quality_report={"level": "Trend"},
        guinier_evidence={"level": "Quantitative", "rg_nm": 4.2},
        metric_evidence={"guinier": {"level": "Quantitative"}},
        q=[0.01, 0.02],
        I=[10.0, 9.0],
        source_path="secret/raw.edf",
    )
    state = _orchestrator()._build_agent_state(_engine(result=raw_result), 1)

    context = state["saxs_ai_context"]
    assert context["mode"] == "static"
    assert context["candidate_only"] is True
    assert context["physical_validation_required"] is True
    assert context["raw_profile_included"] is False
    assert context["raw_detector_data_included"] is False
    assert all(key not in context for key in ("q", "I", "source_path"))


@pytest.mark.parametrize(
    ("mode", "attribute", "condition_key"),
    [("temperature", "_temperature_result", "temperature_C"), ("strain", "_strain_result", "strain")],
)
def test_live_series_state_uses_existing_series_evidence(
    mode: str, attribute: str, condition_key: str
) -> None:
    series = SimpleNamespace(
        temp_points=[_frame(source_index=7, condition_key=condition_key, condition_value=170.0)]
        if mode == "temperature"
        else [],
        strain_points=[_frame(source_index=3, condition_key=condition_key, condition_value=2.0)]
        if mode == "strain"
        else [],
        guinier_sequence_evidence={"level": "Trend", "frame_source_indices": [7 if mode == "temperature" else 3]},
        metric_evidence={"guinier": {"level": "Trend"}},
    )
    engine = _engine(
        result=SimpleNamespace(),
        temperature=series if attribute == "_temperature_result" else None,
        strain=series if attribute == "_strain_result" else None,
    )

    context = _orchestrator()._build_agent_state(engine, 1)["saxs_ai_context"]

    assert context["mode"] == mode
    if mode == "temperature":
        assert context["series"]["guinier_sequence_evidence"]["level"] == "Trend"
    else:
        assert context["series"]["metric_evidence"]["guinier"]["level"] == "Trend"
    assert context["frames"][0]["source_index"] in {3, 7}


def test_non_saxs_state_does_not_gain_saxs_context() -> None:
    state = _orchestrator("waxs")._build_agent_state(_engine(result=SimpleNamespace()), 1)

    assert "saxs_ai_context" not in state


def test_live_context_projection_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import polynexus.orchestrator_state as state_module

    monkeypatch.setattr(
        state_module,
        "build_saxs_ai_summary_context",
        lambda _result, *, mode: (_ for _ in ()).throw(ValueError(f"bad {mode}")),
    )

    state = _orchestrator()._build_agent_state(_engine(result=SimpleNamespace()), 1)

    assert state["saxs_ai_context"] == {}
