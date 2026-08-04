from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import analyze_single


def _profile_with_invalid_low_q_prefix() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.05, 1.8, 240)
    intensity = 2.0 + 0.2 * np.sin(q * 8.0)
    intensity[:12] = np.linspace(2.0e5, 1.2e4, 12)
    return q, intensity


def _profile_with_materially_higher_edge() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.05, 1.8, 240)
    intensity = 2.0 + 0.2 * np.sin(q * 8.0)
    intensity[q < 0.17] = 2.0e4
    return q, intensity


def test_configured_q_min_trims_prefix_and_downgrades_known_truncation() -> None:
    q, intensity = _profile_with_invalid_low_q_prefix()
    result = analyze_single(
        q,
        intensity,
        SAXSConfig(experiment_type="strain", q_min=0.125),
    )

    assert result.q[0] >= 0.125
    assert result.correlation["q_raw"][0] >= 0.125
    assert result.kratky["q"][0] >= 0.125
    assert result.beam_stop_contaminated is False
    assert "ERROR:qstar_contaminated" not in result.quality_flag
    assert "WARN:mask_truncated" in result.quality_flag


def test_auto_detected_edge_above_configured_q_min_remains_hard_contamination() -> None:
    q, intensity = _profile_with_invalid_low_q_prefix()
    result = analyze_single(
        q,
        intensity,
        SAXSConfig(experiment_type="strain", q_min=0.05),
    )

    assert result.beam_stop_contaminated is True
    assert "ERROR:qstar_contaminated" in result.quality_flag
    assert result.effective_q_min > 0.05


def test_materially_higher_edge_remains_hard_after_configured_trimming() -> None:
    q, intensity = _profile_with_materially_higher_edge()
    result = analyze_single(
        q,
        intensity,
        SAXSConfig(experiment_type="strain", q_min=0.125),
    )

    assert result.beam_stop_contaminated is True
    assert "ERROR:qstar_contaminated" in result.quality_flag
    assert result.effective_q_min > 0.125
