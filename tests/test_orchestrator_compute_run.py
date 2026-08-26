from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import polynexus.orchestrator_run_bootstrap as bootstrap
from polynexus.orchestrator_session import _final_report
from polynexus.orchestrator_models import RoundRecord
from polynexus.core.compute import ComputeRunService


class _Engine:
    def __init__(self) -> None:
        self.result = SimpleNamespace(parameters={}, figures={}, metadata={})


def test_bootstrap_uses_shared_compute_run_for_existing_source(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.dat"
    source.write_text("q I\n0.1 1\n0.2 2\n", encoding="utf-8")
    engine = _Engine()
    calls: list[dict[str, object]] = []
    compute_run = SimpleNamespace(status="completed", legacy_result=engine.result)

    class _ComputeRunService:
        def __init__(self, engine_factory):
            self.engine_factory = engine_factory

        def run_direct(self, **kwargs):
            calls.append(kwargs)
            return compute_run

    monkeypatch.setattr(bootstrap, "ComputeRunService", _ComputeRunService, raising=False)
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: engine)

    record = SimpleNamespace(
        r_squared=0.8,
        eval_score=0.7,
        output_parameters={"r_squared": 0.8},
    )
    harness = SimpleNamespace(
        data_file=str(source),
        project_root=tmp_path,
        technique="waxs",
        history=[],
        _resolve_data_file=lambda value: Path(value),
        _submodule_id=lambda: None,
        _record_round=lambda *args, **kwargs: record,
        _engine_config=lambda _engine: None,
    )

    data_path, resolved_engine, baseline = bootstrap._initialize_run_session(harness)

    assert data_path == source
    assert resolved_engine is engine
    assert baseline is record
    assert harness._compute_run is compute_run
    assert len(calls) == 1
    assert calls[0]["technique"] == "waxs"
    assert calls[0]["path"] == source
    assert calls[0]["engine"] is engine


def test_bootstrap_does_not_bypass_ambiguous_canonical_mapping(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text("A,B,C\n1,2,3\n4,5,6\n", encoding="utf-8")
    engine = _Engine()
    engine.calls = 0

    def run_pipeline(*_args, **_kwargs):
        engine.calls += 1
        return engine.result

    engine.run_pipeline = run_pipeline
    monkeypatch.setattr("polynexus.orchestrator.get_engine", lambda *args, **kwargs: engine)

    harness = SimpleNamespace(
        data_file=str(source),
        project_root=tmp_path,
        technique="ir",
        history=[],
        _resolve_data_file=lambda value: Path(value),
        _submodule_id=lambda: None,
        _record_round=lambda *args, **kwargs: None,
        _engine_config=lambda _engine: None,
    )

    with pytest.raises(RuntimeError, match="conversion_mapping_ambiguous"):
        bootstrap._initialize_run_session(harness)
    assert engine.calls == 0


def test_final_report_exposes_json_safe_compute_run_projection() -> None:
    compute_run = SimpleNamespace(
        to_dict=lambda: {
            "status": "completed",
            "canonical_template": {"template_id": "spectrum_1d.v1"},
        }
    )
    record = RoundRecord(
        round_num=0,
        config_snapshot={},
        output_parameters={"r_squared": 0.8},
        residuals_pattern={},
        analysis_evidence={},
        polymer_knowledge={},
        r_squared=0.8,
        eval_score=0.7,
        llm_advice=None,
    )
    harness = SimpleNamespace(
        technique="ir",
        _public_submodule=lambda: "ir.standard",
        polymer_name="PA6",
        _config_to_dict=lambda value: value or {},
        _best_config={},
        _baseline_r_squared=0.8,
        _best_r_squared=0.8,
        _baseline_eval_score=0.7,
        _best_eval_score=0.7,
        _best_output={"r_squared": 0.8},
        history=[record],
        _benchmark_summary=lambda: {"rounds": 0},
        _to_plain_value=lambda value: value,
        _compute_run=compute_run,
        _last_preprocess_report={},
        _last_stability_report={},
    )

    report = _final_report(harness, Path("sample.csv"), False, "max_rounds")

    assert report["compute_run"]["canonical_template"]["template_id"] == "spectrum_1d.v1"


def test_compute_service_keeps_empty_string_as_no_render_output(tmp_path: Path) -> None:
    source = tmp_path / "sample.dat"
    source.write_text("q I\n0.1 1\n0.2 2\n", encoding="utf-8")
    engine = _Engine()
    calls: list[str] = []

    def run_pipeline(_path, output_dir, **_options):
        calls.append(output_dir)
        return engine.result

    engine.run_pipeline = run_pipeline
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="waxs", path=source, output_dir="", engine=engine
    )

    assert run.status == "completed"
    assert calls == [""]
