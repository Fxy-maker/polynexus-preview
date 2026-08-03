from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_strain import StrainPhase, analyze_strain_series


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


def test_invalid_strain_axis_is_retained_and_reported_as_diagnostic(monkeypatch) -> None:
    _patch_profile_consumers(monkeypatch)
    q = np.array([0.02, 0.03, 0.04], dtype=float)
    intensity = np.array([2.0, 3.0, 4.0], dtype=float)

    result = analyze_strain_series(
        ["0", "bad", np.inf],
        [q, q, q],
        [intensity, intensity, intensity],
        cfg=SAXSConfig(),
    )

    assert result.strains[0] == 0.0
    assert np.isnan(result.strains[1:]).all()
    assert len(result.strain_points) == 3
    assert np.isnan(result.strain_points[1].strain_pct)
    assert np.isnan(result.strain_points[2].strain_pct)
    for evidence in result.metric_evidence.values():
        axis = evidence["condition_axis"]
        assert axis["condition_name"] == "strain_pct"
        assert axis["invalid_condition_indices"] == [1, 2]
        assert axis["status"] == "diagnostic"
        assert "series_metric_condition_axis_invalid" in evidence["reason_codes"]
    assert result.phase_boundaries == {StrainPhase.ELASTIC: 0.0}


def test_empty_strain_series_returns_unusable_evidence_without_reference_indexing() -> None:
    result = analyze_strain_series([], [], [], cfg=SAXSConfig())

    assert result.strains.size == 0
    assert result.strain_points == []
    assert result.phase_boundaries == {}
    for evidence in result.metric_evidence.values():
        assert evidence["level"] == "Unusable"
        assert "series_no_frames" in evidence["reason_codes"]
