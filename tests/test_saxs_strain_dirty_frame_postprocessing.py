from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import LongPeriodResult, StructureParams
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_data_quality_report,
)
from polynexus.core.saxs_engine.saxs_strain import (
    StrainPhase,
    analyze_strain_series,
)


def _fake_frame_result(q: np.ndarray, intensity: np.ndarray) -> SimpleNamespace:
    report = build_data_quality_report(
        q,
        intensity,
        actions=("invalid_pairs_dropped", "q_sorted"),
    )
    return SimpleNamespace(
        long_period=LongPeriodResult(
            L_best=10.0,
            L_confidence=0.8,
            method_used="bragg",
        ),
        structure=StructureParams(
            L=10.0,
            lc=3.0,
            la=7.0,
            phi_c=0.3,
            confidence_lc=0.8,
        ),
        data_quality_report=report.to_dict(),
        metric_evidence={},
        detector_quality_report=None,
        orientation_evidence=None,
    )


def test_strain_postprocessing_uses_sanitized_profile_and_keeps_quality_actions(
    monkeypatch,
) -> None:
    import polynexus.core.saxs_engine.saxs_strain as module

    q = np.array([0.04, np.nan, 0.02, 0.03], dtype=float)
    intensity = np.array([4.0, 5.0, -1.0, 3.0], dtype=float)
    invariant_seen: list[tuple[np.ndarray, np.ndarray]] = []
    phase_seen: list[tuple[np.ndarray, np.ndarray]] = []
    void_seen: list[tuple[np.ndarray, np.ndarray]] = []
    original_seen: list[tuple[np.ndarray, np.ndarray]] = []

    def checked_invariant(
        q_values: np.ndarray,
        intensity_values: np.ndarray,
        *,
        cfg: SAXSConfig,
    ) -> float:
        del cfg
        assert np.all(np.isfinite(q_values))
        assert np.all(q_values > 0)
        assert np.all(np.isfinite(intensity_values))
        assert np.all(intensity_values > 0)
        assert np.all(np.diff(q_values) >= 0)
        invariant_seen.append((q_values.copy(), intensity_values.copy()))
        return 2.0

    def checked_phase(
        strain_pct: float,
        q_star: float,
        q_star_ref: float,
        q_values: np.ndarray,
        intensity_values: np.ndarray,
        cfg: SAXSConfig,
    ) -> StrainPhase:
        del strain_pct, q_star, q_star_ref, cfg
        assert np.all(np.isfinite(q_values))
        assert np.all(q_values > 0)
        assert np.all(np.isfinite(intensity_values))
        assert np.all(intensity_values > 0)
        assert np.all(np.diff(q_values) >= 0)
        phase_seen.append((q_values.copy(), intensity_values.copy()))
        return StrainPhase.ELASTIC

    def checked_voids(
        q_values: np.ndarray,
        intensity_values: np.ndarray,
        cfg: SAXSConfig,
    ) -> dict:
        del cfg
        assert np.all(np.isfinite(q_values))
        assert np.all(q_values > 0)
        assert np.all(np.isfinite(intensity_values))
        assert np.all(intensity_values > 0)
        assert np.all(np.diff(q_values) >= 0)
        void_seen.append((q_values.copy(), intensity_values.copy()))
        return {"has_voids": False, "phi_void": np.nan, "void_ar": np.nan}

    def fake_analyze(
        q_values: np.ndarray,
        intensity_values: np.ndarray,
        cfg: SAXSConfig,
    ) -> SimpleNamespace:
        del cfg
        original_seen.append((q_values.copy(), intensity_values.copy()))
        return _fake_frame_result(q_values, intensity_values)

    monkeypatch.setattr(module, "analyze_single", fake_analyze)
    monkeypatch.setattr(module, "scattering_invariant", checked_invariant)
    monkeypatch.setattr(module, "detect_strain_phase", checked_phase)
    monkeypatch.setattr(module, "detect_voids", checked_voids)

    result = analyze_strain_series(
        [0.0, 5.0],
        [q, q.copy()],
        [intensity, intensity.copy()],
        cfg=SAXSConfig(),
    )

    assert result.Q_star_array.tolist() == [2.0, 2.0]
    assert len(invariant_seen) == 3  # reference plus one call per frame
    assert len(phase_seen) == 2
    assert len(void_seen) == 2
    assert original_seen
    assert np.isnan(original_seen[0][0][1])
    assert original_seen[0][1][2] == -1.0
    assert result.strain_points[0].data_quality_report is not None
    assert "invalid_pairs_dropped" in result.strain_points[0].data_quality_report[
        "actions"
    ]
    assert "q_sorted" in result.strain_points[0].data_quality_report["actions"]


