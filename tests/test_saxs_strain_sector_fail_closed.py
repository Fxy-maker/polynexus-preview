from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPhase,
    analyze_strain_series,
    herman_from_sector_data,
)


def _fake_frame_result() -> SimpleNamespace:
    return SimpleNamespace(
        long_period=SimpleNamespace(L_best=10.0, L_confidence=0.8, method_used="bragg"),
        structure=SimpleNamespace(lc=3.0, la=7.0, phi_c=0.3),
        data_quality_report={},
        metric_evidence={},
        detector_quality_report=None,
        orientation_evidence=None,
    )


def _patch_profile_consumers(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_strain as module

    monkeypatch.setattr(module, "analyze_single", lambda q, intensity, cfg: _fake_frame_result())
    monkeypatch.setattr(module, "scattering_invariant", lambda q, intensity, *, cfg: 2.0)
    monkeypatch.setattr(
        module,
        "detect_strain_phase",
        lambda strain, q_star, q_ref, q, intensity, cfg: StrainPhase.ELASTIC,
    )
    monkeypatch.setattr(
        module,
        "detect_voids",
        lambda q, intensity, cfg: {
            "has_voids": False,
            "phi_void": np.nan,
            "void_ar": np.nan,
        },
    )


def test_malformed_nested_sector_data_returns_unusable_orientation_evidence() -> None:
    result = herman_from_sector_data({"meridional": None, "equatorial": {}})

    assert np.isnan(result["f"])
    evidence = result["orientation_evidence"]
    assert evidence["level"] == "Unusable"
    assert "strain_sector_data_invalid" in evidence["reason_codes"]
    assert evidence["physical_checks"]["input_validation_reason"] == (
        "strain_sector_data_invalid"
    )
    assert result["detector_quality_report"]["level"] == "Unusable"


def test_malformed_sector_frame_does_not_abort_strain_series(monkeypatch) -> None:
    _patch_profile_consumers(monkeypatch)
    q = np.array([0.02, 0.03, 0.04], dtype=float)
    intensity = np.array([2.0, 3.0, 4.0], dtype=float)

    result = analyze_strain_series(
        [0.0],
        [q],
        [intensity],
        sector_data_list=[{"meridional": None}],
        cfg=SAXSConfig(),
    )

    assert len(result.strain_points) == 1
    assert result.strain_points[0].L_nm == 10.0
    assert result.strain_points[0].orientation_evidence["level"] == "Unusable"
    assert "strain_sector_data_invalid" in result.strain_points[0].orientation_evidence[
        "reason_codes"
    ]
    assert result.orientation_evidence["level"] == "Unusable"
