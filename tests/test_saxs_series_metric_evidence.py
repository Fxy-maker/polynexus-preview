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
