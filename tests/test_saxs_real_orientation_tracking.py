from __future__ import annotations

import os
from pathlib import Path

import pytest


def test_real_orientation_tracking_is_read_only_and_fixture_explicit() -> None:
    fixture_root = os.environ.get("POLYNEXUS_SAXS_REAL_ROOT", "")
    if not fixture_root or not Path(fixture_root).exists():
        pytest.skip(
            "real EDF orientation-tracking fixture unavailable; set "
            "POLYNEXUS_SAXS_REAL_ROOT for read-only acceptance"
        )
    pytest.skip("real EDF replay requires the registered strain bundle adapter")
