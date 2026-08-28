from __future__ import annotations

import pytest

from polynexus.core.compute.method_sensitivity import MethodSensitivity
from polynexus.core.compute.method_sensitivity import (
    METHOD_SENSITIVITY_DIMENSIONS,
    evaluate_method_sensitivity,
    sensitivities_from_metrics,
)
from polynexus.core.compute.models import ComputeResult


def test_method_sensitivity_keeps_primary_candidate_and_difference_range():
    sensitivity = MethodSensitivity.create(
        metric_path="Xc_pct",
        primary_method="endpoint_linear",
        primary_value=40.0,
        candidates={"tail_constant": 42.0, "quadratic": 39.0},
        parameters={"window": [0.05, 0.8]},
        source="sample.dsc",
        warnings=("baseline_review",),
    )

    assert sensitivity.difference_range == pytest.approx(3.0)
    assert sensitivity.to_dict() == {
        "metric_path": "Xc_pct",
        "primary": {"method": "endpoint_linear", "value": 40.0},
        "candidates": [
            {"method": "quadratic", "value": 39.0},
            {"method": "tail_constant", "value": 42.0},
        ],
        "difference_range": 3.0,
        "parameters": {"window": [0.05, 0.8]},
        "source": "sample.dsc",
        "warnings": ["baseline_review"],
        "status": "computed",
    }


def test_method_sensitivity_preserves_unavailable_difference():
    sensitivity = MethodSensitivity.create(
        metric_path="peak_area",
        primary_method="fit",
        primary_value=None,
        candidates={"integral": 2.0},
    )

    assert sensitivity.difference_range is None
    assert sensitivity.status == "unavailable"


def test_compute_result_serializes_method_sensitivity_alongside_metrics():
    sensitivity = MethodSensitivity.create(
        metric_path="Xc_pct",
        primary_method="endpoint_linear",
        primary_value=40.0,
        candidates={"tail_constant": 42.0},
    )
    result = ComputeResult(metrics={"Xc_pct": 40.0}, method_sensitivities=(sensitivity,))

    assert result.to_public_dict()["method_sensitivities"][0]["difference_range"] == 2.0


def test_evaluate_method_sensitivity_runs_explicit_candidates_deterministically():
    sensitivity = evaluate_method_sensitivity(
        metric_path="peak.area",
        primary_method="endpoint",
        methods={"tail": lambda: 11.0, "endpoint": lambda: 10.0},
        source="sample.csv",
    )

    assert sensitivity.to_dict()["primary"] == {"method": "endpoint", "value": 10.0}
    assert sensitivity.to_dict()["candidates"] == [{"method": "tail", "value": 11.0}]
    assert sensitivity.difference_range == 1.0


def test_sensitivities_from_metrics_only_consumes_explicit_variant_payloads():
    metrics = {
        "method_variants": {
            "Xc_pct": {
                "primary_method": "peak_area",
                "primary": 40.0,
                "candidates": {"halo_fit": 42.0},
                "parameters": {"window": [10, 20]},
            }
        }
    }

    values = sensitivities_from_metrics(metrics, technique="waxs", source="sample.raw")

    assert len(values) == 1
    assert values[0].metric_path == "Xc_pct"
    assert values[0].source == "sample.raw"
    assert values[0].difference_range == 2.0


def test_sensitivities_from_metrics_extracts_dsc_baseline_variants():
    metrics = {
        "baseline_method": "endpoint_linear",
        "DHc_iso_Jg": 10.0,
        "baseline_variants": [
            {"method": "endpoint_linear", "area_Wg_min": 10.0},
            {"method": "tail_constant", "area_Wg_min": 12.0},
        ],
    }

    values = sensitivities_from_metrics(metrics, technique="dsc")

    assert [item.metric_path for item in values] == ["area_Wg_min"]
    assert values[0].primary_method == "endpoint_linear"
    assert values[0].candidates == {"tail_constant": 12.0}


def test_method_sensitivity_dimensions_cover_supported_techniques_without_defaults():
    assert set(METHOD_SENSITIVITY_DIMENSIONS) >= {"dsc", "ftir", "saxs", "waxs", "nmr"}
    assert "normalization" in METHOD_SENSITIVITY_DIMENSIONS["ftir"]
    assert "fit_model" in METHOD_SENSITIVITY_DIMENSIONS["saxs"]
    assert "region_integration" in METHOD_SENSITIVITY_DIMENSIONS["nmr"]
