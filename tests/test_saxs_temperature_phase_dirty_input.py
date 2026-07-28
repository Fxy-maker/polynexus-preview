from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.saxs_temperature import (
    TempPhase,
    detect_temperature_phase,
)


def test_temperature_phase_coerces_numeric_strings() -> None:
    expected = detect_temperature_phase(200.0, 0.2, 1.0, 10.0, 8.0, "heating")
    actual = detect_temperature_phase("200", "0.2", "1", "10", "8", "heating")

    assert expected is TempPhase.MELTING
    assert actual is expected


def test_temperature_phase_degrades_malformed_length_inputs_without_raising() -> None:
    result = detect_temperature_phase(200.0, 0.7, 1.0, "bad-length", "bad-solid-length", "heating")

    assert result is TempPhase.MELTING


def test_temperature_phase_keeps_existing_invalid_qstar_fallback() -> None:
    result = detect_temperature_phase(
        "bad-qstar",
        "bad-solid-qstar",
        "bad-solid-qstar",
        10.0,
        8.0,
        "heating",
    )

    assert result is TempPhase.HEATING_SOLID


def test_temperature_phase_accepts_nonfinite_scalars_with_existing_fallbacks() -> None:
    assert detect_temperature_phase(np.nan, np.nan, np.nan, np.nan, np.nan, "heating") is TempPhase.HEATING_SOLID
    assert detect_temperature_phase(np.nan, np.nan, np.nan, np.nan, np.nan, "cooling") is TempPhase.COOLING_MELT


def test_temperature_phase_preserves_cooling_isothermal_and_unknown_branches() -> None:
    assert detect_temperature_phase(200.0, 0.8, 1.0, 10.0, 8.0, "cooling") is TempPhase.CRYSTALLIZATION
    assert detect_temperature_phase(200.0, 0.8, 1.0, 10.0, 8.0, "isothermal") is TempPhase.ISOTHERMAL
    assert detect_temperature_phase(200.0, 0.8, 1.0, 10.0, 8.0, "other") is TempPhase.HEATING_SOLID
