from __future__ import annotations

import json

import numpy as np

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    GuinierSequenceEvidence,
    QualityLevel,
    build_guinier_sequence_evidence,
    contract_json,
)


def _frame(rg_nm: float, level: str = "Quantitative") -> dict:
    return {"rg_nm": rg_nm, "level": level}


def test_two_valid_frames_produce_trend_without_quantitative_upgrade():
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_ref="synthetic"
    )

    assert evidence.level is QualityLevel.TREND
    assert evidence.valid_frame_count == 2
    assert evidence.missing_frame_indices == ()
    assert evidence.metric is not None
    assert evidence.metric.metric_name == "Rg_sequence"
    assert evidence.metric.level is QualityLevel.TREND


def test_empty_and_single_frame_sequences_are_not_trends():
    empty = build_guinier_sequence_evidence([], [])
    single = build_guinier_sequence_evidence([170.0], [_frame(4.0)])

    assert empty.level is QualityLevel.UNUSABLE
    assert "guinier_sequence_no_valid_frames" in empty.reason_codes
    assert single.level is QualityLevel.DIAGNOSTIC
    assert "guinier_sequence_insufficient_frames" in single.reason_codes


def test_missing_and_diagnostic_frames_keep_their_input_positions():
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0, 190.0],
        [_frame(4.0), None, _frame(4.5, "Diagnostic")],
    )

    assert evidence.valid_frame_count == 1
    assert evidence.missing_frame_indices == (1,)
    assert evidence.diagnostic_frame_indices == (2,)
    assert "guinier_sequence_missing_frames" in evidence.reason_codes


def test_invalid_and_duplicate_temperature_positions_are_diagnostic():
    evidence = build_guinier_sequence_evidence(
        [170.0, 170.0, np.nan, 200.0],
        [_frame(4.0), _frame(4.1), _frame(4.2), _frame(4.3)],
    )

    assert evidence.invalid_temperature_indices == (2,)
    assert evidence.duplicate_temperature_indices == (0, 1)
    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert "guinier_sequence_temperature_axis_invalid" in evidence.reason_codes


def test_steady_monotonic_rg_change_is_not_marked_as_an_outlier():
    evidence = build_guinier_sequence_evidence(
        np.arange(170.0, 240.0, 10.0),
        [_frame(value) for value in (4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0)],
    )

    assert evidence.level is QualityLevel.TREND
    assert evidence.continuity_break_indices == ()


def test_isolated_rg_jump_is_diagnostic_evidence_without_frame_deletion():
    evidence = build_guinier_sequence_evidence(
        np.arange(170.0, 240.0, 10.0),
        [_frame(value) for value in (4.0, 4.1, 4.2, 9.0, 4.3, 4.4, 4.5)],
    )

    assert evidence.level is QualityLevel.TREND
    assert evidence.continuity_break_indices == (3,)
    assert "guinier_sequence_continuity_break" in evidence.reason_codes
    assert evidence.valid_frame_count == 7


def test_sequence_evidence_is_strict_json_serializable():
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)]
    )

    payload = json.loads(contract_json(evidence))

    assert payload["level"] == "Trend"
    assert payload["metric"]["metric_name"] == "Rg_sequence"
    assert payload["relative_change_stats"]["relative_change_median"] is not None
    assert payload["relative_change_stats"]["local_deviation_threshold"] is None


def test_sequence_evidence_round_trips_from_json_safe_payload():
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)], source_ref="synthetic"
    )

    restored = GuinierSequenceEvidence.from_dict(evidence.to_dict())

    assert restored.level is QualityLevel.TREND
    assert restored.source_ref == "synthetic"
    assert restored.valid_frame_count == evidence.valid_frame_count
    assert restored.metric is not None
    assert restored.metric.metric_name == "Rg_sequence"
