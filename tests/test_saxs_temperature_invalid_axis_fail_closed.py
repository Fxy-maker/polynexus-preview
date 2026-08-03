import json

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def _profile() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.02, 1.8, 80)
    intensity = 180.0 * np.exp(-(q**2) * 2.2) + 8.0
    return q, intensity


def test_invalid_temperature_values_are_retained_as_unresolved_frames():
    q, intensity = _profile()
    result = analyze_temperature_series(
        ["170", "bad", None],
        [q, q, q],
        [intensity, intensity, intensity],
        cfg=SAXSConfig(),
    )

    assert len(result.temp_points) == 3
    assert result.temp_points[0].temperature_C == 170.0
    assert np.isnan(result.temp_points[1].temperature_C)
    assert np.isnan(result.temp_points[2].temperature_C)
    assert [point.source_index for point in result.temp_points] == [0, 1, 2]
    assert result.guinier_sequence_evidence["level"] == "Unusable"
    assert "guinier_sequence_temperature_axis_invalid" in result.guinier_sequence_evidence["reason_codes"]
    json.dumps(result.guinier_sequence_evidence, allow_nan=False)
