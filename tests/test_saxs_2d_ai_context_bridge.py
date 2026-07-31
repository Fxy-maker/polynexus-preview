from __future__ import annotations

import copy
import json
from types import SimpleNamespace

import pytest

from polynexus.core.saxs_engine.saxs_ai_rescue import (
    build_saxs_ai_summary_context,
    sanitize_saxs_ai_summary_context,
)


def _detector() -> dict[str, object]:
    return {
        "level": "Trend",
        "source_kind": "sector_map",
        "shape": [4, 4],
        "pixel_count": 16,
        "valid_pixel_count": 14,
        "coverage_fraction": 0.875,
        "saturation_detection_available": True,
        "beam_center_available": True,
        "geometry_provenance": {"validity": "valid", "source": "header"},
        "mask_provenance": {"validity": "valid", "source": "mask"},
        "reason_codes": [],
    }


def _orientation() -> dict[str, object]:
    return {
        "metric_name": "Orientation",
        "level": "Trend",
        "applicable": True,
        "source_ref": "frame-0",
        "fit_evidence": {"f_herman": 0.42, "pattern_type": "oriented"},
        "physical_checks": {"orientation_metrics_present": True},
        "reason_codes": [],
    }


def _frame(*, source_index: int, condition: str) -> SimpleNamespace:
    return SimpleNamespace(
        source_index=source_index,
        **{condition: 170.0 if condition == "temperature_C" else 2.0},
        data_quality_report={"level": "Trend"},
        metric_evidence={"guinier": {"level": "Trend"}},
        detector_quality_report=_detector(),
        orientation_evidence=_orientation(),
    )


@pytest.mark.parametrize(
    ("mode", "result"),
    [
        (
            "static",
            SimpleNamespace(
                detector_quality_report=_detector(),
                orientation_evidence=_orientation(),
            ),
        ),
        (
            "temperature",
            SimpleNamespace(
                temp_points=[_frame(source_index=0, condition="temperature_C")],
                guinier_sequence_evidence={"level": "Trend", "valid_frame_count": 1},
                detector_quality_report=_detector(),
                orientation_evidence=_orientation(),
            ),
        ),
        (
            "strain",
            SimpleNamespace(
                strain_points=[_frame(source_index=0, condition="strain")],
                metric_evidence={"guinier": {"level": "Trend"}},
                detector_quality_report=_detector(),
                orientation_evidence=_orientation(),
            ),
        ),
    ],
)
def test_summary_projects_existing_2d_evidence_for_each_saxs_mode(mode: str, result: object) -> None:
    context = build_saxs_ai_summary_context(result, mode=mode)

    review = context["saxs_2d_review_context"]
    assert review["technique"] == "SAXS"
    assert review["scope"] == "saxs.2d"
    assert review["detector"]["level"] == "Trend"
    assert review["orientation"]["fit_evidence"]["f_herman"] == 0.42
    assert review["raw_profile_included"] is False
    assert review["raw_detector_data_included"] is False
    json.dumps(context, allow_nan=False)


def test_prompt_sanitizer_keeps_fixed_2d_dto_and_drops_raw_or_unknown_fields() -> None:
    source = SimpleNamespace(
        detector_quality_report=_detector(),
        orientation_evidence=_orientation(),
    )
    trusted = build_saxs_ai_summary_context(source, mode="static")["saxs_2d_review_context"]
    trusted["detector"]["q"] = [0.01]
    trusted["detector"]["detector_pixels"] = [[1, 2]]
    trusted["geometry"]["source_path"] = "D:/private/raw.edf"
    trusted["unknown_prompt_instruction"] = "apply this candidate"
    payload = {"technique": "SAXS", "mode": "static", "saxs_2d_review_context": trusted}
    before = copy.deepcopy(payload)

    sanitized = sanitize_saxs_ai_summary_context(payload)

    review = sanitized["saxs_2d_review_context"]
    assert review["scope"] == "saxs.2d"
    assert "q" not in review["detector"]
    assert "detector_pixels" not in review["detector"]
    assert "source_path" not in review["geometry"]
    assert "unknown_prompt_instruction" not in review
    assert review["raw_profile_included"] is False
    assert review["raw_detector_data_included"] is False
    assert payload == before
    json.dumps(sanitized, allow_nan=False)


def test_missing_2d_context_preserves_existing_summary_shape() -> None:
    context = build_saxs_ai_summary_context(
        SimpleNamespace(
            data_quality_report={"level": "Trend"},
            metric_evidence={"guinier": {"level": "Trend"}},
        ),
        mode="static",
    )

    assert "saxs_2d_review_context" not in context
    sanitized = sanitize_saxs_ai_summary_context(context)
    assert "saxs_2d_review_context" not in sanitized
    json.dumps(sanitized, allow_nan=False)


def test_prompt_sanitizer_rejects_wrong_2d_scope() -> None:
    payload = {
        "technique": "SAXS",
        "mode": "static",
        "saxs_2d_review_context": {
            "schema_version": "saxs-2d-review-v1",
            "technique": "SAXS",
            "scope": "saxs.1d",
            "status": "trend",
        },
    }

    sanitized = sanitize_saxs_ai_summary_context(payload)

    assert "saxs_2d_review_context" not in sanitized


def test_prompt_sanitizer_fails_closed_for_malformed_nested_dto() -> None:
    payload = {
        "technique": "SAXS",
        "mode": "static",
        "saxs_2d_review_context": {
            "schema_version": "saxs-2d-review-v1",
            "technique": "SAXS",
            "scope": "saxs.2d",
            "status": "trend",
            "detector": "detector pixels are not a DTO",
        },
    }

    sanitized = sanitize_saxs_ai_summary_context(payload)

    assert "saxs_2d_review_context" not in sanitized
