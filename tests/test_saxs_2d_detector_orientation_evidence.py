from __future__ import annotations

import json

import numpy as np

from polynexus.core.saxs_engine.saxs_quality_contracts import (
    QualityLevel,
    build_detector_quality_report,
    build_orientation_evidence,
    contract_json,
)
from polynexus.core.saxs_engine.saxs_anisotropy import analyze_anisotropy


def _orientation_payload() -> dict:
    return {
        "f_herman": 0.6,
        "P2": 0.6,
        "P4": 0.1,
        "pattern_type": "fiber",
        "anisotropy_ratio": 2.0,
        "anisotropy_index": 0.3,
        "confidence": 0.85,
    }


def test_detector_report_counts_explicit_mask_and_saturation_without_guessing():
    image = np.asarray([[1.0, 2.0, 100.0], [3.0, np.nan, 4.0]])
    mask = np.asarray([[False, True, False], [False, False, False]])

    report = build_detector_quality_report(
        image,
        mask=mask,
        saturation_value=100.0,
        source_kind="raw_detector",
        beam_center=(1.0, 0.0),
    )

    assert report.source_kind == "raw_detector"
    assert report.pixel_count == 6
    assert report.masked_pixel_count == 1
    assert report.nonfinite_pixel_count == 1
    assert report.saturated_pixel_count == 1
    assert report.saturation_detection_available is True
    assert report.beam_center_available is True
    assert report.level is QualityLevel.DIAGNOSTIC


def test_sector_map_without_saturation_metadata_is_not_claimed_as_raw_quality():
    report = build_detector_quality_report(
        np.ones((4, 4)), source_kind="sector_map", beam_center=None
    )

    assert report.source_kind == "sector_map"
    assert report.saturation_detection_available is False
    assert report.saturated_pixel_count == 0
    assert report.level is QualityLevel.DIAGNOSTIC
    assert "detector_saturation_unknown" in report.reason_codes


def test_supported_orientation_evidence_is_trend_and_references_detector_report():
    detector = build_detector_quality_report(
        np.ones((4, 4)), source_kind="raw_detector", beam_center=(2.0, 2.0)
    )

    evidence = build_orientation_evidence(
        _orientation_payload(), detector, applicability="supported", source_ref="synthetic"
    )

    assert evidence.level is QualityLevel.TREND
    assert evidence.metric_name == "Orientation"
    assert evidence.applicable is True
    assert evidence.physical_checks["detector_source_kind"] == "raw_detector"
    assert evidence.fit_evidence["pattern_type"] == "fiber"


def test_orientation_unknown_or_missing_evidence_degrades_without_fabrication():
    detector = build_detector_quality_report(
        np.ones((4, 4)), source_kind="sector_map"
    )
    unknown = build_orientation_evidence(_orientation_payload(), detector)
    missing = build_orientation_evidence({}, detector, applicability="supported")

    assert unknown.level is QualityLevel.DIAGNOSTIC
    assert any("applicability_unresolved" in reason for reason in unknown.reason_codes)
    assert missing.level is QualityLevel.UNUSABLE
    assert "orientation_metrics_missing" in missing.reason_codes


def test_detector_and_orientation_evidence_are_strict_json_safe():
    detector = build_detector_quality_report(
        np.ones((3, 3)), source_kind="raw_detector", saturation_value=10.0
    )
    evidence = build_orientation_evidence(
        _orientation_payload(), detector, applicability="supported"
    )

    detector_payload = json.loads(contract_json(detector))
    evidence_payload = json.loads(contract_json(evidence))

    assert detector_payload["pixel_count"] == 9
    assert evidence_payload["metric_name"] == "Orientation"


def test_anisotropy_result_keeps_legacy_empty_path_and_attaches_json_evidence():
    result = analyze_anisotropy(
        None,
        np.asarray([]),
        np.asarray([]),
        np.asarray([]),
        np.asarray([]),
    )

    assert result.confidence == 0.0
    assert result.detector_quality_report["source_kind"] == "sector_map"
    assert result.orientation_evidence["level"] == QualityLevel.UNUSABLE.value
    json.dumps(result.detector_quality_report, allow_nan=False)
    json.dumps(result.orientation_evidence, allow_nan=False)
