from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine import core as saxs_core
from polynexus.core.saxs_engine.preprocess import normalize_intensity, subtract_background
from polynexus.core.saxs_engine.saxs_extrapolation_helpers import _extrapolate_guinier
from polynexus.core.saxs_engine.saxs_physical_helpers import (
    _crystallinity_invariant,
    specific_surface_from_porod,
)
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    absolute_q_unit_status,
    normalize_q_to_nm,
    prepare_uniform_q_profile,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    _relative_crystallinity_from_sequence,
    analyze_temperature_series,
    avrami_kinetics,
    gibbs_thomson_analysis,
)


def test_transmission_background_scaling_uses_sample_over_background() -> None:
    cfg = SAXSConfig(
        transmission_sample=0.5,
        transmission_background=1.0,
        sample_thickness_m=1.0,
    )
    q = np.array([0.1, 0.2])
    corrected = subtract_background(q, [7.0, 7.0], [4.0, 4.0], cfg, q)

    result = normalize_intensity(corrected, cfg)

    np.testing.assert_allclose(result, [10.0, 10.0])


def test_guinier_extrapolation_remains_finite_at_q_zero() -> None:
    q = np.linspace(0.15, 0.5, 20)
    intensity = 100.0 * np.exp(-(q * q) * 4.0 / 3.0)

    q_extended, intensity_extended = _extrapolate_guinier(
        q, intensity, q[1] - q[0], n_extra=15
    )

    assert q_extended[0] == pytest.approx(0.0)
    assert np.isfinite(intensity_extended[:15]).all()
    assert intensity_extended[0] == pytest.approx(100.0, rel=0.2)
    assert intensity_extended[0] / intensity_extended[1] < 1.2


def test_porod_invariant_crystallinity_uses_documented_two_phase_constant() -> None:
    drho = 0.2
    phi = 0.35
    length_nm = 10.0
    specific_surface_nm = 2.0 / length_nm
    q_invariant = 2.0 * np.pi**2 * drho**2 * phi * (1.0 - phi)
    porod_constant = 2.0 * np.pi * drho**2 * specific_surface_nm

    result = _crystallinity_invariant(
        length_nm,
        q_invariant,
        porod_constant,
        q_unit="nm^-1",
        length_unit="nm",
    )

    assert result == pytest.approx(phi, rel=1e-6)


def test_specific_surface_requires_phase_fraction() -> None:
    phi = 0.35
    q_invariant = 2.0
    porod_constant = 3.0

    result = specific_surface_from_porod(q_invariant, porod_constant, phi)

    assert result == pytest.approx(np.pi * phi * (1.0 - phi) * porod_constant / q_invariant)


def test_q_invariant_confidence_penalty_is_applied_after_assignment(monkeypatch) -> None:
    monkeypatch.setattr(saxs_core, "_tangent_lc", lambda *_args, **_kwargs: 3.0)
    monkeypatch.setattr(saxs_core, "_porod_constant", lambda *_args, **_kwargs: 1.0)
    cfg = SAXSConfig()
    corr_result = {
        "Q_invariant": 100.0,
        "q_ext": np.linspace(0.1, 2.0, 20),
        "I_ext": np.ones(20),
    }

    result = saxs_core.compute_structure_params(
        corr_result,
        {"lc_idf": 3.0},
        cfg,
        L_ensemble=10.0,
    )

    assert result.confidence_lc == pytest.approx(0.5)


def test_angstrom_q_is_converted_to_the_same_nm_axis() -> None:
    q_angstrom = np.array([0.01, 0.02, 0.03])

    q_nm = normalize_q_to_nm(q_angstrom, "angstrom^-1")

    np.testing.assert_allclose(q_nm, [0.1, 0.2, 0.3])


def test_unitless_q_blocks_absolute_metrics_with_a_reason() -> None:
    status = absolute_q_unit_status(None)

    assert status["available"] is False
    assert status["reason"] == "q_unit_required"


def test_fourier_profile_is_deduplicated_and_resampled_to_uniform_q() -> None:
    q = np.array([0.1, 0.15, 0.15, 0.4, 0.7])
    intensity = np.array([1.0, 0.8, 0.6, 0.3, 0.1])

    prepared = prepare_uniform_q_profile(q, intensity, points=13)

    assert np.all(np.diff(prepared.q) > 0)
    np.testing.assert_allclose(np.diff(prepared.q), np.diff(prepared.q)[0])
    assert prepared.intensity[1] == pytest.approx(0.7)


def test_analyze_single_hides_absolute_metrics_without_declared_q_unit() -> None:
    q = np.linspace(0.1, 2.0, 80)
    intensity = 1.0 / (1.0 + q * q)
    cfg = SAXSConfig(
        q_unit=None,
        q_unit_declared=False,
        smooth_method="none",
    )

    result = saxs_core.analyze_single(q, intensity, cfg)

    assert result.q_unit_status["available"] is False
    assert result.structure.Q_invariant != result.structure.Q_invariant
    assert result.Q_star_valid is False


def test_cooling_relative_crystallinity_uses_fixed_full_sequence_endpoints() -> None:
    q_values = np.arange(1.0, 8.0)

    Xc, q_melt, q_solid = _relative_crystallinity_from_sequence(q_values, "cooling")

    np.testing.assert_allclose(Xc, np.linspace(0.0, 1.0, 7))
    assert q_melt == pytest.approx(1.0)
    assert q_solid == pytest.approx(7.0)


def test_avrami_requires_explicit_seconds_axis() -> None:
    result = avrami_kinetics(None, np.linspace(0.0, 1.0, 8))

    assert result["valid"] is False
    assert result["reason"] == "time_axis_required"


def test_temperature_series_does_not_treat_frame_indices_as_seconds() -> None:
    q = np.linspace(0.1, 2.0, 40)
    intensity = 1.0 / (1.0 + q * q)

    result = analyze_temperature_series(
        [100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.0],
        [q] * 7,
        [intensity] * 7,
        cfg=SAXSConfig(smooth_method="none"),
        exp_type="cooling",
    )

    assert result.avrami["valid"] is False
    assert result.avrami["reason"] == "time_axis_required"


def test_gibbs_thomson_requires_melting_window_and_enthalpy() -> None:
    result = gibbs_thomson_analysis(
        np.array([180.0, 185.0, 190.0, 195.0]),
        np.array([4.0, 5.0, 6.0, 7.0]),
        Tm_inf=220.0,
        melting_window_status=["outside_window"] * 4,
        delta_Hf_Jm3=None,
    )

    assert result["valid"] is False
    assert result["reason"] == "melting_window_required"
