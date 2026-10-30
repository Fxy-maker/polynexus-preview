from __future__ import annotations

import math

import pytest

from polynexus.core.tga_processing import (
    TGAKineticsSpec,
    analyze_tga_isoconversional_kinetics,
    analyze_tga_multirate_kinetics,
)


def test_tga_multirate_kissinger_candidate_is_deterministic():
    spec = TGAKineticsSpec.create(heating_rates=(5.0, 10.0, 20.0))
    result = analyze_tga_multirate_kinetics((500.0, 510.0, 520.0), spec)
    assert result["status"] == "computed_with_warning"
    assert result["method"] == "kissinger_linear_fit"
    assert math.isfinite(result["activation_energy_J_mol"])
    assert len(result["residuals"]) == 3


def test_tga_multirate_missing_peak_is_local_unavailable():
    spec = TGAKineticsSpec.create(heating_rates=(5.0, 10.0))
    result = analyze_tga_multirate_kinetics((500.0,), spec)
    assert result == {"status": "unavailable", "unavailable_reason": "peak_temperature_count_mismatch"}


def test_tga_kinetics_spec_rejects_invalid_rates():
    with pytest.raises(ValueError, match="at least two"):
        TGAKineticsSpec.create(heating_rates=(5.0,))


def test_tga_isoconversional_candidate_preserves_conversion_metadata():
    spec = TGAKineticsSpec.create(
        heating_rates=(5.0, 10.0, 20.0),
        conversion_levels=(0.2, 0.5),
        curve_measurement_ids=("a", "b", "c"),
    )
    curves = tuple(
        {
            "measurement_id": identifier,
            "temperature_K": tuple(value + offset for value in (300.0, 400.0, 500.0, 600.0)),
            "mass": (100.0, 90.0, 60.0, 20.0),
        }
        for identifier, offset in (("a", 0.0), ("b", 12.0), ("c", 25.0))
    )
    result = analyze_tga_isoconversional_kinetics(curves, spec)
    assert result["status"] == "computed_with_warning"
    assert result["source_measurement_ids"] == ["a", "b", "c"]
    assert result["conversion_levels"]["conversion_0.2"]["method"] == "ozawa_flynn_wall_linear_fit"
