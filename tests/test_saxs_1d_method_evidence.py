from __future__ import annotations

from types import SimpleNamespace

import json
import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import analyze_single
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    MetricEvidence,
    QualityLevel,
    build_data_quality_report,
    build_invariant_evidence,
    build_kratky_evidence,
    build_lamellar_evidence,
    build_porod_evidence,
    contract_json,
)


def _quality() -> object:
    q = np.linspace(0.02, 2.5, 40)
    intensity = np.exp(-q) + 0.2
    return build_data_quality_report(q, intensity, source_id="synthetic-1d")


def _porod() -> dict:
    q = np.linspace(0.8, 2.5, 20)
    return {
        "Kp": 2.0,
        "Sv": 0.5,
        "slope": -4.0,
        "q_porod": q,
        "Iq4": np.full(q.size, 2.0),
    }


def _kratky() -> dict:
    q = np.linspace(0.02, 2.0, 40)
    kratky = q**2 * np.exp(-q)
    return {
        "q": q,
        "kratky": kratky,
        "kratky_norm": kratky / np.max(kratky),
        "q_peak_kratky": float(q[np.argmax(kratky)]),
    }


def _lamellar() -> tuple[SimpleNamespace, SimpleNamespace]:
    return (
        SimpleNamespace(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        SimpleNamespace(L=10.0, lc=3.0, la=7.0, phi_c=0.3, confidence_lc=0.8),
    )


def test_supported_1d_methods_emit_conservative_trend_evidence():
    quality = _quality()
    long_period, structure = _lamellar()

    metrics = [
        build_porod_evidence(_porod(), quality_report=quality, applicability="supported"),
        build_kratky_evidence(_kratky(), quality_report=quality, applicability="supported"),
        build_invariant_evidence(1.2, quality_report=quality, valid=True, applicability="supported"),
        build_lamellar_evidence(
            long_period, structure, quality_report=quality, applicability="supported"
        ),
    ]

    assert all(isinstance(metric, MetricEvidence) for metric in metrics)
    assert [metric.level for metric in metrics] == [QualityLevel.TREND] * 4
    assert all(metric.applicable is True for metric in metrics)
    assert all(json.loads(contract_json(metric))["level"] == "Trend" for metric in metrics)


def test_unknown_applicability_never_promotes_method_evidence():
    quality = _quality()
    long_period, structure = _lamellar()

    metrics = [
        build_porod_evidence(_porod(), quality_report=quality),
        build_kratky_evidence(_kratky(), quality_report=quality),
        build_invariant_evidence(1.2, quality_report=quality, valid=True),
        build_lamellar_evidence(long_period, structure, quality_report=quality),
    ]

    assert all(metric.level is QualityLevel.DIAGNOSTIC for metric in metrics)
    assert all(
        any("applicability_unresolved" in reason for reason in metric.reason_codes)
        for metric in metrics
    )


def test_porod_evidence_requires_slope_near_minus_four_and_iq4_plateau():
    quality = _quality()
    payload = _porod()
    payload["slope"] = -3.0
    payload["Iq4"] = np.linspace(1.0, 3.0, 20)

    metric = build_porod_evidence(payload, quality_report=quality, applicability="supported")

    assert metric.applicable is False
    assert metric.level is QualityLevel.DIAGNOSTIC
    assert "porod_slope_outside_tolerance" in metric.reason_codes
    assert "porod_iq4_plateau_unstable" in metric.reason_codes


def test_unusable_quality_and_missing_payloads_remain_unusable():
    q = np.asarray([0.1, 0.2, 0.3])
    quality = build_data_quality_report(q, np.ones_like(q))
    long_period, structure = _lamellar()

    metrics = [
        build_porod_evidence(None, quality_report=quality, applicability="supported"),
        build_kratky_evidence({}, quality_report=quality, applicability="supported"),
        build_invariant_evidence(None, quality_report=quality, applicability="supported"),
        build_lamellar_evidence(None, None, quality_report=quality, applicability="supported"),
    ]

    assert all(metric.level is QualityLevel.UNUSABLE for metric in metrics)
    assert all("data_quality_unusable" in metric.reason_codes for metric in metrics)


def test_analyze_single_preserves_legacy_outputs_and_attaches_metric_evidence():
    q = np.linspace(0.05, 2.5, 180)
    intensity = 300.0 * np.exp(-q) + 70.0 * np.exp(-0.5 * ((q - 0.7) / 0.06) ** 2)
    cfg = SAXSConfig(
        q_bragg_min=0.3,
        q_bragg_max=1.1,
        q_corr_min=0.1,
        q_corr_max=2.2,
        condition_context={
            "porod_applicability": "supported",
            "kratky_applicability": "supported",
            "invariant_applicability": "supported",
            "lamellar_applicability": "supported",
        },
    )

    result = analyze_single(q, intensity, cfg)

    assert result.porod is not None
    assert result.kratky is not None
    assert result.structure is not None
    assert set(result.metric_evidence) == {"porod", "kratky", "invariant", "lamellar"}
    assert all(payload["metric_name"] in {"Porod", "Kratky", "Q_star", "Lamellar"} for payload in result.metric_evidence.values())


def test_metric_evidence_builder_failure_does_not_drop_legacy_result(monkeypatch):
    import polynexus.core.saxs_engine.core as saxs_core

    q = np.linspace(0.05, 2.5, 120)
    intensity = 260.0 * np.exp(-q) + 55.0 * np.exp(-0.5 * ((q - 0.7) / 0.06) ** 2)
    monkeypatch.setattr(
        saxs_core,
        "build_porod_evidence",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("injected evidence failure")),
    )

    result = analyze_single(q, intensity, SAXSConfig())

    assert result.porod is not None
    assert result.metric_evidence["porod"]["level"] == "Diagnostic"
    assert result.metric_evidence["porod"]["reason_codes"] == ["metric_evidence_build_failed"]
