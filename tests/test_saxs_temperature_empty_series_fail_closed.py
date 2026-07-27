import json

import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def test_empty_temperature_series_returns_unusable_structured_result():
    result = analyze_temperature_series([], [], [], cfg=SAXSConfig())

    assert result.temp_points == []
    assert result.temperatures.size == 0
    assert result.guinier_sequence_evidence["level"] == "Unusable"
    assert "guinier_sequence_no_valid_frames" in result.guinier_sequence_evidence["reason_codes"]
    assert set(result.metric_evidence) == {
        "guinier", "porod", "kratky", "invariant", "lamellar"
    }
    assert all(
        evidence["level"] == "Unusable"
        and evidence["reason_codes"] == ["series_no_frames"]
        for evidence in result.metric_evidence.values()
    )
    assert result.sequence_rescue_candidates == []
    json.dumps(result.guinier_sequence_evidence, allow_nan=False)
    json.dumps(result.metric_evidence, allow_nan=False)


def test_empty_temperature_series_keeps_length_mismatch_validation():
    with pytest.raises(ValueError, match="same length"):
        analyze_temperature_series([180.0], [], [], cfg=SAXSConfig())
