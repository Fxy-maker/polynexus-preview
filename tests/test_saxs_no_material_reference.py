from __future__ import annotations

import numpy as np

from polynexus.core.saxs import _select_static_reference_index


def test_static_reference_selection_uses_first_finite_invariant_not_filename() -> None:
    q_values = [10.0, 20.0, 30.0]
    file_list = ["sample-a.edf", "PA6-control.edf", "sample-c.edf"]

    assert _select_static_reference_index(q_values, file_list) == 0


def test_static_reference_selection_skips_nonfinite_values_in_order() -> None:
    assert _select_static_reference_index([np.nan, 4.0], ["a.edf", "b.edf"]) == 1


def test_static_reference_selection_falls_back_to_first_frame() -> None:
    assert _select_static_reference_index([np.nan, np.nan], ["a.edf", "PA6.edf"]) == 0
