from __future__ import annotations

import json
from dataclasses import fields
from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.preprocess import integrate_chi_sectors
from polynexus.core.saxs_engine.saxs_anisotropy import analyze_anisotropy
from polynexus.core.saxs_engine.saxs_strain import analyze_strain_series
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    AnnulusQualityReport,
    QualityLevel,
    SectorMapQualityReport,
    build_annulus_quality_report,
    build_detector_quality_report,
    build_orientation_evidence,
    build_sector_map_quality_report,
)


def _synthetic_annulus_input(axis_deg: float = 37.0) -> tuple[np.ndarray, ...]:
    q = np.linspace(0.3, 1.0, 120)
    q_profile = 0.1 + np.exp(-((q - 0.55) / 0.025) ** 2)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    angular = 1.0 + 8.0 * np.cos(chi - np.deg2rad(axis_deg)) ** 2
    return np.outer(angular, q_profile), q, chi, q, q_profile


def test_effective_herman_requires_explicit_tensile_axis() -> None:
    payload = _synthetic_annulus_input()
    raw = build_detector_quality_report(
        np.ones((16, 16)), source_kind="raw_detector", beam_center=(8.0, 8.0)
    )

    result = analyze_anisotropy(
        *payload,
        cfg=SAXSConfig(tensile_axis_deg=None),
        support_count=np.ones_like(payload[0]),
        raw_detector_quality=raw.to_dict(),
    )

    assert np.isfinite(result.f_herman_raw)
    assert not np.isfinite(result.f_herman)
    assert not np.isfinite(result.P2)
    assert not np.isfinite(result.P4)
    assert np.isfinite(result.principal_scattering_axis_deg)
    assert result.reference_axis_kind == "unknown"
    assert result.herman_convention == "detector_plane_2d_v1"
    assert result.isotropic_baseline == 0.25
    assert result.orientation_evidence["fit_evidence"]["reference_axis_kind"] == "unknown"
    assert "tensile_axis_unknown" in result.orientation_evidence["reason_codes"]


def test_strain_missing_tensile_axis_preserves_raw_but_not_final_herman() -> None:
    I_2d, q, chi, _q_1d, intensity = _synthetic_annulus_input()
    sector_data = {
        "I_2d": I_2d,
        "q_2d": q,
        "chi_rad": chi,
        "I_full": intensity,
        "support_count": np.ones_like(I_2d),
    }

    result = analyze_strain_series(
        [0.0], [q], [intensity], sector_data_list=[sector_data],
        cfg=SAXSConfig(smooth_method="none", tensile_axis_deg=None),
    )

    point = result.strain_points[0]
    assert np.isfinite(point.f_herman_raw)
    assert not np.isfinite(point.f_herman)
    assert "tensile_axis_unknown" in point.orientation_evidence["reason_codes"]


def test_supported_annulus_uses_tensile_axis_and_ignores_empty_bins_outside_band() -> None:
    payload = _synthetic_annulus_input()
    support = np.ones_like(payload[0])
    support[:, :5] = 0.0
    raw = build_detector_quality_report(
        np.ones((16, 16)), source_kind="raw_detector", beam_center=None
    )

    result = analyze_anisotropy(
        *payload,
        cfg=SAXSConfig(tensile_axis_deg=37.0),
        support_count=support,
        raw_detector_quality=raw,
    )

    checks = result.orientation_evidence["physical_checks"]
    assert result.f_herman > 0.5
    assert result.reference_axis_deg == 37.0
    assert result.reference_axis_kind == "tensile_axis"
    assert checks["sector_map_quality_report"]["empty_bin_count"] == 360
    assert checks["annulus_quality_report"]["support_available"] is True
    assert checks["annulus_quality_report"]["level"] == "Trend"
    assert result.detector_quality_report["source_kind"] == "raw_detector"
    assert result.detector_quality_report["level"] == "Diagnostic"
    assert "nonpositive_pixels" not in result.orientation_evidence["reason_codes"]
    json.dumps(result.orientation_evidence, allow_nan=False)