def test_empty_sanitized_strain_frame_remains_unavailable(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_strain as module

    q = np.array([np.nan, -0.02], dtype=float)
    intensity = np.array([1.0, -2.0], dtype=float)
    seen: list[tuple[np.ndarray, np.ndarray]] = []

    monkeypatch.setattr(
        module,
        "analyze_single",
        lambda q_values, intensity_values, cfg: _fake_frame_result(
            q_values, intensity_values
        ),
    )

    def empty_invariant(
        q_values: np.ndarray,
        intensity_values: np.ndarray,
        *,
        cfg: SAXSConfig,
    ) -> float:
        del cfg
        seen.append((q_values.copy(), intensity_values.copy()))
        assert q_values.size == 0
        assert intensity_values.size == 0
        return np.nan

    monkeypatch.setattr(module, "scattering_invariant", empty_invariant)
    monkeypatch.setattr(
        module,
        "detect_strain_phase",
        lambda strain, q_star, q_ref, q_values, intensity_values, cfg: StrainPhase.ELASTIC,
    )
    monkeypatch.setattr(
        module,
        "detect_voids",
        lambda q_values, intensity_values, cfg: {
            "has_voids": False,
            "phi_void": np.nan,
            "void_ar": np.nan,
        },
    )

    result = analyze_strain_series([0.0], [q], [intensity], cfg=SAXSConfig())

    assert len(seen) == 2  # reference and frame invariant
    assert np.isnan(result.Q_star_array[0])
    assert np.isnan(result.strain_points[0].phi_void)
    assert "invalid_pairs_dropped" in result.strain_points[0].data_quality_report[
        "actions"
    ]


def test_clean_strain_profiles_keep_existing_frame_order(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_strain as module

    q_first = np.array([0.02, 0.03, 0.04], dtype=float)
    q_second = q_first + 0.01
    i_first = np.array([2.0, 3.0, 4.0], dtype=float)
    i_second = i_first + 1.0
    seen: list[tuple[np.ndarray, np.ndarray]] = []

    monkeypatch.setattr(
        module,
        "analyze_single",
        lambda q_values, intensity_values, cfg: (
            seen.append((q_values.copy(), intensity_values.copy()))
            or _fake_frame_result(q_values, intensity_values)
        ),
    )
    monkeypatch.setattr(
        module,
        "scattering_invariant",
        lambda q_values, intensity_values, *, cfg: 2.0,
    )
    monkeypatch.setattr(
        module,
        "detect_strain_phase",
        lambda strain, q_star, q_ref, q_values, intensity_values, cfg: StrainPhase.ELASTIC,
    )
    monkeypatch.setattr(
        module,
        "detect_voids",
        lambda q_values, intensity_values, cfg: {
            "has_voids": False,
            "phi_void": np.nan,
            "void_ar": np.nan,
        },
    )

    result = analyze_strain_series(
        [5.0, 0.0],
        [q_first, q_second],
        [i_first, i_second],
        cfg=SAXSConfig(),
    )

    assert result.strains.tolist() == [5.0, 0.0]
    assert [point.strain_pct for point in result.strain_points] == [5.0, 0.0]
    assert np.array_equal(seen[0][0], q_first)
    assert np.array_equal(seen[1][0], q_second)
