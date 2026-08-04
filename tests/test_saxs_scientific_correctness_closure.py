from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs_engine import saxs_physical_helpers as helpers
from polynexus.core.saxs_engine import saxs_quality_contracts as contracts
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import scattering_invariant
from polynexus.core.saxs_engine.saxs_temperature import (
    TempPhase,
    detect_temperature_phase,
)
from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_eligibility import classify_frame_eligibility


def test_porod_invariant_crystallinity_is_unit_invariant() -> None:
    phi = 0.35
    length_nm = 10.0
    kp_nm = 2.5
    q_nm = (np.pi / 2.0) * kp_nm * length_nm * phi * (1.0 - phi)

    length_a = length_nm * 10.0
    kp_a = kp_nm * 1.0e-4
    q_a = q_nm * 1.0e-3

    nm_value = helpers._crystallinity_invariant(
        length_nm, q_nm, kp_nm, q_unit="nm^-1", length_unit="nm"
    )
    angstrom_value = helpers._crystallinity_invariant(
        length_a, q_a, kp_a, q_unit="angstrom^-1", length_unit="angstrom"
    )

    assert nm_value == pytest.approx(phi, rel=1e-6)
    assert angstrom_value == pytest.approx(nm_value, rel=1e-6)


def test_cooling_phase_uses_low_temperature_solid_reference() -> None:
    assert detect_temperature_phase(100, 1.0, 1.0, 10.0, 10.0, "cooling") is TempPhase.COOLING_SOLID
    assert detect_temperature_phase(100, 0.1, 1.0, 10.0, 10.0, "cooling") is TempPhase.COOLING_MELT


def test_signed_profile_retains_negative_residual_and_quality_count() -> None:
    profile = contracts.sanitize_1d_profile([0.1, 0.2, 0.3], [1.0, -0.2, 0.5])

    assert profile.intensity.tolist() == [1.0, -0.2, 0.5]
    report = contracts.build_data_quality_report(
        [0.1, 0.2, 0.3], [1.0, -0.2, 0.5]
    ).to_dict()
    assert report["nonpositive_intensity_count"] == 1


def test_positive_only_fit_masks_negative_values_without_changing_invariant() -> None:
    q = np.linspace(0.1, 1.5, 40)
    intensity = np.exp(-q**2)
    intensity[4] = -1.0
    signed = scattering_invariant(q, intensity, cfg=SAXSConfig(q_min=0.1))
    positive = scattering_invariant(q, np.maximum(intensity, 0.0), cfg=SAXSConfig(q_min=0.1))

    assert signed < positive
    rg, _i0, q_fit, _ln_i = helpers.guinier_analysis(q, intensity)
    assert np.isfinite(rg)
    assert np.all(intensity[np.searchsorted(q, q_fit)] > 0)


def test_default_batch_is_unlimited_and_configured_limit_is_provenance_visible(monkeypatch, tmp_path) -> None:
    from polynexus.core.saxs import SAXSEngine
    from polynexus.core.saxs_engine.config import ExperimentCondition
    import polynexus.core.saxs as saxs_module

    paths = []
    for index in range(3):
        path = tmp_path / f"frame_{index}.dat"
        path.write_text("0.1 1\n0.2 0.9\n0.3 0.8\n0.4 0.7\n0.5 0.6\n", encoding="utf-8")
        paths.append(str(path))
    monkeypatch.setattr(
        saxs_module,
        "scan_experiment_dir",
        lambda *_: [ExperimentCondition(value=0.0, files=paths)],
    )

    unlimited = SAXSEngine(SAXSConfig())
    assert unlimited.load(str(tmp_path)) is True
    assert len(unlimited._q_list) == 3
    assert not unlimited._skipped_files

    limited = SAXSEngine(SAXSConfig(max_frames_per_condition=2))
    assert limited.load(str(tmp_path)) is True
    assert len(limited._q_list) == 2
    assert any(
        item.get("reason") == "condition_frame_limit" and item.get("limit") == 2
        for item in limited._skipped_files
    )


def test_figure_eligibility_requires_physical_gate_and_complete_geometry() -> None:
    analysis = type(
        "Analysis",
        (),
        {
            "final_parameters": {"quality_flag": "OK", "paper_figure_candidate": True},
            "detector_quality_report": {
                "geometry_provenance": {
                    "validity": "metadata_complete",
                    "field_sources": {"wavelength_m": "header"},
                }
            },
        },
    )()
    frame = SAXSFrameView(
        index=0,
        label="frame",
        condition=0.0,
        q=np.asarray([0.1, 0.2]),
        intensity=np.asarray([1.0, 0.8]),
        analysis=analysis,
        parameters={},
    )

    decision = classify_frame_eligibility(frame)
    assert decision.highest_role == "si"
    assert "geometry_incomplete" in decision.reasons


def test_hdf5_reader_reports_typed_dataset_error(tmp_path) -> None:
    import h5py
    from polynexus.core.saxs_engine.io import UnsupportedDatasetError, read_image

    path = tmp_path / "empty.nxs"
    with h5py.File(path, "w"):
        pass
    with pytest.raises(UnsupportedDatasetError, match="hdf5_dataset_missing"):
        read_image(str(path))


def test_hdf5_two_column_profile_uses_directory_1d_route(monkeypatch, tmp_path) -> None:
    import h5py
    from polynexus.core.saxs import SAXSEngine
    from polynexus.core.saxs_engine.config import ExperimentCondition
    import polynexus.core.saxs as saxs_module

    path = tmp_path / "frame.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("entry/data", data=np.column_stack((np.linspace(0.1, 0.5, 5), np.ones(5))))
    monkeypatch.setattr(
        saxs_module,
        "scan_experiment_dir",
        lambda *_: [ExperimentCondition(value=0.0, files=[str(path)])],
    )

    engine = SAXSEngine(SAXSConfig())
    assert engine.load(str(tmp_path)) is True
    np.testing.assert_allclose(engine._q_list[0], np.linspace(0.1, 0.5, 5))


def test_strain_scalar_metrics_use_total_channel_not_sector_data(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_strain as strain_module

    q = np.linspace(0.1, 1.4, 48)
    intensity = np.exp(-q**2) + 0.1
    monkeypatch.setattr(
        strain_module,
        "herman_from_sector_data",
        lambda sector, **_kwargs: {
            "f": float(sector["marker"]),
            "f_raw": float(sector["marker"]),
            "f_sub": np.nan,
            "f_eq": np.nan,
        },
    )

    result = strain_module.analyze_strain_series(
        [0.0, 10.0],
        [q, q],
        [intensity, intensity],
        sector_data_list=[{"marker": 0.1}, {"marker": 0.8}],
        cfg=SAXSConfig(q_min=0.1),
    )

    np.testing.assert_allclose(result.Q_star_array[0], result.Q_star_array[1])
    np.testing.assert_allclose(result.Q_star_rel_array, [1.0, 1.0])
    np.testing.assert_allclose(result.f_herman_array, [0.1, 0.8])
    assert all(point.metric_source_channel == "total" for point in result.strain_points)