def test_omitted_raw_report_does_not_promote_sector_bins_to_detector_defects() -> None:
    I_2d, q, chi, q_1d, I_1d = _synthetic_annulus_input()
    I_2d = np.array(I_2d, copy=True)
    I_2d[:, :5] = 0.0

    result = analyze_anisotropy(
        I_2d,
        q,
        chi,
        q_1d,
        I_1d,
        cfg=SAXSConfig(tensile_axis_deg=37.0),
        support_count=np.ones_like(I_2d),
    )

    report = result.detector_quality_report
    assert report["source_kind"] == "raw_detector"
    assert report["level"] == "Diagnostic"
    assert "raw_detector_quality_unavailable" in report["reason_codes"]
    assert "nonpositive_pixels" not in report["reason_codes"]
    json.dumps(report, allow_nan=False)


def test_sparse_annulus_support_blocks_final_herman_and_is_json_safe() -> None:
    payload = _synthetic_annulus_input()
    support = np.zeros_like(payload[0])
    support[0, np.abs(payload[1] - 0.55) <= 0.02] = 1.0

    result = analyze_anisotropy(
        *payload,
        cfg=SAXSConfig(tensile_axis_deg=37.0),
        support_count=support,
    )

    annulus = result.orientation_evidence["physical_checks"][
        "annulus_quality_report"
    ]
    assert annulus["support_fraction"] == pytest.approx(1.0 / 72.0)
    assert "annulus_support_insufficient" in result.orientation_evidence["reason_codes"]
    assert not np.isfinite(result.f_herman)
    assert not np.isfinite(result.P2)
    assert not np.isfinite(result.P4)
    assert result.orientation_reliability_status != "usable"
    json.dumps(result.orientation_evidence, allow_nan=False)


def test_observed_principal_axis_is_not_overwritten_by_legacy_reference_axis() -> None:
    payload = _synthetic_annulus_input(axis_deg=37.0)

    result = analyze_anisotropy(
        *payload,
        cfg=SAXSConfig(orientation_axis_deg=90.0, tensile_axis_deg=37.0),
        support_count=np.ones_like(payload[0]),
    )

    fit = result.orientation_evidence["fit_evidence"]
    assert abs(((result.principal_scattering_axis_deg - 37.0 + 90.0) % 180.0) - 90.0) < 5.0
    assert result.orientation_axis_deg == 90.0
    assert result.orientation_axis_source == "configured"
    assert fit["raw_reference_axis_deg"] == 90.0
    assert fit["raw_reference_axis_kind"] == "legacy_configured_axis"
    assert abs(((fit["principal_scattering_axis_deg"] - 37.0 + 90.0) % 180.0) - 90.0) < 5.0
    assert result.f_herman_raw != result.f_herman
    assert result.reference_axis_deg == 37.0


def test_diagnostic_raw_nonpositive_pixels_do_not_automatically_veto_final_herman() -> None:
    payload = _synthetic_annulus_input(axis_deg=37.0)
    raw = build_detector_quality_report(
        np.asarray([[1.0, 0.0], [1.0, 1.0]]),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )

    result = analyze_anisotropy(
        *payload,
        cfg=SAXSConfig(tensile_axis_deg=37.0),
        support_count=np.ones_like(payload[0]),
        raw_detector_quality=raw,
    )

    assert raw.level is QualityLevel.DIAGNOSTIC
    assert "nonpositive_pixels" in raw.reason_codes
    assert np.isfinite(result.f_herman)
    assert "detector_quality_diagnostic" in result.orientation_evidence["reason_codes"]
    assert "raw_detector_quality_unusable" not in result.orientation_evidence[
        "reason_codes"
    ]
    json.dumps(result.orientation_evidence, allow_nan=False)


