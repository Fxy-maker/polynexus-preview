from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import LongPeriodResult, StructureParams
from polynexus.core.saxs_engine.saxs_quality_contracts import (
    build_data_quality_report,
)
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


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
        guinier_evidence=None,
        data_quality_report=report.to_dict(),
        metric_evidence={},
        detector_quality_report=None,
        orientation_evidence=None,
    )


def test_temperature_postprocessing_uses_surviving_profile_and_keeps_quality_actions(
    monkeypatch,
) -> None:
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.array([0.04, np.nan, 0.02, 0.03], dtype=float)
    intensity = np.array([4.0, 5.0, -1.0, 3.0], dtype=float)
    seen: list[tuple[np.ndarray, np.ndarray]] = []
    bragg_seen: list[tuple[np.ndarray, np.ndarray]] = []
    peak_seen: list[np.ndarray] = []
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
        seen.append((q_values.copy(), intensity_values.copy()))
        return 2.0

    def fake_analyze(
        q_values: np.ndarray,
        intensity_values: np.ndarray,
        cfg: SAXSConfig,
    ) -> SimpleNamespace:
        del cfg
        original_seen.append((q_values.copy(), intensity_values.copy()))
        return _fake_frame_result(q_values, intensity_values)

    def checked_bragg(
        q_values: np.ndarray,
        intensity_values: np.ndarray,
    ) -> tuple[float, float, dict]:
        assert np.all(np.isfinite(q_values))
        assert np.all(q_values > 0)
        assert np.all(np.isfinite(intensity_values))
        assert np.all(intensity_values > 0)
        bragg_seen.append((q_values.copy(), intensity_values.copy()))
        return 10.0, 0.6, {}

    def capture_melting(
        temperatures: np.ndarray,
        long_period: np.ndarray,
        peak_intensity: np.ndarray,
    ) -> dict:
        del temperatures, long_period
        peak_seen.append(peak_intensity.copy())
        return {}

    monkeypatch.setattr(
        module,
        "analyze_single",
        fake_analyze,
    )
    monkeypatch.setattr(module, "scattering_invariant", checked_invariant)
    monkeypatch.setattr(module, "bragg_long_period", checked_bragg)
    monkeypatch.setattr(module, "detect_melting_from_saxs", capture_melting)

    result = analyze_temperature_series(
        [170.0, 180.0],
        [q, q.copy()],
        [intensity, intensity.copy()],
        cfg=SAXSConfig(),
    )

    assert result.Q_star_array.tolist() == [2.0, 2.0]
    assert seen
    assert bragg_seen
    assert len(peak_seen) == 1
    assert np.array_equal(peak_seen[0], np.array([4.0, 4.0]))
    assert original_seen
    assert np.isnan(original_seen[0][0][1])
    assert original_seen[0][1][2] == -1.0
    assert result.temp_points[0].data_quality_report is not None
    assert "invalid_pairs_dropped" in result.temp_points[0].data_quality_report[
        "actions"
    ]
    assert "q_sorted" in result.temp_points[0].data_quality_report["actions"]


def test_empty_sanitized_temperature_frame_remains_fail_closed(monkeypatch) -> None:
    import polynexus.core.saxs_engine.saxs_temperature as module

    q = np.array([np.nan, -0.02], dtype=float)
    intensity = np.array([1.0, -2.0], dtype=float)

    monkeypatch.setattr(
        module,
        "analyze_single",
        lambda q_values, intensity_values, cfg: _fake_frame_result(
            q_values, intensity_values
        ),
    )
    monkeypatch.setattr(
        module,
        "scattering_invariant",
        lambda q_values, intensity_values, *, cfg: np.nan,
    )
    monkeypatch.setattr(
        module,
        "bragg_long_period",
        lambda q_values, intensity_values: (np.nan, np.nan, {}),
    )

    result = analyze_temperature_series([170.0], [q], [intensity], cfg=SAXSConfig())

    assert np.isnan(result.Q_star_array[0])
    assert "temperature_frame_invariant_unavailable" in result.temp_points[0].warnings
    assert "invalid_pairs_dropped" in result.temp_points[0].data_quality_report[
        "actions"
    ]
