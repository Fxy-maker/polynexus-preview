from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from polynexus.core.saxs_engine.saxs_quality_contracts import contract_json
from polynexus.core.saxs_engine.saxs_sequence_rescue import (
    build_sequence_rescue_candidates,
    resolve_sequence_rescue_candidate,
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


def test_sequence_reference_resolves_one_detached_existing_candidate():
    candidate = build_sequence_rescue_candidates([_point()])[0]

    resolved = resolve_sequence_rescue_candidate(
        [candidate.to_dict()],
        candidate.candidate_id,
    )

    assert resolved is not None
    assert resolved is not candidate
    assert resolved.candidate_id == candidate.candidate_id
    assert resolved.kind == "deterministic"
    assert resolved.source == "saxs_temperature.select_lc_sequence_path"
    assert resolved.parameters["axis_name"] == "temperature"
    assert resolved.parameters["metric"] == "lc_nm"
    assert resolved.parameters["apply_mode"] == "candidate_only"
    assert resolved.parameters["preserve_missing_frames"] is True
    assert resolved.requires_validation is True


@pytest.mark.parametrize(
    "mutator",
    [
        lambda payload: payload.update({"kind": "ai"}),
        lambda payload: payload.pop("source"),
        lambda payload: payload["parameters"].update({"apply_mode": "validated"}),
        lambda payload: payload["parameters"].update({"preserve_missing_frames": False}),
    ],
)
def test_sequence_reference_rejects_untrusted_candidate_identity(mutator):
    candidate = build_sequence_rescue_candidates([_point()])[0]
    payload = candidate.to_dict()
    mutator(payload)

    assert resolve_sequence_rescue_candidate([payload], candidate.candidate_id) is None


@pytest.mark.parametrize(
    ("candidate_id", "mode"),
    [
        ("", "temperature"),
        ("unknown", "temperature"),
        ("temperature-frame-0-lc-tangent", "static"),
    ],
)
def test_sequence_reference_rejects_empty_unknown_or_unsupported_request(
    candidate_id, mode
):
    candidate = build_sequence_rescue_candidates([_point()])[0]

    assert resolve_sequence_rescue_candidate(
        [candidate.to_dict()],
        candidate_id,
        mode=mode,
    ) is None


def test_sequence_reference_rejects_ambiguous_duplicate_ids():
    candidate = build_sequence_rescue_candidates([_point()])[0]

    assert resolve_sequence_rescue_candidate(
        [candidate.to_dict(), candidate.to_dict()],
        candidate.candidate_id,
    ) is None


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
