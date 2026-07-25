from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.dsc import DSCEngine
from polynexus.core.dsc_engine.core import DSCResult
from polynexus.core.ir import IREngine
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.waxs import WAXSEngine
from polynexus.core.waxs_engine.core import WAXSResult


def test_dsc_analyze_attaches_unified_analysis_evidence(monkeypatch):
    monkeypatch.setattr(
        "polynexus.core.dsc.analyze_scan",
        lambda *_args, **_kwargs: DSCResult(
            label="scan-1",
            Tm_peak_C=220.0,
            Xc_pct=35.0,
            r_squared=0.98,
        ),
    )
    engine = DSCEngine()
    engine._scans = [
        SimpleNamespace(
            label="scan-1",
            metadata={},
            T_C=np.array([100.0, 200.0]),
            HF_Wg=np.array([0.0, 1.0]),
            t_min=np.array([0.0, 1.0]),
        )
    ]

    assert engine.analyze() is True
    assert engine.result.analysis_evidence["technique"] == "DSC"


def test_waxs_analyze_attaches_unified_analysis_evidence(monkeypatch):
    monkeypatch.setattr(
        "polynexus.core.waxs.analyze_scan",
        lambda *_args, **_kwargs: WAXSResult(
            label="scan-1",
            Xc_pct=35.0,
            n_peaks=2,
            r_squared=0.98,
        ),
    )
    engine = WAXSEngine()
    engine._dataset = SimpleNamespace(scans=[SimpleNamespace(label="scan-1")])

    assert engine.analyze() is True
    assert engine.result.analysis_evidence["technique"] == "WAXS"


def test_ir_analyze_attaches_unified_analysis_evidence(monkeypatch):
    monkeypatch.setattr(
        "polynexus.core.ir.analyze_spectrum",
        lambda *_args, **_kwargs: IRResult(
            label="scan-1",
            n_peaks=3,
            polymer_name="PA6",
            Xc_pct=20.0,
            r_squared=0.99,
        ),
    )
    engine = IREngine()
    engine._spectra = [
        SimpleNamespace(
            label="scan-1",
            wavenumber=np.array([1800.0, 1700.0]),
            absorbance=np.array([0.1, 0.2]),
        )
    ]

    assert engine.analyze() is True
    assert engine.result.analysis_evidence["technique"] == "IR"
