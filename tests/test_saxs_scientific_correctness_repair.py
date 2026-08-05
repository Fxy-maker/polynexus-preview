from __future__ import annotations

import numpy as np
import pytest
import h5py

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine import core as saxs_core
from polynexus.core.saxs_engine.preprocess import normalize_intensity, subtract_background
from polynexus.core.saxs_engine.preprocess import _manual_integrate
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
from polynexus.core.saxs_engine.io import (
    UnsupportedDatasetError,
    extract_geometry_from_header,
    read_hdf5_dataset,
    read_1d_profile,
)
from polynexus.core.saxs_engine.saxs_temperature import (
    _relative_crystallinity_from_sequence,
    analyze_temperature_series,
    avrami_kinetics,
    gibbs_thomson_analysis,
)
from polynexus.core.saxs_engine.saxs_anisotropy import (
    detector_plane_sector_mask,
    herman_from_azimuthal,
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


def test_correlation_payload_keeps_declared_q_bounds_in_raw_view() -> None:
    q = np.linspace(0.05, 1.8, 240)
    intensity = 2.0 + 0.2 * np.sin(q * 8.0)
    result = saxs_core.correlation_function(
        q,
        intensity,
        SAXSConfig(q_corr_min=0.05, q_corr_max=1.8),
        q_min=0.125,
        q_max=1.5,
        extrapolate_q0=False,
        extrapolate_qinf=False,
    )

    assert "q_raw" in result
    assert result["q_raw"][0] >= 0.125
    assert result["q_raw"][-1] <= 1.5


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


def test_analyze_single_normalizes_declared_angstrom_q_to_nm() -> None:
    q_angstrom = np.linspace(0.01, 0.2, 80)
    intensity = 1.0 / (1.0 + q_angstrom * q_angstrom)
    cfg = SAXSConfig(q_unit="angstrom^-1", q_unit_declared=True, smooth_method="none")

    result = saxs_core.analyze_single(q_angstrom, intensity, cfg)

    assert result.q_unit_status["available"] is True
    assert result.q[0] == pytest.approx(0.1)


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


def test_geometry_header_parsing_does_not_mutate_the_base_config() -> None:
    cfg = SAXSConfig()
    original_wavelength = cfg.wavelength_m

    header_cfg = extract_geometry_from_header(
        {"WaveLength": 1.0, "PSize": 0.0001, "SampleDistance": 500.0, "Center_1": 10.0, "Center_2": 20.0},
        cfg,
    )
    fallback_cfg = extract_geometry_from_header({}, cfg)

    assert header_cfg is not cfg
    assert header_cfg.wavelength_m != original_wavelength
    assert fallback_cfg.wavelength_m == pytest.approx(original_wavelength)


def test_directory_frames_keep_isolated_geometry_configs(monkeypatch, tmp_path) -> None:
    import polynexus.core.saxs as saxs_module
    from polynexus.core.saxs import SAXSEngine
    from polynexus.core.saxs_engine.config import ExperimentCondition

    paths = [tmp_path / "frame_a.edf", tmp_path / "frame_b.edf"]
    for path in paths:
        path.write_bytes(b"placeholder")

    monkeypatch.setattr(
        saxs_module,
        "scan_experiment_dir",
        lambda *_: [ExperimentCondition(value=0.0, files=[str(path) for path in paths])],
    )
    headers = {
        str(paths[0]): {"WaveLength": 1.0, "PSize": 0.075, "SampleDistance": 450.0, "Center_1": 10.0, "Center_2": 20.0},
        str(paths[1]): {},
    }
    monkeypatch.setattr(
        saxs_module,
        "read_image",
        lambda path: (np.ones((4, 4)), headers[str(path)]),
    )
    monkeypatch.setattr(
        saxs_module,
        "preprocess_pipeline",
        lambda _img, _cfg, **_kwargs: {
            "q": np.linspace(0.1, 0.5, 5),
            "Iq": np.ones(5),
            "Iq_norm": np.ones(5),
            "Iq_smooth": np.ones(5),
            "sector_data": None,
        },
    )
    monkeypatch.setattr(
        saxs_module,
        "_integrate_pyfai_shadow",
        lambda *_args: (np.array([]), np.array([])),
    )

    engine = SAXSEngine(SAXSConfig())
    assert engine.load(str(tmp_path)) is True

    assert len(engine._cfg_list) == 2
    assert engine._cfg_list[0].wavelength_m == pytest.approx(1.0e-10)
    assert engine._cfg_list[1].wavelength_m == pytest.approx(SAXSConfig().wavelength_m)


def test_hdf5_reader_rejects_equally_eligible_datasets(tmp_path) -> None:
    path = tmp_path / "ambiguous.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("entry/data_a", data=np.ones((4, 4)))
        handle.create_dataset("entry/data_b", data=np.ones((4, 4)))

    with pytest.raises(UnsupportedDatasetError, match="ambiguous"):
        read_hdf5_dataset(str(path))


def test_text_reader_preserves_declared_q_unit_and_marks_missing_unit(tmp_path) -> None:
    angstrom_path = tmp_path / "profile_a.dat"
    angstrom_path.write_text(
        "# q [A^-1] I\n0.01 10\n0.02 8\n0.03 6\n",
        encoding="utf-8",
    )
    unitless_path = tmp_path / "profile_unknown.dat"
    unitless_path.write_text("0.1 10\n0.2 8\n0.3 6\n", encoding="utf-8")

    _q_a, _i_a, meta_a = read_1d_profile(str(angstrom_path))
    _q_u, _i_u, meta_u = read_1d_profile(str(unitless_path))

    assert meta_a["q_unit"] == "angstrom^-1"
    assert meta_u["q_unit"] is None
    assert meta_u["q_unit_reason"] == "q_unit_required"


def test_detector_plane_sector_masks_include_both_mirrored_axes() -> None:
    chi = np.deg2rad(np.array([-180.0, -90.0, 0.0, 90.0, 180.0]))

    meridional = detector_plane_sector_mask(chi, axis_deg=0.0, halfwidth_deg=15.0)
    equatorial = detector_plane_sector_mask(chi, axis_deg=90.0, halfwidth_deg=15.0)

    np.testing.assert_array_equal(meridional, [True, False, True, False, True])
    np.testing.assert_array_equal(equatorial, [False, True, False, True, False])


def test_orientation_result_identifies_detector_plane_projection() -> None:
    chi = np.linspace(-np.pi, np.pi, 73)
    intensity = np.ones_like(chi)

    result = herman_from_azimuthal(chi, intensity)

    assert result["convention"] == "detector_plane_2d_v1"
    assert result["metric_name"] == "projected_order_parameter_2d"
    assert result["f"] == pytest.approx(0.25, abs=1e-3)


def test_manual_detector_integration_preserves_signed_residuals() -> None:
    cfg = SAXSConfig(
        beam_center_x=0.0,
        beam_center_y=0.0,
        pixel_size_m=1.0e-3,
        sdd_m=0.1,
        wavelength_m=1.0e-10,
        q_min=0.01,
        q_max=2.0,
        n_pt=100,
        dummy_val=-10.0,
        ddummy=0.1,
    )
    image = np.ones((3, 3), dtype=float)
    image[2, 1] = -0.5
    image[1, 2] = -0.5

    _q, integrated = _manual_integrate(image, cfg)

    assert np.any(integrated < 0)


def test_manual_detector_integration_marks_unsupported_bins_unavailable() -> None:
    cfg = SAXSConfig(
        beam_center_x=0.0,
        beam_center_y=0.0,
        pixel_size_m=1.0e-3,
        sdd_m=0.1,
        wavelength_m=1.0e-10,
        q_min=0.01,
        q_max=2.0,
        n_pt=100,
        dummy_val=-10.0,
        ddummy=0.1,
    )
    from polynexus.core.saxs_engine.preprocess import _manual_integrate

    q, integrated, support = _manual_integrate(
        np.ones((3, 3), dtype=float), cfg, return_support=True
    )

    assert len(q) == len(integrated) == len(support) == cfg.n_pt
    assert np.any(support == 0)
    assert np.all(np.isnan(integrated[support == 0]))
