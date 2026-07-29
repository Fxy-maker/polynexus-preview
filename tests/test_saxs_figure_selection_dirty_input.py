from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.saxs_engine.figure_common import SAXSFrameView
from polynexus.core.saxs_engine.figure_selection import _intensity_features


def test_intensity_features_keep_finite_pairs_from_malformed_profile() -> None:
    frame = SAXSFrameView(
        index=0,
        label="dirty",
        condition=100.0,
        q=np.asarray([0.1, "bad-q", 0.3, 0.4], dtype=object),
        intensity=np.asarray([2.0, 3.0, 4.0, "bad-intensity"], dtype=object),
        analysis=SimpleNamespace(),
        parameters={},
    )

    area, maximum = _intensity_features(frame)

    assert area == 0.6
    assert maximum == 4.0
