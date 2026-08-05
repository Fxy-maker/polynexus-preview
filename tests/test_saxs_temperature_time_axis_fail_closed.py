import json

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def _profile() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.02, 1.8, 80)
    intensity = 180.0 * np.exp(-(q**2) * 2.2) + 8.0
    return q, intensity


def test_mismatched_times_preserves_frames_and_disables_avrami():
    q, intensity = _profile()
    result = analyze_temperature_series(
        [180.0, 170.0],
        [q, q],
        [intensity, intensity],
        times=[0.0],
        cfg=SAXSConfig(),
        exp_type="cooling",
    )

    assert len(result.temp_points) == 2
    # Cooling is sequence-dependent; a malformed time axis must not reorder
    # frames or invent positional seconds.
    assert [point.source_index for point in result.temp_points] == [0, 1]
    assert result.avrami == {
        "valid": False,
        "reason": "temperature_time_axis_length_mismatch",
    }
    json.dumps(result.avrami, allow_nan=False)
