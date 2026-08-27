from __future__ import annotations

from polynexus.core.ir_engine.config import IRConfig
from polynexus.core.ir_engine.core import IRSpectrum, analyze_spectrum


def _spectrum() -> IRSpectrum:
    x = [float(value) for value in range(1800, 1599, -1)]
    y = [0.01] * len(x)
    for center, height in ((1650, 1.0), (1630, 0.7), (1605, 0.4)):
        y[1800 - center] = height
    return IRSpectrum(wavenumber=x, absorbance=y, metadata={"source": "test"})


def test_ftir_without_material_hint_does_not_claim_polymer_identity() -> None:
    result = analyze_spectrum(_spectrum(), IRConfig(polymer_name=""))

    assert result.peaks
    assert result.polymer_name == ""
    assert all(not peak.get("polymer") for peak in result.peaks)


def test_ftir_explicit_material_hint_keeps_scoped_assignment() -> None:
    result = analyze_spectrum(_spectrum(), IRConfig(polymer_name="PA6"))

    assert result.polymer_name == "PA6"
