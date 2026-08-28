from __future__ import annotations

import pytest

from polynexus.core.compute.method_sensitivity import MethodSensitivity
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
