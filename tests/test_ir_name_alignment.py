from __future__ import annotations

import numpy as np

from polynexus.core.ir_engine import IRConfig
from polynexus.core.ir_engine.core import IRResult, compute_polymer_band_indices
from polynexus.core.ir_engine.io import IRSpectrum
from polynexus.core.ir_engine.ir_state import IR_CRYSTALLINITY_BANDS, judge_polymer_state


def _spectrum_with_peaks(peaks: dict[float, float]) -> IRSpectrum:
    wn = np.linspace(4000.0, 500.0, 1800)
    absorbance = np.full_like(wn, 0.03)
    for center, height in peaks.items():
        absorbance += height * np.exp(-0.5 * ((wn - center) / 10.0) ** 2)
    return IRSpectrum(label="demo", wavenumber=wn, absorbance=absorbance)


def test_compute_polymer_band_indices_accepts_ipp_alias() -> None:
    spec = _spectrum_with_peaks({998.0: 0.8, 973.0: 0.25})
    indices = compute_polymer_band_indices(spec, "iPP")

    assert "PP_crystalline_998" in indices
    assert indices["PP_crystalline_998"] > 0


def test_ir_state_judgment_accepts_ipp_alias() -> None:
    spec = _spectrum_with_peaks({998.0: 0.8, 841.0: 0.35, 1167.0: 0.4, 973.0: 0.15})
    state = judge_polymer_state(spectrum=spec, polymer_name="iPP")

    assert state["method"] == "ir"
    assert state["state"] in {"semi_crystalline", "crystalline"}
    assert state["confidence"] > 0.0
    assert "PP" in IR_CRYSTALLINITY_BANDS
