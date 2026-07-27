from __future__ import annotations

import json
from types import SimpleNamespace

from polynexus.core.saxs_engine.saxs_quality_contracts import contract_json
from polynexus.core.saxs_engine.saxs_sequence_rescue import (
    build_sequence_rescue_candidates,
    validate_sequence_rescue_candidate,
)
from polynexus.core.saxs_engine.saxs_temperature import TemperaturePointResult, TempSeriesResult


def _point(**overrides):
    values = {
        "temperature_C": 180.0,
        "lc_nm": 10.0,
        "lc_effective_nm": 10.8,
        "lc_effective_source": "tangent",
        "lc_path_status": "low_confidence",
        "lc_path_reason": "selected=tangent|selection_margin=0.2",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_sequence_candidates_wrap_existing_alternative_without_mutating_frame():
    point = _point()
    candidates = build_sequence_rescue_candidates([point])

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.kind == "deterministic"
    assert candidate.parameters["frame_index"] == 0
    assert candidate.parameters["proposed_source"] == "tangent"
    assert candidate.parameters["preserve_missing_frames"] is True
    assert point.lc_nm == 10.0


def test_sequence_candidates_do_not_fabricate_missing_or_usable_frames():
    candidates = build_sequence_rescue_candidates(
        [_point(lc_effective_nm=10.0, lc_effective_source="primary", lc_path_status="usable"), None]
    )

    assert candidates == ()


def test_rescue_validation_requires_all_hard_gates_and_is_strict_json_safe():
    candidate = build_sequence_rescue_candidates([_point()])[0]
    accepted = validate_sequence_rescue_candidate(
        candidate,
        hard_gate_passed=True,
        physical_gate_passed=True,
        data_preserved=True,
        sequence_gate_passed=True,
        soft_score=0.9,
    )
    rejected = validate_sequence_rescue_candidate(
        candidate,
        hard_gate_passed=True,
        physical_gate_passed=False,
        data_preserved=True,
        sequence_gate_passed=True,
    )

    assert accepted.effective_decision() == "accepted"
    assert rejected.effective_decision() == "rejected"
    assert "physical_gate_failed" in rejected.to_dict()["rejection_reasons"]
    json.loads(contract_json(accepted))


def test_temperature_result_exposes_candidate_id_in_frame_table():
    candidate = build_sequence_rescue_candidates([_point()])[0]
    result = TempSeriesResult(
        temp_points=[TemperaturePointResult(temperature_C=180.0)],
        sequence_rescue_candidates=[candidate.to_dict()],
    )

    table = result.to_dataframe()

    assert table.iloc[0]["sequence_rescue_candidate"] == candidate.candidate_id
