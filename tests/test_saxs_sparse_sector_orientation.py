from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import herman_from_sector_data


def _sparse_sector_payload() -> dict[str, np.ndarray]:
    q = np.linspace(0.3, 1.0, 120)
    q_profile = 0.1 + np.exp(-((q - 0.55) / 0.025) ** 2)
    chi = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    intensity = np.outer(1.0 + 8.0 * np.cos(chi) ** 2, q_profile)
    support = np.ones_like(intensity)
    support[:, :5] = 0.0
    intensity[:, :5] = np.nan
    return {
        "I_2d": intensity,
        "q_2d": q,
        "chi_rad": chi,
        "I_full": q_profile,
        "support_count": support,
    }


def test_sparse_unsupported_sector_bins_do_not_disable_herman() -> None:
    result = herman_from_sector_data(
        _sparse_sector_payload(),
        cfg=SAXSConfig(tensile_axis_deg=0.0),
    )

    assert np.isfinite(result["f_raw"])
    assert np.isfinite(result["f"])
    assert "strain_canonical_sector_payload_invalid" not in result[
        "orientation_evidence"
    ]["reason_codes"]


def test_supported_nonfinite_sector_bin_remains_unusable() -> None:
    payload = _sparse_sector_payload()
    payload["I_2d"][0, 5] = np.nan

    result = herman_from_sector_data(
        payload,
        cfg=SAXSConfig(tensile_axis_deg=0.0),
    )

    assert np.isnan(result["f"])
    assert "strain_canonical_sector_payload_invalid" in result["reason_codes"]
