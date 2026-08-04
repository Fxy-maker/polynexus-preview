from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_anisotropy import analyze_anisotropy
from polynexus.core.saxs_engine.saxs_strain import (
    herman_from_sector_data,
)
from polynexus.core.saxs_engine.saxs_orientation_reliability import (
    axial_distance_deg,
    build_q_resolved_orientation,
    contract_json,
    evaluate_orientation_sensitivity,
)


def test_q_resolved_m2_preserves_detector_plane_baseline() -> None:
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    q = np.array([0.20, 0.30, 0.40])
    intensity = np.ones((chi.size, q.size))
    support = np.ones_like(intensity)

    evidence = build_q_resolved_orientation(
        intensity, q, chi, support_count=support
    )

    assert all(
        point.f_principal_raw == pytest.approx(0.25, abs=1e-12)
        for point in evidence.q_bins
    )
    assert evidence.convention == "detector_plane_2d_v1"
    assert evidence.isotropic_baseline == 0.25


def test_q_resolved_m2_recovers_known_axis_and_strength() -> None:
    chi = np.linspace(-np.pi, np.pi, 180, endpoint=False)
    q = np.array([0.25, 0.30, 0.35])
    axis = np.deg2rad(35.0)
    intensity = 10.0 * (1.0 + 0.4 * np.cos(2.0 * (chi[:, None] - axis)))
    intensity = np.repeat(intensity, q.size, axis=1)

    evidence = build_q_resolved_orientation(
        intensity, q, chi, support_count=np.ones_like(intensity)
    )

    point = evidence.q_bins[1]
    assert point.anisotropy_strength == pytest.approx(0.2, abs=0.01)
    assert axial_distance_deg(point.principal_axis_deg, 35.0) < 1.0
    assert point.f_principal_raw == pytest.approx(0.40, abs=0.01)


def _harmonic_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    q = np.asarray([0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80])
    axis = np.deg2rad(35.0)
    intensity = np.ones((chi.size, q.size))
    harmonic = 10.0 * (1.0 + 0.8 * np.cos(2.0 * (chi - axis)))
    intensity[:, :3] = harmonic[:, None]
    intensity[:, 4:] = harmonic[:, None]
    support = np.ones_like(intensity)
    return intensity, q, chi, support


def test_q_bins_keep_additive_harmonics_reference_projection_and_stable_ids() -> None:
    intensity, q, chi, support = _harmonic_fixture()
    first = build_q_resolved_orientation(
        intensity,
        q,
        chi,
        support_count=support,
        reference_axis_deg=0.0,
        reference_axis_kind="tensile_axis",
        source_id="frame-0",
    )
    second = build_q_resolved_orientation(
        intensity,
        q,
        chi,
        support_count=support,
        reference_axis_deg=0.0,
        reference_axis_kind="tensile_axis",
        source_id="frame-0",
    )

    point = first.q_bins[1]
    assert point.q_bin_id == second.q_bins[1].q_bin_id
    assert point.harmonic_numerator_real is not None
    assert point.harmonic_numerator_imag is not None
    assert point.intensity_denominator == pytest.approx(720.0)
    assert point.f_reference != pytest.approx(point.f_principal_raw)
    assert point.reference_axis_kind == "tensile_axis"
    assert first.q_band_candidates
    assert {candidate.feature_kind for candidate in first.q_band_candidates} == {
        "q_band"
    }


def test_zero_support_is_unavailable_and_separated_bands_remain_neutral() -> None:
    intensity, q, chi, support = _harmonic_fixture()
    support[:, 3] = 0.0
    evidence = build_q_resolved_orientation(
        intensity, q, chi, support_count=support
    )

    assert evidence.q_bins[3].level == "Unusable"
    assert "annulus_no_supported_angular_bins" in evidence.q_bins[3].reason_codes
    assert [candidate.supported_q_bin_ids for candidate in evidence.q_band_candidates]
    assert all(candidate.feature_kind == "q_band" for candidate in evidence.q_band_candidates)
    assert len(evidence.q_band_candidates) == 2


def test_stability_is_deterministic_json_safe_and_non_mutating() -> None:
    intensity, q, chi, support = _harmonic_fixture()
    before = intensity.copy()
    first = build_q_resolved_orientation(
        intensity, q, chi, support_count=support, source_id="frame-0"
    )
    second = build_q_resolved_orientation(
        intensity, q, chi, support_count=support, source_id="frame-0"
    )

    assert first.to_dict() == second.to_dict()
    assert "confidence_interval" not in str(first.to_dict())
    contract_json(first)
    np.testing.assert_array_equal(intensity, before)


def test_sensitivity_is_bounded_candidate_only_and_does_not_mutate_inputs() -> None:
    intensity, q, chi, support = _harmonic_fixture()
    cfg = SAXSConfig()
    cfg_before = SAXSConfig(**{field: getattr(cfg, field) for field in cfg.__dataclass_fields__})
    mask = np.zeros((8, 8), dtype=bool)
    mask[4, 4] = True
    mask_before = mask.copy()

    evidence = evaluate_orientation_sensitivity(
        intensity,
        q,
        chi,
        support_count=support,
        cfg=cfg,
        confirmed_mask=mask,
        source_id="frame-0",
    )

    assert evidence.sensitivity_summary.baseline_variant_id == "baseline"
    assert evidence.reliability_policy_digest
    assert evidence.sensitivity_summary.observations
    assert all(
        entry.status == "candidate_only"
        for entry in evidence.correction_ledger
        if entry.operation.endswith("variant")
    )
    assert cfg == cfg_before
    np.testing.assert_array_equal(mask, mask_before)


def test_anisotropy_and_strain_consumers_receive_detached_q_evidence() -> None:
    intensity, q, chi, support = _harmonic_fixture()
    cfg = SAXSConfig(tensile_axis_deg=0.0, orientation_axis_deg=None)
    result = analyze_anisotropy(
        intensity,
        q,
        chi,
        q,
        np.mean(intensity, axis=0),
        cfg=cfg,
        support_count=support,
    )
    assert result.q_resolved_orientation_evidence is not None
    assert np.isfinite(result.f_herman_raw)

    sector_result = herman_from_sector_data(
        {
            "I_2d": intensity,
            "q_2d": q,
            "chi_rad": chi,
            "q": q,
            "I_full": np.mean(intensity, axis=0),
            "support_count": support,
        },
        cfg=cfg,
    )
    assert sector_result["q_resolved_orientation_evidence"] is not None