def test_numpy_sector_map_preserves_zero_support_separately_from_intensity() -> None:
    cfg = SAXSConfig(q_min=0.01, q_max=5.0, n_pt=8, n_chi_sectors=12)
    image = np.ones((32, 32), dtype=float)
    image[0, 0] = -1.5

    sector_map = integrate_chi_sectors(None, image, cfg)

    assert sector_map.intensity.shape == (12, 8)
    assert sector_map.support_count.shape == sector_map.intensity.shape
    assert np.array_equal(sector_map.empty_bin_mask, sector_map.support_count == 0)
    assert np.any(sector_map.empty_bin_mask)
    q, intensity, chi = sector_map
    assert q is sector_map.q
    assert intensity is sector_map.intensity
    assert chi is sector_map.chi


def test_sector_map_preserves_legacy_tuple_length_indexing_and_errors() -> None:
    result = integrate_chi_sectors(
        None,
        np.ones((32, 32), dtype=float),
        SAXSConfig(q_min=0.01, q_max=5.0, n_pt=8, n_chi_sectors=12),
    )

    assert len(result) == 3
    assert result[0] is result.q
    assert result[1] is result.intensity
    assert result[2] is result.chi
    legacy_view = result[0:3]
    assert isinstance(legacy_view, tuple)
    assert legacy_view[0] is result.q
    assert legacy_view[1] is result.intensity
    assert legacy_view[2] is result.chi
    with pytest.raises(IndexError):
        result[3]


def test_pyfai_sector_map_reorders_valid_count_with_intensity() -> None:
    class FakeAI:
        def integrate2d(self, *_args, **_kwargs):
            return SimpleNamespace(
                intensity=np.asarray([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]),
                radial=np.asarray([0.2, 0.3]),
                azimuthal=np.asarray([90.0, -90.0, 0.0]),
                count=np.asarray([[0.5, 2.0], [3.25, 4.0], [5.0, 6.75]]),
            )

    result = integrate_chi_sectors(
        FakeAI(), np.ones((8, 8)), SAXSConfig(n_pt=2, n_chi_sectors=3)
    )

    assert result.integration_backend == "pyfai"
    assert np.array_equal(result.chi, np.deg2rad([-90.0, 0.0, 90.0]))
    assert np.array_equal(result.intensity, [[3.0, 4.0], [5.0, 6.0], [1.0, 2.0]])
    assert np.array_equal(result.support_count, [[3.25, 4.0], [5.0, 6.75], [0.5, 2.0]])


def test_pyfai_sector_map_fails_closed_when_count_attribute_is_absent() -> None:
    class FakeAI:
        def integrate2d(self, *_args, **_kwargs):
            return SimpleNamespace(
                intensity=np.ones((3, 2)),
                radial=np.asarray([0.2, 0.3]),
                azimuthal=np.asarray([0.0, 1.0, 2.0]),
            )

    result = integrate_chi_sectors(
        FakeAI(), np.ones((8, 8)), SAXSConfig(n_pt=2, n_chi_sectors=3)
    )

    assert result.support_count is None
    assert result.empty_bin_mask is None


def test_pyfai_sector_map_fails_closed_for_invalid_count_payloads() -> None:
    class FakeAI:
        def __init__(self, count):
            self.count = count

        def integrate2d(self, *_args, **_kwargs):
            return SimpleNamespace(
                intensity=np.ones((3, 2)),
                radial=np.asarray([0.2, 0.3]),
                azimuthal=np.asarray([0.0, 1.0, 2.0]),
                count=self.count,
            )

    invalid_counts = (
        None,
        [[1.0, 1.0], [1.0]],
        np.ones((2, 3)),
        np.ones(6),
        np.asarray([[1.0, np.nan], [1.0, 1.0], [1.0, 1.0]]),
        np.asarray([[1.0, -1.0], [1.0, 1.0], [1.0, 1.0]]),
        np.asarray([[True, False], [True, True], [True, True]]),
        [[True, 1.0], [1.0, 1.0], [1.0, 1.0]],
        np.asarray([["1.0", "1.0"], ["1.0", "1.0"], ["1.0", "1.0"]]),
        np.asarray([[1.0 + 0.0j, 1.0 + 0.0j], [1.0 + 0.0j, 1.0 + 0.0j], [1.0 + 0.0j, 1.0 + 0.0j]]),
    )

    for count in invalid_counts:
        result = integrate_chi_sectors(
            FakeAI(count), np.ones((8, 8)), SAXSConfig(n_pt=2, n_chi_sectors=3)
        )
        assert result.support_count is None
        assert result.empty_bin_mask is None


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


