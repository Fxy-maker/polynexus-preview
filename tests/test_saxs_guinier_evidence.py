from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    QualityLevel,
    build_data_quality_report,
    build_guinier_evidence,
)


def _clean_fit():
    q = np.linspace(0.02, 0.18, 24)
    rg = 4.5
    ln_i = np.log(120.0) - q**2 * rg**2 / 3.0
    return q, ln_i, rg


def test_supported_guinier_fit_reports_uncertainty_and_quantitative_level():
    q, ln_i, rg = _clean_fit()
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=rg, i0=120.0, quality_report=quality,
        applicability="supported", source_ref="synthetic",
    )

    assert evidence.level is QualityLevel.QUANTITATIVE
    assert evidence.assumption_supported is True
    assert evidence.q_rg_max < 1.3
    assert evidence.r_squared > 0.99
    assert evidence.rg_uncertainty_nm is not None
    assert evidence.rg_uncertainty_nm >= 0
    assert evidence.metric is not None
    assert evidence.metric.level is QualityLevel.QUANTITATIVE


def test_unknown_guinier_applicability_is_diagnostic_even_when_fit_is_clean():
    q, ln_i, rg = _clean_fit()
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=rg, i0=120.0, quality_report=quality,
        applicability="unknown",
    )

    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "guinier_applicability_unresolved" in evidence.reason_codes


def test_qrg_gate_downgrades_a_fit_outside_the_guinier_assumption():
    _q, _ln_i, rg = _clean_fit()
    q = np.linspace(0.02, 0.40, 24)
    ln_i = np.log(120.0) - q**2 * rg**2 / 3.0
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=rg, i0=120.0, quality_report=quality,
        applicability="supported",
    )

    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "qrg_gate_failed" in evidence.reason_codes


def test_unusable_input_quality_cannot_produce_quantitative_guinier_evidence():
    q = np.asarray([0.02, 0.03, 0.04])
    ln_i = np.log(np.asarray([10.0, 9.0, 8.0]))
    quality = build_data_quality_report(q, np.exp(ln_i))

    evidence = build_guinier_evidence(
        q, ln_i, rg_nm=4.0, i0=10.0, quality_report=quality,
        applicability="supported",
    )

    assert evidence.level is QualityLevel.UNUSABLE
    assert "data_quality_unusable" in evidence.reason_codes


def test_guinier_metric_preserves_processed_quality_reference():
    q, ln_i, rg = _clean_fit()
    quality = build_data_quality_report(
        q,
        np.exp(ln_i),
        processed_data_ref="run/frame-001/I_smooth",
        processing_config_ref="run/config.json",
    )

    evidence = build_guinier_evidence(
        q,
        ln_i,
        rg_nm=rg,
        i0=120.0,
        quality_report=quality,
        applicability="supported",
    )

    assert evidence.metric is not None
    assert evidence.metric.data_quality_ref == "run/frame-001/I_smooth"
