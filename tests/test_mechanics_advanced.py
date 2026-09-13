from __future__ import annotations

from polynexus.core.mechanics_processing import (
    analyze_mechanics_cycles,
    analyze_mechanics_fatigue,
    integrate_fracture_energy,
    integrate_mechanics_creep,
)


def test_mechanics_cycle_and_fatigue_candidates():
    cycles = analyze_mechanics_cycles((1, 1, 2, 2), (10, 8, 9, 7))
    assert cycles["peak_response"] == (10.0, 9.0)
    fatigue = analyze_mechanics_fatigue((1, 2, 3), (10, 9, 7))
    assert fatigue["status"] == "computed_with_warning"


def test_mechanics_creep_and_fracture_integrals():
    assert integrate_mechanics_creep((0, 1, 2), (0, 2, 2))["area"] == 3.0
    assert integrate_fracture_energy((0, 1, 2), (0, 2, 0))["energy"] == 2.0
