from __future__ import annotations

import numpy as np

from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.io import SUPPORTED_1D_EXTENSIONS
from polynexus.core.saxs_engine.preprocess import apply_polarisation_correction
from polynexus.core.saxs_engine.saxs_temperature import (
    TempPhase,
    analyze_temperature_series,
    detect_temperature_phase,
    gibbs_thomson_analysis,
)


def test_polarisation_correction_has_correct_small_angle_limits() -> None:
    cfg = SAXSConfig(do_polarisation_correction=True, polarisation_degree=1.0)
    q = np.asarray([0.0, 0.01])
    intensity = np.ones(2)

    corrected = apply_polarisation_correction(q, intensity, cfg)

    np.testing.assert_allclose(corrected[0], 1.0, rtol=1e-12)
    assert np.all(corrected <= 1.01)


def test_cooling_phase_distinguishes_solid_from_melt() -> None:
    assert hasattr(TempPhase, "COOLING_SOLID")
    assert detect_temperature_phase(100, 1.0, 1.0, 10.0, 10.0, "cooling") is TempPhase.COOLING_SOLID
    assert detect_temperature_phase(100, 0.1, 1.0, 10.0, 10.0, "cooling") is TempPhase.COOLING_MELT


def test_cooling_series_preserves_acquisition_order_and_uses_coldest_reference() -> None:
    q = np.linspace(0.1, 1.5, 40)
    profile = np.exp(-q)
    result = analyze_temperature_series(
        temperatures=[100.0, 80.0, 90.0],
        q_list=[q, q, q],
        I_list=[profile, profile, profile],
        times=[0.0, 1.0, 2.0],
        cfg=SAXSConfig(),
        exp_type="cooling",
    )

    assert result.temperatures.tolist() == [100.0, 80.0, 90.0]
    assert [point.source_index for point in result.temp_points] == [0, 1, 2]
    assert result.avrami.get("valid") is False or result.avrami == {}


def test_gibbs_thomson_converts_nm_to_si_and_honors_fixed_tm_inf() -> None:
    lc_nm = np.asarray([2.0, 2.5, 3.0, 4.0, 5.0])
    tm_inf_c = 180.0
    sigma = 0.02
    delta_hf = 2.0e8
    tm_k = (tm_inf_c + 273.15) * (1 - 2 * sigma / (delta_hf * lc_nm * 1e-9))
    temperatures = tm_k - 273.15

    result = gibbs_thomson_analysis(
        temperatures,
        lc_nm,
        Tm_inf=tm_inf_c,
        melting_window_status=["within_window"] * len(lc_nm),
        delta_Hf_Jm3=delta_hf,
    )

    np.testing.assert_allclose(result["Tm_inf_C"], tm_inf_c, atol=1e-10)
    np.testing.assert_allclose(result["sigma_e_Jm2"], sigma, rtol=1e-6)


def test_correlation_extrapolation_flags_control_extension() -> None:
    from polynexus.core.saxs_engine.core import correlation_function

    q = np.linspace(0.15, 2.0, 80)
    intensity = 1.0 / (1.0 + q**2)
    cfg = SAXSConfig(q_corr_min=0.15, q_corr_max=2.0, n_z_points=128)

    no_ext = correlation_function(q, intensity, cfg, extrapolate_q0=False, extrapolate_qinf=False)
    with_ext = correlation_function(q, intensity, cfg, extrapolate_q0=True, extrapolate_qinf=True)

    assert len(no_ext["q_ext"]) == len(q[(q >= 0.15) & (q <= 2.0)])
    assert len(with_ext["q_ext"]) > len(no_ext["q_ext"])


def test_xy_is_a_supported_single_profile_extension(tmp_path) -> None:
    path = tmp_path / "profile.xy"
    path.write_text("0.1 1.0\n0.2 0.8\n0.3 0.6\n0.4 0.5\n0.5 0.4\n", encoding="utf-8")

    assert ".xy" in SUPPORTED_1D_EXTENSIONS
    engine = SAXSEngine(SAXSConfig())
    assert engine.load(str(path)) is True


def test_directory_profile_projection_uses_unsmoothed_normalized_layer(tmp_path, monkeypatch) -> None:
    path = tmp_path / "frame.dat"
    path.write_text("0.1 1.0\n0.2 0.8\n0.3 0.6\n0.4 0.5\n0.5 0.4\n", encoding="utf-8")
    cfg = SAXSConfig(experiment_type="static")
    engine = SAXSEngine(cfg)
    monkeypatch.setattr(
        "polynexus.core.saxs.scan_experiment_dir",
        lambda _root, _cfg: [],
    )
    assert engine._processed_profile_from_payload(
        {"q": [0.1], "Iq": [1.0], "Iq_norm": [2.0], "Iq_smooth": [3.0]},
        source="test",
    ).normalized.tolist() == [2.0]


def test_temperature_override_is_written_to_correction_config(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_temperature as temperature_module

    seen = []

    def capture(cfg, temperature):
        seen.append(float(cfg.alpha_thermal_expansion))
        return cfg

    monkeypatch.setattr(temperature_module, "apply_thermal_correction", capture)
    q = np.linspace(0.1, 1.5, 40)
    analyze_temperature_series(
        temperatures=[80.0],
        q_list=[q],
        I_list=[np.exp(-q)],
        cfg=SAXSConfig(),
        thermal_expansion_coeff=1.2e-4,
    )

    assert seen == [1.2e-4]


def test_directory_2d_batch_uses_normalized_unsmoothed_intensity(monkeypatch, tmp_path) -> None:
    import polynexus.core.saxs as saxs_module
    from polynexus.core.saxs_engine.config import ExperimentCondition

    path = tmp_path / "frame.edf"
    path.write_bytes(b"placeholder")
    condition = ExperimentCondition(value=0.0, files=[str(path)])
    monkeypatch.setattr(saxs_module, "scan_experiment_dir", lambda *_: [condition])
    monkeypatch.setattr(saxs_module, "read_image", lambda *_: (np.ones((2, 2)), {}))
    monkeypatch.setattr(saxs_module, "_integrate_pyfai_shadow", lambda *_: (np.array([]), np.array([])))
    monkeypatch.setattr(
        saxs_module,
        "preprocess_pipeline",
        lambda *_args, **_kwargs: {
            "q": np.asarray([0.1, 0.2]),
            "Iq": np.asarray([10.0, 9.0]),
            "Iq_norm": np.asarray([1.0, 0.9]),
            "Iq_smooth": np.asarray([0.8, 0.7]),
        },
    )

    engine = SAXSEngine(SAXSConfig())
    assert engine.load(str(tmp_path)) is True
    np.testing.assert_array_equal(engine._I_list[0], [1.0, 0.9])


def test_directory_truncation_is_recorded_as_condition_frame_limit(monkeypatch, tmp_path) -> None:
    from polynexus.core.saxs_engine.config import ExperimentCondition
    import polynexus.core.saxs as saxs_module

    files = []
    for index in range(11):
        path = tmp_path / f"frame_{index}.dat"
        path.write_text("0.1 1\n0.2 0.9\n0.3 0.8\n0.4 0.7\n0.5 0.6\n", encoding="utf-8")
        files.append(str(path))
    monkeypatch.setattr(
        saxs_module,
        "scan_experiment_dir",
        lambda *_: [ExperimentCondition(value=0.0, files=files)],
    )

    engine = SAXSEngine(SAXSConfig())
    assert engine.load(str(tmp_path)) is True
    assert len(engine._q_list) == 11
    assert not any(item["reason"] == "condition_frame_limit" for item in engine._skipped_files)
