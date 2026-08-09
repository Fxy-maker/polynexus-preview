"""Regression coverage for SAXS pipeline stage timing diagnostics."""

from __future__ import annotations

import re

from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig


def test_saxs_pipeline_records_stage_timings(monkeypatch, tmp_path) -> None:
    """Each executed SAXS boundary emits one elapsed-time diagnostic."""

    engine = SAXSEngine(config=SAXSConfig(experiment_type="static"), log_fn=lambda _line: None)
    monkeypatch.setattr("polynexus.core.saxs.publish_saxs_result_contract", lambda _engine: None)
    monkeypatch.setattr(engine, "load", lambda _path: True)
    monkeypatch.setattr(engine, "preprocess", lambda: True)
    monkeypatch.setattr(engine, "analyze", lambda: True)
    monkeypatch.setattr(engine, "get_parameters", lambda: {})
    monkeypatch.setattr(engine, "plot", lambda _output_dir: {"profile": "figure.png"})
    monkeypatch.setattr(engine, "_validate_results", lambda: True)

    result = engine.run_pipeline("sample.edf", output_dir=str(tmp_path))

    timing_logs = [line for line in result.logs if line.startswith("[PERF] SAXS ")]
    assert [re.match(r"\[PERF\] SAXS (load|preprocess|analyze|plot): [0-9]+\.[0-9]{3}s$", line).group(1)
            for line in timing_logs] == ["load", "preprocess", "analyze", "plot"]


def test_saxs_plot_only_pipeline_times_only_plot(monkeypatch, tmp_path) -> None:
    """A plot-only rerun does not report skipped load/preprocess/analyze stages."""

    engine = SAXSEngine(config=SAXSConfig(experiment_type="static"), log_fn=lambda _line: None)
    monkeypatch.setattr("polynexus.core.saxs.publish_saxs_result_contract", lambda _engine: None)
    monkeypatch.setattr(engine, "plot", lambda _output_dir: {})
    monkeypatch.setattr(engine, "_validate_results", lambda: True)

    result = engine.run_pipeline("sample.edf", output_dir=str(tmp_path), skip_to="plot")

    timing_logs = [line for line in result.logs if line.startswith("[PERF] SAXS ")]
    assert len(timing_logs) == 1
    assert re.match(r"\[PERF\] SAXS plot: [0-9]+\.[0-9]{3}s$", timing_logs[0])
