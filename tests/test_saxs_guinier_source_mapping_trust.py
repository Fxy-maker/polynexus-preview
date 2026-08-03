from __future__ import annotations

import json

import pytest

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    QualityLevel,
    build_guinier_sequence_evidence,
    contract_json,
)


def _frame(rg_nm: float, level: str = "Quantitative") -> dict[str, object]:
    return {"rg_nm": rg_nm, "level": level}


def test_complete_valid_mapping_is_emitted_for_frame_and_pair_evidence() -> None:
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0],
        [_frame(4.0), _frame(4.2)],
        source_indices=[7, 3],
    )

    assert evidence.frame_source_indices == (7, 3)
    assert evidence.relative_change_stats["frame_source_indices"] == (7, 3)
    assert evidence.relative_change_stats["pair_source_indices"] == ((7, 3),)
    assert evidence.level is QualityLevel.TREND


@pytest.mark.parametrize(
    ("source_indices", "field", "reason"),
    [
        ([7, 7], "duplicate_source_index_indices", "guinier_sequence_source_index_duplicate"),
        ([True, 3], "invalid_source_index_indices", "guinier_sequence_source_index_invalid"),
        ([float("inf"), 3], "invalid_source_index_indices", "guinier_sequence_source_index_invalid"),
        ([1.5, 3], "invalid_source_index_indices", "guinier_sequence_source_index_invalid"),
        (["bad", 3], "invalid_source_index_indices", "guinier_sequence_source_index_invalid"),
        ([7], "invalid_source_index_indices", "guinier_sequence_source_index_mismatch"),
    ],
)
def test_defective_mapping_is_diagnostic_but_not_trusted(
    source_indices: list[object], field: str, reason: str
) -> None:
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0],
        [_frame(4.0), _frame(4.2)],
        source_indices=source_indices,
    )

    if reason != "guinier_sequence_source_index_mismatch":
        assert getattr(evidence, field)
    assert reason in evidence.reason_codes
    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert evidence.frame_source_indices == ()
    assert evidence.relative_change_stats["frame_source_indices"] == ()
    assert evidence.relative_change_stats["pair_source_indices"] == ()


def test_omitted_mapping_stays_empty_and_round_trips_strict_json() -> None:
    evidence = build_guinier_sequence_evidence(
        [170.0, 180.0], [_frame(4.0), _frame(4.2)]
    )

    payload = json.loads(contract_json(evidence))
    assert evidence.frame_source_indices == ()
    assert payload["frame_source_indices"] == []
    assert payload["relative_change_stats"]["pair_source_indices"] == []
