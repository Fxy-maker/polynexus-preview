from __future__ import annotations

import json
from typing import cast

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    AnnulusQualityReport,
    QualityLevel,
    SectorMapQualityReport,
    build_annulus_quality_report,
    build_detector_quality_report,
    build_orientation_evidence,
    build_sector_map_quality_report,
)


def test_support_reports_distinguish_empty_bins_from_intensity_values() -> None:
    intensity = np.asarray([[0.0, 3.0], [0.0, -2.0]])
    support = np.asarray([[0.0, 4.0], [0.0, 2.0]])

    sector = build_sector_map_quality_report(intensity, support)
    annulus = build_annulus_quality_report(
        support,
        np.asarray([0.40, 0.50]),
        q_target=0.50,
        q_width=0.01,
    )

    assert sector.empty_bin_count == 2
    assert sector.measured_nonpositive_bin_count == 1
    assert "sector_empty_bins_present" in sector.reason_codes
    assert "nonpositive_pixels" not in sector.reason_codes
    assert annulus.supported_angular_bin_count == 2
    json.dumps(sector.to_dict(), allow_nan=False)
    json.dumps(annulus.to_dict(), allow_nan=False)


def test_config_keeps_tensile_axis_separate_from_legacy_axis() -> None:
    config = SAXSConfig(orientation_axis_deg=37.0, tensile_axis_deg=90.0)

    assert config.orientation_axis_deg == 37.0
    assert config.tensile_axis_deg == 90.0


def test_support_reports_fail_closed_for_missing_or_mismatched_support() -> None:
    sector = build_sector_map_quality_report(
        np.ones((2, 2)),
        np.ones((1, 2)),
    )
    annulus = build_annulus_quality_report(
        None,
        np.asarray([0.40, 0.50]),
        q_target=0.50,
        q_width=0.01,
    )

    for report in (sector, annulus):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


def test_saxs_engine_package_facade_exports_support_quality_contracts() -> None:
    from polynexus.core import saxs_engine
    from polynexus.core.saxs_engine import (
        AnnulusQualityReport as exported_annulus_report,
        SectorMapQualityReport as exported_sector_report,
        build_annulus_quality_report as exported_annulus_builder,
        build_sector_map_quality_report as exported_sector_builder,
    )

    assert exported_sector_report is SectorMapQualityReport
    assert exported_annulus_report is AnnulusQualityReport
    assert exported_sector_builder is build_sector_map_quality_report
    assert exported_annulus_builder is build_annulus_quality_report
    assert {
        "SectorMapQualityReport",
        "AnnulusQualityReport",
        "build_sector_map_quality_report",
        "build_annulus_quality_report",
    } <= set(saxs_engine.__all__)


def test_sector_report_counts_negative_infinity_only_with_support() -> None:
    report = build_sector_map_quality_report(
        np.asarray([[-np.inf, np.nan, 0.0]]),
        np.asarray([[1.0, 1.0, 0.0]]),
    )

    assert report.measured_nonpositive_bin_count == 1


def test_annulus_quality_widens_q_window_before_counting_support() -> None:
    report = build_annulus_quality_report(
        np.asarray([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        np.asarray([0.44, 0.50, 0.54]),
        q_target=0.50,
        q_width=0.01,
    )

    assert report.selected_q_bin_count == 2
    assert report.supported_angular_bin_count == 2


def test_sector_report_fails_closed_for_negative_support_count() -> None:
    for invalid_support in (-1.0, np.nan, np.inf):
        report = build_sector_map_quality_report(
            np.ones((1, 2)),
            np.asarray([[1.0, invalid_support]]),
        )

        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


def test_annulus_report_fails_closed_for_negative_support_count() -> None:
    for invalid_support in (-1.0, np.nan, np.inf):
        report = build_annulus_quality_report(
            np.asarray([[1.0, invalid_support], [1.0, 1.0]]),
            np.asarray([0.40, 0.50]),
            q_target=0.50,
            q_width=0.01,
        )

        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


def test_orientation_evidence_normalizes_unavailable_support_reports() -> None:
    sector_payload = {
        "shape": [1, 2],
        "support_available": False,
        "reason_codes": ["sector_support_unavailable", "sector_source_missing"],
        "level": "Diagnostic",
    }
    original_sector_payload = json.loads(json.dumps(sector_payload))
    diagnostic_annulus = AnnulusQualityReport(
        support_available=True,
        reason_codes=("annulus_support_incomplete",),
        level="Diagnostic",
    )
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )

    evidence = build_orientation_evidence(
        {"f_herman": 0.4},
        detector,
        applicability="supported",
        sector_map_quality=sector_payload,
        annulus_quality=diagnostic_annulus,
    )

    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert evidence.applicable is False
    assert {"sector_support_unavailable", "sector_source_missing", "annulus_support_incomplete"} <= set(evidence.reason_codes)
    sector_evidence_payload = evidence.physical_checks["sector_map_quality_report"]
    annulus_evidence_payload = evidence.physical_checks["annulus_quality_report"]
    assert sector_evidence_payload is not sector_payload
    assert annulus_evidence_payload is not diagnostic_annulus
    assert sector_evidence_payload["support_available"] is False
    assert annulus_evidence_payload["level"] == "Diagnostic"
    assert "sector_support_unavailable" in sector_evidence_payload["reason_codes"]
    assert "annulus_support_incomplete" in annulus_evidence_payload["reason_codes"]
    assert sector_payload["shape"] == original_sector_payload["shape"]
    assert sector_payload["support_available"] is original_sector_payload["support_available"]
    assert sector_payload["reason_codes"] == original_sector_payload["reason_codes"]
    json.dumps(evidence.to_dict(), allow_nan=False)

    noncanonical_annulus = AnnulusQualityReport(
        support_available=True,
        reason_codes=("annulus_quality_level_invalid",),
        level=cast(QualityLevel, "not-a-quality-level"),
    )
    diagnostic_evidence = build_orientation_evidence(
        {"f_herman": 0.4},
        detector,
        applicability="supported",
        sector_map_quality=build_sector_map_quality_report(
            np.ones((2, 2)), np.ones((2, 2))
        ),
        annulus_quality=noncanonical_annulus,
    )

    assert diagnostic_evidence.level is QualityLevel.DIAGNOSTIC
    assert diagnostic_evidence.applicable is False
    assert "annulus_quality_level_invalid" in diagnostic_evidence.reason_codes
    assert (
        diagnostic_evidence.physical_checks["annulus_quality_report"]["level"]
        == "Unusable"
    )


def test_orientation_evidence_keeps_trend_for_normalized_valid_support_reports() -> None:
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )
    valid_sector = build_sector_map_quality_report(
        np.ones((2, 2)),
        np.ones((2, 2)),
    )
    valid_annulus = build_annulus_quality_report(
        np.ones((2, 2)),
        np.asarray([0.40, 0.50]),
        q_target=0.50,
        q_width=0.01,
    )
    valid = build_orientation_evidence(
        {"f_herman": 0.4},
        detector,
        applicability="supported",
        sector_map_quality=valid_sector.to_dict(),
        annulus_quality=valid_annulus,
    )

    assert valid.level is QualityLevel.TREND
    assert valid.applicable is True