def test_config_preserves_preexisting_positional_arguments_after_orientation_axis() -> None:
    defaults = SAXSConfig()
    legacy_values = [
        getattr(defaults, item.name)
        for item in fields(SAXSConfig)
        if item.name != "tensile_axis_deg"
    ]
    legacy_values[30:38] = [37.0, 0.12, 13, 2.5, 0.8, 9.0, 21.0, -1.2]

    config = SAXSConfig(*legacy_values)

    assert config.orientation_axis_deg == 37.0
    assert config.orientation_auto_min_strength == 0.12
    assert config.orientation_auto_min_bins == 13
    assert config.orientation_auto_min_significance == 2.5
    assert config.orientation_min_coverage == 0.8
    assert config.orientation_min_effective_bins == 9.0
    assert config.orientation_max_axis_drift_deg == 21.0
    assert config.dummy_val == -1.2
    assert config.tensile_axis_deg is None


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


def test_sector_report_fails_closed_for_zero_sized_map_and_support() -> None:
    report = build_sector_map_quality_report(
        np.empty((0, 0)),
        np.empty((0, 0)),
    )

    assert report.support_available is False
    assert report.level is QualityLevel.DIAGNOSTIC
    assert "sector_support_unavailable" in report.reason_codes


def test_detached_support_reports_fail_closed_for_malformed_fields() -> None:
    sector = SectorMapQualityReport.from_dict(
        {
            "shape": [1, 2],
            "support_available": "false",
            "supported_bin_count": 2,
            "empty_bin_count": 0,
            "measured_nonpositive_bin_count": 0,
            "support_fraction": 1.0,
            "reason_codes": [],
            "level": "Trend",
        }
    )
    annulus = AnnulusQualityReport.from_dict(
        {
            "q_target_nm1": 0.5,
            "q_width_nm1": 0.1,
            "selected_q_bin_count": "two",
            "angular_bin_count": 2,
            "supported_angular_bin_count": 2,
            "support_fraction": 1.0,
            "support_available": True,
            "reason_codes": [],
            "level": "Trend",
        }
    )

    for report in (sector, annulus):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes
        json.dumps(report.to_dict(), allow_nan=False)


def test_detached_support_reports_canonicalize_invalid_shape_counts_and_q_fields() -> None:
    sector = SectorMapQualityReport.from_dict(
        {
            "shape": "not-a-shape",
            "support_available": True,
            "supported_bin_count": "many",
            "empty_bin_count": [4],
            "measured_nonpositive_bin_count": -1,
            "support_fraction": "full",
            "reason_codes": [],
            "level": "Trend",
        }
    )
    annulus = AnnulusQualityReport.from_dict(
        {
            "q_target_nm1": [0.5],
            "q_width_nm1": "narrow",
            "selected_q_bin_count": "one",
            "angular_bin_count": [2],
            "supported_angular_bin_count": "two",
            "support_fraction": "half",
            "support_available": True,
            "reason_codes": [],
            "level": "Trend",
        }
    )

    assert sector.shape == ()
    assert sector.supported_bin_count == 0
    assert sector.empty_bin_count == 0
    assert sector.measured_nonpositive_bin_count == 0
    assert sector.support_fraction is None
    assert annulus.q_target_nm1 is None
    assert annulus.q_width_nm1 is None
    assert annulus.selected_q_bin_count == 0
    assert annulus.angular_bin_count == 0
    assert annulus.supported_angular_bin_count == 0
    assert annulus.support_fraction is None
    for report in (sector, annulus):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes
        json.dumps(report.to_dict(), allow_nan=False)


