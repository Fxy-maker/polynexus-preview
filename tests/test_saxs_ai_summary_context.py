from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from polynexus.core.saxs_engine.saxs_ai_rescue import build_saxs_ai_summary_context


def _frame(*, source_index: int = 0, level: str = "Trend") -> SimpleNamespace:
    return SimpleNamespace(
        source_index=source_index,
        temperature_C=25.0 + source_index,
        quality_flag="OK",
        Q_star_valid=True,
        data_quality_report={
            "level": level,
            "reason_codes": ["existing_quality_summary"],
            "coverage_fraction": 1.0,
        },
        guinier_evidence={
            "metric_name": "Rg",
            "value": 4.2,
            "unit": "nm",
            "physical_checks": {"method_gate_passed": True},
        },
        metric_evidence={
            "physical_checks": {"method_gate_passed": True},
            "reason_codes": [],
        },
        raw_q=[0.01, 0.02],
        raw_I=[100.0, 90.0],
        detector_pixels=[[1, 2], [3, 4]],
    )


def test_summary_context_is_strict_json_and_excludes_raw_profile_data() -> None:
    result = SimpleNamespace(
        temp_points=[_frame()],
        guinier_sequence_evidence={
            "level": "Trend",
            "reason_codes": ["existing_sequence_summary"],
            "valid_frame_count": 1,
        },
        validation_passed=True,
    )

    context = build_saxs_ai_summary_context(result, mode="temperature")

    json.dumps(context, allow_nan=False)
    assert context["technique"] == "SAXS"
    assert context["mode"] == "temperature"
    assert context["status"] == "available"
    assert context["quality_gate_status"] == "passed"
    assert context["physical_gate_status"] == "passed"
    assert context["candidate_only"] is True
    assert context["raw_profile_included"] is False
    assert context["raw_detector_data_included"] is False
    serialized = json.dumps(context, ensure_ascii=False)
    assert "raw_q" not in serialized
    assert "raw_I" not in serialized
    assert "detector_pixels" not in serialized


def test_summary_context_fails_closed_for_unsupported_or_missing_result() -> None:
    for result, mode in ((None, "temperature"), (SimpleNamespace(), "unknown")):
        context = build_saxs_ai_summary_context(result, mode=mode)

        assert context["status"] == "unavailable"
        assert context["frames"] == []
        assert context["reason_codes"]
        json.dumps(context, allow_nan=False)


@pytest.mark.parametrize("mode", ("static", "temperature", "strain"))
def test_summary_context_preserves_all_existing_1d_method_evidence(mode: str) -> None:
    metric_names = ("porod", "kratky", "invariant", "lamellar")
    metric_evidence = {
        name: {
            "metric_name": name.title(),
            "level": "Trend",
            "value": float(index + 1),
            "unit": "a.u.",
            "reason_codes": [f"{name}_evidence"],
            "physical_checks": {"method_gate_passed": True},
        }
        for index, name in enumerate(metric_names)
    }
    frame = _frame()
    frame.metric_evidence = {
        **metric_evidence,
        "guinier": {
            "metric_name": "Rg",
            "level": "Quantitative",
            "value": 4.2,
            "unit": "nm",
        },
    }
    if mode == "static":
        result = SimpleNamespace(frames=[frame], metric_evidence=frame.metric_evidence, validation_passed=True)
    elif mode == "temperature":
        result = SimpleNamespace(
            temp_points=[frame],
            metric_evidence=frame.metric_evidence,
            guinier_sequence_evidence={"level": "Trend", "valid_frame_count": 1},
            validation_passed=True,
        )
    else:
        result = SimpleNamespace(
            strain_points=[frame],
            metric_evidence=frame.metric_evidence,
            validation_passed=True,
        )

    context = build_saxs_ai_summary_context(result, mode=mode)
    projected = context["series"]["metric_evidence"]

    assert set(projected) == {*metric_names, "guinier"}
    for name in metric_names:
        assert projected[name]["level"] == "Trend"
        assert projected[name]["physical_checks"]["method_gate_passed"] is True
    json.dumps(context, allow_nan=False)
