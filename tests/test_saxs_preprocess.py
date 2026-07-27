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