def test_orientation_evidence_blocks_invalid_optional_support_report_types() -> None:
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )

    for quality_key, report_key in (
        ("sector_map_quality", "sector_map_quality_report"),
        ("annulus_quality", "annulus_quality_report"),
    ):
        evidence = build_orientation_evidence(
            {"f_herman": 0.4},
            detector,
            applicability="supported",
            **{quality_key: object()},
        )

        report = evidence.physical_checks[report_key]
        assert evidence.level is QualityLevel.DIAGNOSTIC
        assert evidence.applicable is False
        assert report["support_available"] is False
        assert report["level"] == "Diagnostic"
        assert "sector_support_unavailable" in report["reason_codes"]


def test_detached_support_reports_require_complete_generated_fields() -> None:
    payload = {
        "support_available": True,
        "reason_codes": [],
        "level": "Trend",
    }
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )

    for report_type, quality_key in (
        (SectorMapQualityReport, "sector_map_quality"),
        (AnnulusQualityReport, "annulus_quality"),
    ):
        report = report_type.from_dict(payload)
        evidence = build_orientation_evidence(
            {"f_herman": 0.4},
            detector,
            applicability="supported",
            **{quality_key: payload},
        )

        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes
        assert evidence.level is QualityLevel.DIAGNOSTIC
        assert evidence.applicable is False

    sector = build_sector_map_quality_report(np.ones((2, 2)), np.ones((2, 2)))
    annulus = build_annulus_quality_report(
        np.ones((2, 2)),
        np.asarray([0.40, 0.50]),
        q_target=0.50,
        q_width=0.01,
    )
    assert SectorMapQualityReport.from_dict(sector.to_dict()) == sector
    assert AnnulusQualityReport.from_dict(annulus.to_dict()) == annulus
    unavailable_annulus = build_annulus_quality_report(
        np.ones((2, 2)),
        np.asarray([0.40, np.nan]),
        q_target=0.50,
        q_width=0.01,
    )
    assert AnnulusQualityReport.from_dict(unavailable_annulus.to_dict()) == unavailable_annulus


def test_detached_support_reports_reject_coherence_inconsistent_trend_payloads() -> None:
    sector = SectorMapQualityReport.from_dict(
        {
            "shape": [2, 2],
            "support_available": True,
            "supported_bin_count": 0,
            "empty_bin_count": 4,
            "measured_nonpositive_bin_count": 0,
            "support_fraction": 0.0,
            "reason_codes": [],
            "level": "Trend",
        }
    )
    annulus = AnnulusQualityReport.from_dict(
        {
            "q_target_nm1": 0.5,
            "q_width_nm1": 0.1,
            "selected_q_bin_count": 0,
            "angular_bin_count": 2,
            "supported_angular_bin_count": 0,
            "support_fraction": 0.0,
            "support_available": True,
            "reason_codes": [],
            "level": "Trend",
        }
    )

    for report in (sector, annulus):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


def test_detached_support_reports_reject_contradictory_availability_payloads() -> None:
    contradictory_sector = {
        "shape": [1, 1],
        "support_available": True,
        "supported_bin_count": 1,
        "empty_bin_count": 0,
        "measured_nonpositive_bin_count": 0,
        "support_fraction": 1.0,
        "reason_codes": ["sector_support_unavailable"],
        "level": "Trend",
    }
    unavailable_sector = dict(contradictory_sector)
    unavailable_sector.update(support_available=False)
    contradictory_annulus = {
        "q_target_nm1": 0.5,
        "q_width_nm1": 0.1,
        "selected_q_bin_count": 2,
        "angular_bin_count": 2,
        "supported_angular_bin_count": 2,
        "support_fraction": 1.0,
        "support_available": True,
        "reason_codes": ["sector_support_unavailable"],
        "level": "Trend",
    }
    unavailable_annulus = dict(contradictory_annulus)
    unavailable_annulus.update(support_available=False)

    sector_reports = [
        SectorMapQualityReport.from_dict(contradictory_sector),
        SectorMapQualityReport.from_dict(unavailable_sector),
    ]
    annulus_reports = [
        AnnulusQualityReport.from_dict(contradictory_annulus),
        AnnulusQualityReport.from_dict(unavailable_annulus),
    ]

    for report in (*sector_reports, *annulus_reports):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes
        json.dumps(report.to_dict(), allow_nan=False)
    for report in sector_reports:
        assert report.supported_bin_count == 0
        assert report.empty_bin_count == 0
        assert report.measured_nonpositive_bin_count == 0
        assert report.support_fraction is None
    for report in annulus_reports:
        assert report.selected_q_bin_count == 0
        assert report.angular_bin_count == 0
        assert report.supported_angular_bin_count == 0
        assert report.support_fraction is None


