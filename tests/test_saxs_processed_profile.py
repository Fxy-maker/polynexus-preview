from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.processed_profile import ProcessedProfile


def test_processed_profile_freezes_arrays_and_exposes_legacy_layers() -> None:
    profile = ProcessedProfile(
        q=[0.1, 0.2],
        raw=[10.0, 8.0],
        normalized=[1.0, 0.8],
        provenance={"source": "canonical"},
    )

    assert profile.analysis_intensity.tolist() == [1.0, 0.8]
    assert profile.to_legacy_payload()["Iq_norm"].tolist() == [1.0, 0.8]
    with pytest.raises(ValueError):
        profile.q[0] = 0.3


def test_processed_profile_keeps_missing_layers_explicit() -> None:
    profile = ProcessedProfile(q=np.array([0.1]), raw=np.array([1.0]))

    payload = profile.to_legacy_payload()

    assert payload["Iq_corrected"] is None
    assert payload["quality_status"] == "OK"


def test_saxs_engine_publishes_canonical_profile_for_static_1d_data() -> None:
    engine = SAXSEngine(SAXSConfig(experiment_type="static"))
    engine._q = np.linspace(0.02, 0.2, 8)
    engine._I = np.asarray([10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0])

    assert engine.preprocess() is True
    assert engine._processed_profile is not None
    assert engine._processed_profile.raw.tolist() == engine._I.tolist()
    assert engine._processed_profile.smoothed is not None
    assert engine.result.raw_data["processed_profile"] is engine._processed_profile
