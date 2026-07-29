from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_temperature import (
    build_temperature_figure_definitions,
)
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


def _review_payload(*, source_refs: tuple[str, ...], scope: str = "saxs.1d") -> dict[str, object]:
    decisions: dict[str, str]
    if scope == "saxs.2d":
        decisions = {
            "geometry_reference": "existing_header_or_config",
            "beam_center_policy": "explicit_or_diagnostic",
            "mask_policy": "existing_mask_only",
            "saturation_policy": "diagnostic_when_unknown",
            "orientation_applicability": "review_required",
            "promotion_rule": "review_and_physical_gates",
        }
    else:
        decisions = {
            "sequence_axis_policy": "observed_only",
            "frame_identity_policy": "source_index_and_raw_ref",
            "missing_repeat_policy": "diagnostic_only",
            "metric_claim_scope": "existing_quality_levels",
            "promotion_rule": "review_and_physical_gates",
        }
    return {
        "record_id": "review-saxs-1d-001",
        "scope": scope,
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-29T10:00:00Z",
        "policy_version": "saxs-1d-v1",
        "source_refs": list(source_refs),
        "decisions": decisions,
        "status": "accepted",
        "conditions": [],
    }


def _temperature_engine(review: object = None) -> SimpleNamespace:
    paths = ("source-0.dat", "source-1.dat")
    frames = tuple(
        SAXSFrameView(
            index=index,
            label=f"frame-{index}",
            condition=temperature,
            q=np.asarray([0.1, 0.2, 0.3]),
            intensity=np.asarray([2.0, 4.0, 3.0]),
            analysis=SimpleNamespace(),
            parameters={"data_quality_report": {"source_id": f"frame-{index}", "raw_data_ref": path}},
            source_path=path,
        )
        for index, (temperature, path) in enumerate(zip((20.0, 30.0), paths))
    )
    result = TempSeriesResult(
        temperatures=np.asarray([20.0, 30.0]),
        guinier_sequence_evidence={
            "frame_count": 2,
            "frame_source_indices": [1, 0],
            "level": "Trend",
            "reason_codes": [],
            "source_ref": "saxs_temperature.guinier_sequence",
        },
    )
    result.temp_points = [SimpleNamespace(source_index=1), SimpleNamespace(source_index=0)]
    return SimpleNamespace(
        _temperature_result=result,
        _batch_results=[frame.analysis for frame in frames],
        _batch_params=[{} for _ in frames],
        _q_list=[frame.q for frame in frames],
        _I_list=[frame.intensity for frame in frames],
        _conditions=np.asarray([20.0, 30.0]),
        _file_list=list(paths),
        _condition_type="temperature",
        _results=[],
        cfg=SimpleNamespace(
            experiment_type="temperature",
            condition_label="Temperature",
            condition_unit="C",
            scientific_review=review if review is not None else {},
        ),
    )


def test_temperature_1d_review_binds_all_existing_sources_without_changing_roles() -> None:
    engine = _temperature_engine(
        _review_payload(source_refs=("source-0.dat", "source-1.dat"))
    )

    definitions = build_temperature_figure_definitions(engine)
    provenance = definitions[0].recipe["evidence"]["quality_provenance"]

    review = provenance["scientific_review"]
    json.dumps(review, allow_nan=False)
    assert review["allowed"] is True
    assert review["reason"] == "review_accepted"
    assert review["source_refs"] == ["source-0.dat", "source-1.dat"]
    assert [row["source_ref"] for row in review["frame_decisions"]] == list(
        ("source-0.dat", "source-1.dat")
    )
    assert provenance["series_record"]["guinier_sequence_evidence"][
        "frame_source_indices"
    ] == [1, 0]
    assert all(definition.publication_role != "diagnostic" for definition in definitions[:1])


def test_temperature_1d_review_missing_is_visible_and_fail_closed() -> None:
    definitions = build_temperature_figure_definitions(_temperature_engine())

    review = definitions[0].recipe["evidence"]["quality_provenance"]["scientific_review"]

    assert review["allowed"] is False
    assert review["reason"] == "review_missing"


def test_temperature_1d_review_invalid_payload_is_fail_closed() -> None:
    definitions = build_temperature_figure_definitions(
        _temperature_engine({"record_id": "bad", "scope": "saxs.1d", "status": "accepted"})
    )

    review = definitions[0].recipe["evidence"]["quality_provenance"]["scientific_review"]

    assert review["allowed"] is False
    assert review["reason"] == "review_invalid"


def test_temperature_1d_review_partial_source_match_is_fail_closed() -> None:
    definitions = build_temperature_figure_definitions(
        _temperature_engine(_review_payload(source_refs=("source-0.dat",)))
    )

    review = definitions[0].recipe["evidence"]["quality_provenance"]["scientific_review"]

    assert review["allowed"] is False
    assert review["reason"] == "source_mismatch"
    assert review["frame_decisions"][1]["reason"] == "source_mismatch"


def test_temperature_1d_review_wrong_scope_is_fail_closed() -> None:
    definitions = build_temperature_figure_definitions(
        _temperature_engine(
            _review_payload(source_refs=("source-0.dat", "source-1.dat"), scope="saxs.2d")
        )
    )

    review = definitions[0].recipe["evidence"]["quality_provenance"]["scientific_review"]

    assert review["allowed"] is False
    assert review["reason"] == "scope_mismatch"
