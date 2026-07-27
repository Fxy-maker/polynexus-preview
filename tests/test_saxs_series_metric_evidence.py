import json

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    MetricEvidenceSummary,
    QualityLevel,
    build_series_metric_evidence,
)


def test_complete_two_frame_series_is_trend_and_strict_json_safe():
    frames = [
        {"porod": {"level": "Quantitative"}},
        {"porod": {"level": "Trend"}},
    ]

    summary = build_series_metric_evidence(
        frames, metric_names=("porod",), source_ref="temperature.metric_evidence"
    )["porod"]

    restored = MetricEvidenceSummary.from_dict(summary)
    assert restored.level is QualityLevel.TREND
    assert summary["frame_count"] == 2
    assert summary["evidence_frame_count"] == 2
    assert summary["usable_frame_count"] == 2
    assert summary["coverage_fraction"] == 1.0
    assert summary["applicable"] is True
    assert "series_level_capped_at_trend" in summary["reason_codes"]
    json.dumps(summary, allow_nan=False, sort_keys=True)


def test_missing_and_diagnostic_frames_are_preserved_as_diagnostic():
    frames = [
        {"porod": {"level": "Trend"}},
        None,
        {"porod": {"level": "Diagnostic"}},
    ]

    summary = build_series_metric_evidence(
        frames, metric_names=("porod",), source_ref="strain.metric_evidence"
    )["porod"]

    assert summary["level"] == "Diagnostic"
    assert summary["applicable"] is False
    assert summary["missing_frame_count"] == 1
    assert summary["diagnostic_frame_count"] == 1
    assert summary["coverage_fraction"] == 2 / 3
    assert "series_metric_missing_frames" in summary["reason_codes"]
    assert "series_metric_diagnostic_frames" in summary["reason_codes"]


def test_empty_or_unknown_series_is_unusable_without_nan():
    summaries = build_series_metric_evidence(
        [{"porod": {"level": "not-a-level"}}],
        metric_names=("porod", "kratky"),
    )

    assert summaries["porod"]["level"] == "Unusable"
    assert summaries["kratky"]["level"] == "Unusable"
    assert summaries["kratky"]["coverage_fraction"] == 0.0
    assert "series_metric_missing_all_frames" in summaries["kratky"]["reason_codes"]
    assert "series_metric_invalid_level" in summaries["porod"]["reason_codes"]
    json.dumps(summaries, allow_nan=False)


def test_empty_series_is_unusable_and_has_no_nan_coverage():
    summary = build_series_metric_evidence(
        [], metric_names=("porod",), source_ref="empty.metric_evidence"
    )["porod"]

    assert summary["level"] == "Unusable"
    assert summary["frame_count"] == 0
    assert summary["coverage_fraction"] is None
    assert summary["applicable"] is False
    assert "series_no_frames" in summary["reason_codes"]


def test_series_summary_records_positions_and_source_indices():
    frames = [
        {"porod": {"level": "Quantitative"}},
        None,
        {"porod": {"level": "Diagnostic"}},
        {"porod": {"level": "Unusable"}},
    ]

    summary = build_series_metric_evidence(
        frames,
        metric_names=("porod",),
        frame_source_indices=[7, 2, 5, 9],
    )["porod"]

    assert summary["evidence_frame_indices"] == [0, 2, 3]
    assert summary["missing_frame_indices"] == [1]
    assert summary["diagnostic_frame_indices"] == [2]
    assert summary["unusable_frame_indices"] == [3]
    assert summary["invalid_level_indices"] == []
    assert summary["frame_source_indices"] == [7, 2, 5, 9]


def test_series_summary_records_invalid_level_position_and_round_trips():
    summary = build_series_metric_evidence(
        [{"porod": {"level": "not-a-level"}}],
        metric_names=("porod",),
    )["porod"]

    assert summary["evidence_frame_indices"] == [0]
    assert summary["invalid_level_indices"] == [0]
    assert summary["unusable_frame_indices"] == [0]
    restored = MetricEvidenceSummary.from_dict(summary)
    assert restored.invalid_level_indices == (0,)
    json.dumps(restored.to_dict(), allow_nan=False, sort_keys=True)


def test_series_summary_rejects_partial_source_mapping_without_invention():
    summary = build_series_metric_evidence(
        [{"porod": {"level": "Trend"}}, {"porod": {"level": "Trend"}}],
        metric_names=("porod",),
        frame_source_indices=[4],
    )["porod"]

    assert summary["frame_source_indices"] == []
    assert "series_metric_source_index_mismatch" in summary["reason_codes"]


def test_series_summary_records_a_clean_condition_axis_without_changing_level():
    summary = build_series_metric_evidence(
        [{"porod": {"level": "Trend"}}] * 3,
        metric_names=("porod",),
        condition_name="temperature_C",
        condition_values=[170.0, 180.0, 190.0],
    )["porod"]

    axis = summary["condition_axis"]
    assert axis == {
        "condition_name": "temperature_C",
        "condition_values": [170.0, 180.0, 190.0],
        "invalid_condition_indices": [],
        "duplicate_condition_indices": [],
        "nonmonotonic_condition_indices": [],
        "status": "ordered",
    }
    assert summary["level"] == "Trend"
    json.dumps(MetricEvidenceSummary.from_dict(summary).to_dict(), allow_nan=False)


def test_series_summary_preserves_condition_axis_defects_by_position():
    summary = build_series_metric_evidence(
        [{"porod": {"level": "Trend"}}] * 4,
        metric_names=("porod",),
        condition_name="temperature_C",
        condition_values=[170.0, 170.0, 160.0, float("nan")],
    )["porod"]

    axis = summary["condition_axis"]
    assert axis["condition_values"] == [170.0, 170.0, 160.0, None]
    assert axis["invalid_condition_indices"] == [3]
    assert axis["duplicate_condition_indices"] == [0, 1]
    assert axis["nonmonotonic_condition_indices"] == [1, 2]
    assert axis["status"] == "diagnostic"
    assert summary["level"] == "Trend"


def test_series_summary_rejects_partial_condition_axis_without_invention():
    summary = build_series_metric_evidence(
        [{"porod": {"level": "Trend"}}] * 2,
        metric_names=("porod",),
        condition_name="temperature_C",
        condition_values=[170.0],
    )["porod"]

    assert summary["condition_axis"] == {
        "condition_name": "temperature_C",
        "condition_values": [],
        "invalid_condition_indices": [],
        "duplicate_condition_indices": [],
        "nonmonotonic_condition_indices": [],
        "status": "diagnostic",
    }
    assert "series_metric_condition_axis_length_mismatch" in summary["reason_codes"]
