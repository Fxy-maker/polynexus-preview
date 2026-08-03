from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.core import analyze_single


def test_limited_q_profile_returns_structured_result_instead_of_unbound_local():
    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)

    result = analyze_single(q, intensity, SAXSConfig())

    assert result.structure is not None
    assert result.data_quality_report is not None
    assert result.guinier_evidence is not None
