from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import analyze_strain_series
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def _metric_payload(frame_id: str) -> dict:
    return {
        "porod": {"metric_name": "Porod", "level": "Trend", "source": frame_id},
        "kratky": {"metric_name": "Kratky", "level": "Diagnostic", "source": frame_id},
        "invariant": {"metric_name": "Q_star", "level": "Trend", "source": frame_id},
        "lamellar": {"metric_name": "Lamellar", "level": "Trend", "source": frame_id},
    }


def _fake_saxs_result(frame_id: str = "frame") -> SimpleNamespace:
    return SimpleNamespace(
        long_period=SimpleNamespace(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        structure=SimpleNamespace(
            L=10.0, lc=3.0, la=7.0, phi_c=0.3, confidence_lc=0.8
        ),
        data_quality_report={"level": "Quantitative", "source_id": frame_id},
        guinier_evidence={"rg_nm": 4.0, "level": "Trend", "reason_codes": []},
        metric_evidence=_metric_payload(frame_id),
    )


def test_temperature_propagates_frame_specific_evidence_and_keeps_failure_missing(monkeypatch):
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-q**2 * 4.0**2 / 3.0)
    calls = {"count": 0}

    def fake_analyze(q_arr, i_arr, cfg):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("injected temperature failure")
        return _fake_saxs_result(f"temperature-{calls['count']}")

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_temperature_series(
        [170.0, 180.0, 190.0], [q, q, q], [intensity, intensity, intensity], cfg=SAXSConfig()
    )

    assert len(result.temp_points) == 3
    assert result.temp_points[0].metric_evidence["porod"]["source"] == "temperature-1"
    assert result.temp_points[1].metric_evidence is None
    assert result.temp_points[1].data_quality_report is None
    assert result.metric_evidence["porod"]["level"] == "Diagnostic"
    assert result.metric_evidence["porod"]["missing_frame_count"] == 1
    assert result.metric_evidence["porod"]["applicable"] is False
    table = result.to_dataframe()
    assert "Metric_evidence_levels" in table.columns
    assert table.iloc[0]["Metric_evidence_levels"] == "invariant:Trend|kratky:Diagnostic|lamellar:Trend|porod:Trend"
    assert str(table.iloc[1]["Metric_evidence_levels"]) == "nan"


def test_strain_propagates_evidence_without_creating_temperature_sequence_state(monkeypatch):
    import polynexus.core.saxs_engine.saxs_strain as module

    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-q**2 * 4.0**2 / 3.0)
    calls = {"count": 0}

    def fake_analyze(q_arr, i_arr, cfg):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("injected strain failure")
        return _fake_saxs_result(f"strain-{calls['count']}")

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", lambda q_arr, i_arr, cfg=None: 1.0)
    monkeypatch.setattr(module, "bragg_long_period", lambda q_arr, i_arr: (10.0, 0.628, {}))

    result = analyze_strain_series(
        [0.0, 10.0], [q, q], [intensity, intensity], cfg=SAXSConfig()
    )

    assert len(result.strain_points) == 2
    assert result.strain_points[0].metric_evidence["lamellar"]["source"] == "strain-1"
    assert result.strain_points[1].metric_evidence is None
    assert result.strain_points[0].data_quality_report["source_id"] == "strain-1"
    assert result.metric_evidence["porod"]["level"] == "Diagnostic"
    assert result.metric_evidence["porod"]["missing_frame_count"] == 1
    assert not hasattr(result, "guinier_sequence_evidence")
    assert "Metric_evidence_levels" in result.to_dataframe().columns
