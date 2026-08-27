from __future__ import annotations

import numpy as np

import polynexus.core.ir  # noqa: F401
from polynexus.core.engine import SUBMODULE_REGISTRY
from polynexus.core.ir_engine import IRConfig, IRSpectrum
import polynexus.core.ir_engine.ir_temperature as ir_temperature


def test_ir_standard_submodule_has_no_pa6_default() -> None:
    spec = next(spec for spec in SUBMODULE_REGISTRY["ir"] if spec.id == "ir.temperature_2d")

    assert spec.config_schema["polymer_name"]["default"] == ""


def test_ir_temperature_series_does_not_inject_pa6(monkeypatch) -> None:
    wavenumber = np.linspace(400.0, 4000.0, 20)
    absorbance = np.sin(wavenumber / 200.0)
    spectra = [
        IRSpectrum(
            wavenumber=wavenumber,
            absorbance=absorbance,
            label="frame-1",
        )
    ]
    captured: list[str] = []

    def fake_analyze_spectrum(spectrum, config, *, label="", polymer_name="", **kwargs):
        captured.append(polymer_name)
        return type(
            "Result",
            (),
            {"polymer_score": np.nan, "parameters": {}, "band_indices": {}},
        )()

    monkeypatch.setattr(ir_temperature, "analyze_spectrum", fake_analyze_spectrum)

    ir_temperature.analyze_temperature_2d_series(spectra, IRConfig(polymer_name=""))

    assert captured == [""]