def test_detached_support_defect_reasons_cannot_claim_usable_levels() -> None:
    sector = SectorMapQualityReport.from_dict(
        {
            "shape": [1, 1],
            "support_available": True,
            "supported_bin_count": 1,
            "empty_bin_count": 0,
            "measured_nonpositive_bin_count": 1,
            "support_fraction": 1.0,
            "reason_codes": ["sector_measured_nonpositive_bins_present"],
            "level": "Quantitative",
        }
    )
    annulus = AnnulusQualityReport.from_dict(
        {
            "q_target_nm1": 0.5,
            "q_width_nm1": 0.1,
            "selected_q_bin_count": 2,
            "angular_bin_count": 2,
            "supported_angular_bin_count": 0,
            "support_fraction": 0.0,
            "support_available": True,
            "reason_codes": ["annulus_no_supported_angular_bins"],
            "level": "Trend",
        }
    )

    for report in (sector, annulus):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


def test_support_builders_reject_string_and_complex_counts() -> None:
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )
    for support in (
        np.asarray([["1", "1"]]),
        np.asarray([[1.0 + 0.0j, 1.0 + 0.0j]]),
    ):
        sector = build_sector_map_quality_report(np.ones((1, 2)), support)
        annulus = build_annulus_quality_report(
            support,
            np.asarray([0.40, 0.50]),
            q_target=0.50,
            q_width=0.01,
        )
        evidence = build_orientation_evidence(
            {"f_herman": 0.4},
            detector,
            applicability="supported",
            annulus_quality=annulus,
        )

        for report in (sector, annulus):
            assert report.support_available is False
            assert report.level is QualityLevel.DIAGNOSTIC
            assert "sector_support_unavailable" in report.reason_codes
        assert evidence.applicable is False


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


def test_sector_report_downgrades_supported_nonfinite_intensity() -> None:
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )

    for intensity in (np.nan, np.inf):
        report = build_sector_map_quality_report(
            np.asarray([[intensity, 1.0]]),
            np.ones((1, 2)),
        )
        evidence = build_orientation_evidence(
            {"f_herman": 0.4},
            detector,
            applicability="supported",
            sector_map_quality=report,
        )

        assert report.support_available is True
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_measured_nonfinite_bins_present" in report.reason_codes
        assert evidence.applicable is False


def test_sector_report_accepts_fractional_and_rejects_bool_support_counts() -> None:
    fractional = build_sector_map_quality_report(
        np.ones((1, 2)),
        np.asarray([[0.5, 1.0]]),
    )
    assert fractional.support_available is True
    assert fractional.support_fraction == 1.0
    json.dumps(fractional.to_dict(), allow_nan=False)

    boolean = build_sector_map_quality_report(
        np.ones((1, 2)),
        np.asarray([[True, 1]], dtype=bool),
    )
    assert boolean.support_available is False
    assert boolean.level is QualityLevel.DIAGNOSTIC
    assert "sector_support_unavailable" in boolean.reason_codes


