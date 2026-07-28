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
from polynexus.core.saxs_engine.config import SAXSConfig


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


def test_anisotropy_mismatched_q_axis_fails_closed_with_unusable_evidence():
    I_2d = np.ones((72, 5))
    q = np.linspace(0.1, 1.0, 10)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    q_1d = np.linspace(0.1, 1.0, 10)
    I_1d = np.ones(10)

    result = analyze_anisotropy(I_2d, q, chi, q_1d, I_1d)

    assert not np.isfinite(result.f_herman)
    assert result.orientation_evidence["level"] == QualityLevel.UNUSABLE.value
    assert "orientation_input_shape_mismatch" in result.orientation_evidence["reason_codes"]
    json.dumps(result.detector_quality_report, allow_nan=False)
    json.dumps(result.orientation_evidence, allow_nan=False)


def _synthetic_azimuthal_input(axis_deg: float) -> tuple[np.ndarray, ...]:
    q = np.linspace(0.3, 1.0, 120)
    q_profile = 0.1 + np.exp(-((q - 0.55) / 0.025) ** 2)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    axis = np.deg2rad(axis_deg)
    angular = 1.0 + 8.0 * np.cos(chi - axis) ** 2
    return np.outer(angular, q_profile), q, chi, q, q_profile


def test_anisotropy_prefers_explicit_axis_and_uses_detector_plane_weighting():
    payload = _synthetic_azimuthal_input(90.0)
    result = analyze_anisotropy(*payload, cfg=SAXSConfig(orientation_axis_deg=90.0))

    assert result.orientation_axis_source == "configured"
    assert result.orientation_axis_deg == 90.0
    assert result.f_herman > 0.5
    assert result.orientation_evidence["fit_evidence"]["orientation_axis_source"] == "configured"
    json.dumps(result.orientation_evidence, allow_nan=False)


def test_anisotropy_auto_detects_arbitrary_in_plane_axis():
    payload = _synthetic_azimuthal_input(37.0)
    result = analyze_anisotropy(
        *payload,
        cfg=SAXSConfig(
            orientation_axis_deg=None,
            orientation_auto_min_strength=0.05,
        ),
    )

    assert result.orientation_axis_source == "auto_detected"
    assert abs(((result.orientation_axis_deg - 37.0 + 90.0) % 180.0) - 90.0) < 5.0
    assert result.orientation_axis_strength > 0.05
    assert result.f_herman > 0.5
    json.dumps(result.orientation_evidence, allow_nan=False)


def test_anisotropy_auto_detection_fails_closed_for_isotropic_profile():
    q = np.linspace(0.3, 1.0, 120)
    q_profile = 0.1 + np.exp(-((q - 0.55) / 0.025) ** 2)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    I_2d = np.outer(np.ones_like(chi), q_profile)

    result = analyze_anisotropy(
        I_2d,
        q,
        chi,
        q,
        q_profile,
        cfg=SAXSConfig(orientation_axis_deg=None),
    )

    assert result.orientation_axis_source == "unavailable"
    assert not np.isfinite(result.f_herman)
    assert "orientation_axis_low_strength" in result.orientation_evidence["reason_codes"]
