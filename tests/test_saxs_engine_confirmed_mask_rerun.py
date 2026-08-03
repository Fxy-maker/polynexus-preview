"""TDD coverage for the normal SAXS confirmed-mask rerun boundary."""

from __future__ import annotations

import numpy as np

from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_mask_edit import (
    build_mask_edit_candidate,
)
from polynexus.gui.main_window_workers import AnalysisWorker


def _candidate() -> dict[str, object]:
    base = np.zeros((4, 4), dtype=bool)
    edited = base.copy()
    edited[1, 2] = True
    return build_mask_edit_candidate(base, edited, source_path="sample.edf")


def _engine() -> SAXSEngine:
    return SAXSEngine(
        config=SAXSConfig(
            is_isotropic=True,
            analysis_priority="isotropic",
            use_pyfai_integration=False,
        )
    )


def _stub_static_run(monkeypatch, engine: SAXSEngine, seen: list[object]) -> None:
    monkeypatch.setattr(engine, "load", lambda _path: True)

    def fake_preprocess() -> bool:
        seen.append(getattr(engine, "_mask_edit_candidate", None))
        return True

    monkeypatch.setattr(engine, "preprocess", fake_preprocess)
    monkeypatch.setattr(engine, "analyze", lambda: True)
    monkeypatch.setattr(engine, "get_parameters", lambda: {})
    monkeypatch.setattr(engine, "_validate_results", lambda: True)


def test_engine_forwards_candidate_for_one_static_run(monkeypatch) -> None:
    engine = _engine()
    candidate = _candidate()
    seen: list[object] = []
    _stub_static_run(monkeypatch, engine, seen)

    engine.run_pipeline("sample.edf", mask_edit_candidate=candidate)

    assert seen == [candidate]
    assert getattr(engine, "_mask_edit_candidate", None) is None


def test_engine_clears_candidate_after_pipeline_failure(monkeypatch) -> None:
    engine = _engine()
    candidate = _candidate()
    monkeypatch.setattr(engine, "load", lambda _path: True)

    def fail_preprocess() -> bool:
        raise RuntimeError("synthetic preprocessing failure")

    monkeypatch.setattr(engine, "preprocess", fail_preprocess)
    monkeypatch.setattr(engine, "_validate_results", lambda: True)

    engine.run_pipeline("sample.edf", mask_edit_candidate=candidate)

    assert getattr(engine, "_mask_edit_candidate", None) is None


def test_plot_only_run_does_not_apply_candidate(monkeypatch) -> None:
    engine = _engine()
    candidate = _candidate()
    called = False

    def unexpected_preprocess() -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(engine, "preprocess", unexpected_preprocess)
    monkeypatch.setattr(engine, "_validate_results", lambda: True)

    engine.run_pipeline(
        "sample.edf",
        skip_to="plot",
        mask_edit_candidate=candidate,
    )

    assert called is False
    assert getattr(engine, "_mask_edit_candidate", None) is None


def test_sequence_preprocess_does_not_forward_candidate(monkeypatch) -> None:
    engine = _engine()
    engine._img = np.ones((4, 4), dtype=float)
    engine._file_list = ["frame-001.edf"]
    engine._condition_type = "temperature"
    engine._mask_edit_candidate = _candidate()
    calls: list[dict[str, object]] = []

    def fake_preprocess_pipeline(_img, _cfg, **kwargs):
        calls.append(kwargs)
        return {
            "q": np.array([0.01, 0.02]),
            "Iq": np.array([1.0, 2.0]),
            "Iq_smooth": np.array([1.0, 2.0]),
        }

    monkeypatch.setattr(
        "polynexus.core.saxs.preprocess_pipeline",
        fake_preprocess_pipeline,
    )

    assert engine.preprocess() is True
    assert calls == [{}]


def test_one_dimensional_preprocess_does_not_use_candidate(monkeypatch) -> None:
    engine = _engine()
    engine._q = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
    engine._I = np.array([1.0, 2.0, 1.5, 1.2, 1.0])
    engine._mask_edit_candidate = _candidate()

    def unexpected_preprocess_pipeline(*_args, **_kwargs):
        raise AssertionError("1D preprocessing must not enter the 2D pipeline")

    monkeypatch.setattr(
        "polynexus.core.saxs.preprocess_pipeline",
        unexpected_preprocess_pipeline,
    )

    assert engine.preprocess() is True


def test_analysis_worker_forwards_candidate_only_when_supplied() -> None:
    calls: list[dict[str, object]] = []

    class FakeEngine:
        def run_pipeline(self, filepath, output_dir, skip_to=None, **kwargs):
            calls.append(
                {
                    "filepath": filepath,
                    "output_dir": output_dir,
                    "skip_to": skip_to,
                    **kwargs,
                }
            )
            return object()

    candidate = _candidate()
    worker = AnalysisWorker(
        "saxs",
        "sample.edf",
        "out",
        engine=FakeEngine(),
        mask_edit_candidate=candidate,
    )

    worker.run()

    assert calls == [
        {
            "filepath": "sample.edf",
            "output_dir": "out",
            "skip_to": None,
            "mask_edit_candidate": candidate,
        }
    ]
