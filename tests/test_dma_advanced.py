from __future__ import annotations

import pytest

from polynexus.core.dma_processing import DMATTSSpec, build_dma_master_curve


def test_dma_tts_builds_shifted_master_curve_candidate():
    spec = DMATTSSpec.create(
        reference_temperature=25.0,
        temperatures=(25.0, 35.0),
        shift_factors=(1.0, 10.0),
    )
    result = build_dma_master_curve(
        (
            {"temperature": 25.0, "frequency": (1.0, 2.0), "modulus": (10.0, 20.0)},
            {"temperature": 35.0, "frequency": (1.0, 2.0), "modulus": (12.0, 22.0)},
        ),
        spec,
    )
    assert result["status"] == "computed_with_warning"
    assert result["points"][2]["frequency"] == 10.0
    assert result["reference_temperature"] == 25.0


def test_dma_tts_missing_curve_is_local_unavailable():
    spec = DMATTSSpec.create(reference_temperature=25.0, temperatures=(25.0, 35.0), shift_factors=(1.0, 2.0))
    result = build_dma_master_curve(({"temperature": 25.0, "frequency": (1.0, 2.0), "modulus": (1.0, 2.0)},), spec)
    assert result["status"] == "unavailable"
    assert result["unavailable_reason"] == "tts_temperature_curve_missing"


def test_dma_tts_rejects_nonpositive_shift_factor():
    with pytest.raises(ValueError, match="positive"):
        DMATTSSpec.create(reference_temperature=25.0, temperatures=(25.0,), shift_factors=(0.0,))


def test_dma_tts_can_fit_overlap_shift_factors_deterministically():
    spec = DMATTSSpec.create(
        reference_temperature=25.0,
        temperatures=(25.0, 35.0),
        shift_mode="overlap_least_squares",
    )
    result = build_dma_master_curve(
        (
            {"temperature": 25.0, "frequency": (1.0, 10.0, 100.0), "modulus": (10.0, 20.0, 30.0)},
            {"temperature": 35.0, "frequency": (0.1, 1.0, 10.0), "modulus": (10.0, 20.0, 30.0)},
        ),
        spec,
    )
    assert result["status"] == "computed_with_warning"
    assert result["shift_mode"] == "overlap_least_squares"
    assert len(result["shift_diagnostics"]) == 2
