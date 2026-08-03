from __future__ import annotations

import json

import pytest

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    MetricEvidenceSummary,
    build_series_metric_evidence,
)


def _frames(count: int = 2) -> list[dict[str, dict[str, str]]]:
    return [{"porod": {"level": "Trend"}} for _ in range(count)]


def test_valid_reordered_mapping_is_recorded_without_downgrade():
    summary = build_series_metric_evidence(
        _frames(), metric_names=("porod",), frame_source_indices=[1, 0]
    )["porod"]

    assert summary["frame_source_indices"] == [1, 0]
    assert summary["source_index_order_reordered"] is True
    assert summary["duplicate_source_index_indices"] == []
    assert summary["invalid_source_index_indices"] == []
    assert summary["level"] == "Trend"
    assert "series_metric_source_index_invalid" not in summary["reason_codes"]


@pytest.mark.parametrize(
    ("source_indices", "reason", "field", "positions"),
    [
        ([0, 0], "series_metric_source_index_duplicate", "duplicate_source_index_indices", [0, 1]),
        ([-1, 1], "series_metric_source_index_invalid", "invalid_source_index_indices", [0]),
        ([0, 1.5], "series_metric_source_index_invalid", "invalid_source_index_indices", [1]),
        ([0, True], "series_metric_source_index_invalid", "invalid_source_index_indices", [1]),
        ([0, float("nan")], "series_metric_source_index_invalid", "invalid_source_index_indices", [1]),
        ([0, float("inf")], "series_metric_source_index_invalid", "invalid_source_index_indices", [1]),
        ([0, "not-an-index"], "series_metric_source_index_invalid", "invalid_source_index_indices", [1]),
    ],
)
def test_invalid_source_mapping_is_diagnostic_and_untrusted(
    source_indices, reason, field, positions
):
    summary = build_series_metric_evidence(
        _frames(), metric_names=("porod",), frame_source_indices=source_indices
    )["porod"]

    assert summary["frame_source_indices"] == []
    assert summary[field] == positions
    assert reason in summary["reason_codes"]
    assert summary["level"] == "Diagnostic"
    assert summary["applicable"] is False


def test_source_mapping_length_mismatch_is_diagnostic_and_untrusted():
    summary = build_series_metric_evidence(
        _frames(), metric_names=("porod",), frame_source_indices=[4]
    )["porod"]

    assert summary["frame_source_indices"] == []
    assert summary["duplicate_source_index_indices"] == []
    assert summary["invalid_source_index_indices"] == []
    assert "series_metric_source_index_mismatch" in summary["reason_codes"]
    assert summary["level"] == "Diagnostic"


def test_missing_source_mapping_keeps_existing_metric_contract():
    summary = build_series_metric_evidence(_frames(), metric_names=("porod",))["porod"]

    assert summary["frame_source_indices"] == []
    assert summary["source_index_order_reordered"] is False
    assert summary["duplicate_source_index_indices"] == []
    assert summary["invalid_source_index_indices"] == []
    assert summary["level"] == "Trend"
    assert not any("source_index" in reason for reason in summary["reason_codes"])


def test_source_integrity_fields_round_trip_as_strict_json():
    summary = build_series_metric_evidence(
        _frames(), metric_names=("porod",), frame_source_indices=[2, 1]
    )["porod"]

    restored = MetricEvidenceSummary.from_dict(summary)
    assert restored.source_index_order_reordered is True
    assert restored.duplicate_source_index_indices == ()
    assert restored.invalid_source_index_indices == ()
    json.dumps(restored.to_dict(), allow_nan=False, sort_keys=True)