def test_annulus_report_accepts_fractional_and_rejects_bool_support_counts() -> None:
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )
    fractional = build_annulus_quality_report(
        np.asarray([[0.5, 1.0], [1.0, 1.0]]),
        np.asarray([0.40, 0.50]),
        q_target=0.50,
        q_width=0.01,
    )
    assert fractional.support_available is True
    json.dumps(fractional.to_dict(), allow_nan=False)

    boolean = build_annulus_quality_report(
        np.asarray([[True, True], [True, True]], dtype=bool),
        np.asarray([0.40, 0.50]),
        q_target=0.50,
        q_width=0.01,
    )
    evidence = build_orientation_evidence(
        {"f_herman": 0.4},
        detector,
        applicability="supported",
        annulus_quality=boolean,
    )

    assert boolean.support_available is False
    assert boolean.level is QualityLevel.DIAGNOSTIC
    assert "sector_support_unavailable" in boolean.reason_codes
    assert evidence.level is QualityLevel.DIAGNOSTIC
    assert evidence.applicable is False


def test_unavailable_support_cannot_retain_non_unusable_report_level() -> None:
    sector = SectorMapQualityReport.from_dict(
        {
            "shape": [1, 1],
            "support_available": False,
            "supported_bin_count": 0,
            "empty_bin_count": 0,
            "measured_nonpositive_bin_count": 0,
            "support_fraction": None,
            "reason_codes": ["sector_support_unavailable"],
            "level": "Quantitative",
        }
    )
    annulus = AnnulusQualityReport.from_dict(
        {
            "q_target_nm1": None,
            "q_width_nm1": None,
            "selected_q_bin_count": 0,
            "angular_bin_count": 0,
            "supported_angular_bin_count": 0,
            "support_fraction": None,
            "support_available": False,
            "reason_codes": ["sector_support_unavailable"],
            "level": "Trend",
        }
    )

    for report in (sector, annulus):
        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


def test_annulus_report_fails_closed_for_zero_sized_support_maps() -> None:
    for support, q in (
        (np.empty((0, 2)), np.asarray([0.40, 0.50])),
        (np.empty((2, 0)), np.asarray([])),
        (np.empty((0, 0)), np.asarray([])),
    ):
        report = build_annulus_quality_report(
            support,
            q,
            q_target=0.50,
            q_width=0.01,
        )

        assert report.support_available is False
        assert report.level is QualityLevel.DIAGNOSTIC
        assert "sector_support_unavailable" in report.reason_codes


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
        == "Diagnostic"
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


def test_orientation_evidence_preserves_unusable_precedence_over_unavailable_support() -> None:
    unavailable_sector = SectorMapQualityReport(
        reason_codes=("sector_support_unavailable",),
        level=QualityLevel.DIAGNOSTIC,
    )
    usable_detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )
    unusable_detector = build_detector_quality_report(
        np.empty((0, 0)),
        source_kind="raw_detector",
    )

    missing_metrics = build_orientation_evidence(
        {},
        usable_detector,
        applicability="supported",
        sector_map_quality=unavailable_sector,
    )
    detector_unusable = build_orientation_evidence(
        {"f_herman": 0.4},
        unusable_detector,
        applicability="supported",
        sector_map_quality=unavailable_sector,
    )

    for evidence in (missing_metrics, detector_unusable):
        assert evidence.level is QualityLevel.UNUSABLE
        assert evidence.applicable is False
        assert "sector_support_unavailable" in evidence.reason_codes


def test_orientation_evidence_preserves_explicit_unusable_support_precedence() -> None:
    detector = build_detector_quality_report(
        np.ones((2, 2)),
        source_kind="raw_detector",
        beam_center=(1.0, 1.0),
    )
    unusable_sector = SectorMapQualityReport(
        reason_codes=("sector_support_unavailable",),
        level=QualityLevel.UNUSABLE,
    )
    unusable_annulus = AnnulusQualityReport(
        reason_codes=("sector_support_unavailable",),
        level=QualityLevel.UNUSABLE,
    )

    for quality_key, report in (
        ("sector_map_quality", unusable_sector),
        ("annulus_quality", unusable_annulus),
    ):
        evidence = build_orientation_evidence(
            {"f_herman": 0.4},
            detector,
            applicability="supported",
            **{quality_key: report},
        )

        assert evidence.level is QualityLevel.UNUSABLE
        assert evidence.applicable is False
        assert "sector_support_unavailable" in evidence.reason_codes
