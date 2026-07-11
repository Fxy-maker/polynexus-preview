from __future__ import annotations

import importlib

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig


def test_single_frame_lc_reliability_reports_diagnostic_only_for_invalid_invariant() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_quality_helpers")

    status, reason = helpers.classify_single_frame_lc_reliability(
        {
            "lc_confidence": 0.15,
            "lc_method": "tangent",
            "Q_star_valid": False,
            "Q_star": 0.3,
        }
    )

    assert status == "diagnostic_only"
    assert reason == "low_lc_confidence|single_method_fragile|q_invariant_invalid"


def test_saxs_peak_region_fit_quality_combines_bragg_and_guinier_regions() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_quality_helpers")

    q = np.linspace(0.2, 1.0, 80)
    intensity = 8.0 + 55.0 * np.exp(-0.5 * ((q - 0.62) / 0.07) ** 2)
    q_guinier = np.linspace(0.04, 0.12, 12)
    lnI_guinier = 4.2 - 18.0 * (q_guinier**2)

    fit_quality = helpers._saxs_peak_region_fit_quality(
        q,
        intensity,
        SAXSConfig(q_bragg_min=0.3, q_bragg_max=0.9),
        q_bragg_min=0.3,
        q_bragg_max=0.9,
        q_guinier=q_guinier,
        lnI_guinier=lnI_guinier,
    )

    assert fit_quality["method"] == "saxs_peak_region_fit_r2"
    assert fit_quality["r_squared"] > 0.95
    assert fit_quality["fit_rmse"] < 0.3
    assert [region["kind"] for region in fit_quality["fit_regions"]] == ["bragg_peak", "guinier"]


def test_core_reuses_saxs_quality_helper_functions() -> None:
    helpers = importlib.import_module("polynexus.core.saxs_engine.saxs_quality_helpers")
    core = importlib.import_module("polynexus.core.saxs_engine.core")

    assert core._finite_float is helpers._finite_float
    assert core.classify_single_frame_lc_reliability is helpers.classify_single_frame_lc_reliability
    assert core._standardized_region_stats is helpers._standardized_region_stats
    assert core._fit_bragg_region is helpers._fit_bragg_region
    assert core._fit_guinier_region is helpers._fit_guinier_region
    assert core._saxs_peak_region_fit_quality is helpers._saxs_peak_region_fit_quality
