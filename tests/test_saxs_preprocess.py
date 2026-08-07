from __future__ import annotations

import numpy as np


def test_preprocess_pipeline_emits_canonical_azimuthal_payload_without_pyfai(monkeypatch) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    cfg = SAXSConfig(
        experiment_type="strain",
        beam_center_x=16.0,
        beam_center_y=16.0,
        pixel_size_m=1.0e-4,
        sdd_m=0.45,
        n_pt=24,
        n_chi_sectors=12,
        smooth_method="none",
    )
    image = np.ones((32, 32), dtype=float)
    image[16, 24] = 8.0

    processed = preprocess_module.preprocess_pipeline(image, cfg)
    sector_data = processed["sector_data"]

    assert sector_data["I_2d"].shape == (cfg.n_chi_sectors, cfg.n_pt)
    assert sector_data["q_2d"].shape == (cfg.n_pt,)
    assert sector_data["chi_rad"].shape == (cfg.n_chi_sectors,)
    assert np.all(np.isfinite(sector_data["chi_rad"]))
    assert np.any(sector_data["I_2d"] > 0)
    assert sector_data["support_count"].shape == sector_data["I_2d"].shape
    assert sector_data["sector_empty_bin_mask"].shape == sector_data["I_2d"].shape
    assert sector_data["sector_integration_backend"] == "numpy"
    assert sector_data["raw_detector_quality_report"] == processed["detector_quality_report"]
    assert sector_data["raw_detector_quality_report"] is not processed["detector_quality_report"]


def test_preprocess_pipeline_keeps_isotropic_input_without_orientation_payload(monkeypatch) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    cfg = SAXSConfig(
        is_isotropic=True,
        beam_center_x=16.0,
        beam_center_y=16.0,
        pixel_size_m=1.0e-4,
        sdd_m=0.45,
        n_pt=24,
        smooth_method="none",
    )

    processed = preprocess_module.preprocess_pipeline(np.ones((32, 32), dtype=float), cfg)

    assert "I_2d" not in processed["sector_data"]


def test_chi_halfwidth_changes_anisotropic_sector_output_without_pyfai(monkeypatch) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    size = 101
    center = 50.0
    y, x = np.indices((size, size), dtype=float)
    chi = np.degrees(np.arctan2(y - center, x - center))
    off_axis = (np.abs(chi) >= 20.0) & (np.abs(chi) <= 30.0)
    opposite = (np.abs(chi) >= 150.0) & (np.abs(chi) <= 160.0)
    image = np.ones((size, size), dtype=float)
    image[off_axis | opposite] = 20.0
    common = dict(
        experiment_type="strain",
        is_isotropic=False,
        analysis_priority="anisotropic",
        beam_center_x=center,
        beam_center_y=center,
        pixel_size_m=1.0e-4,
        sdd_m=0.45,
        q_min=0.01,
        q_max=0.6,
        n_pt=32,
        n_chi_sectors=12,
        smooth_method="none",
    )

    narrow = preprocess_module.preprocess_pipeline(
        image,
        SAXSConfig(
            **common,
            chi_halfwidth=5.0,
            chi_halfwidth_authoritative=True,
        ),
    )
    wide = preprocess_module.preprocess_pipeline(
        image,
        SAXSConfig(
            **common,
            chi_halfwidth=35.0,
            chi_halfwidth_authoritative=True,
        ),
    )

    assert np.nanmean(wide["Iq_equat"]) > np.nanmean(narrow["Iq_equat"])


def test_custom_legacy_sector_ranges_remain_authoritative_by_default() -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig

    config = SAXSConfig(
        chi_halfwidth=15.0,
        chi_merid_range=(62.0, 118.0),
        chi_equat_range=(-8.0, 12.0),
    )

    assert preprocess_module._sector_azimuth_range(config, "meridional") == (
        62.0,
        118.0,
    )
    assert preprocess_module._sector_azimuth_range(config, "equatorial") == (
        -8.0,
        12.0,
    )


def test_explicit_halfwidth_authority_uses_centered_sector_ranges() -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig

    config = SAXSConfig(
        chi_halfwidth=12.0,
        chi_halfwidth_authoritative=True,
        chi_merid_center=88.0,
        chi_equat_center=3.0,
        chi_merid_range=(62.0, 118.0),
        chi_equat_range=(-8.0, 12.0),
    )

    assert preprocess_module._sector_azimuth_range(config, "meridional") == (
        76.0,
        100.0,
    )
    assert preprocess_module._sector_azimuth_range(config, "equatorial") == (
        -9.0,
        15.0,
    )


def test_scalar_mask_dilation_changes_effective_mask_and_integration_support(
    monkeypatch,
) -> None:
    from polynexus.core.saxs_engine import preprocess as preprocess_module
    from polynexus.core.saxs_engine.config import SAXSConfig

    monkeypatch.setattr(preprocess_module, "build_integrator", lambda _cfg: None)
    image = np.ones((41, 41), dtype=float)
    image[20, 30] = -1.5
    image[19:22, 29:32] = 100.0
    image[20, 30] = -1.5
    common = dict(
        experiment_type="strain",
        is_isotropic=False,
        analysis_priority="anisotropic",
        beam_center_x=20.0,
        beam_center_y=20.0,
        pixel_size_m=1.0e-4,
        sdd_m=0.45,
        q_min=0.01,
        q_max=0.5,
        n_pt=24,
        n_chi_sectors=12,
        smooth_method="none",
        dummy_val=-1.5,
        ddummy=0.01,
    )

    baseline = preprocess_module.preprocess_pipeline(
        image,
        SAXSConfig(**common, mask_dilation_px=0),
    )
    dilated = preprocess_module.preprocess_pipeline(
        image,
        SAXSConfig(**common, mask_dilation_px=1),
    )

    assert baseline["mask_edit_base_mask"].sum() == 1
    assert dilated["mask_edit_base_mask"].sum() > 1
    assert np.nansum(dilated["sector_data"]["support_count"]) < np.nansum(
        baseline["sector_data"]["support_count"]
    )
    assert not np.allclose(
        baseline["Iq"],
        dilated["Iq"],
        equal_nan=True,
    )
