from __future__ import annotations

import numpy as np

from polynexus.core.saxs_engine import guinier_analysis


def test_guinier_discards_dirty_pairs_and_fits_sorted_survivors() -> None:
    clean_q = np.arange(0.1, 1.3, 0.1)
    clean_i = 100.0 * np.exp(-(clean_q**2) * 4.0 / 3.0)
    dirty_q = np.array(
        [0.5, "bad-q", 0.1, 0.9, -0.2, 1.2, 0.3, np.nan,
         0.8, 0.4, 0.7, 1.0, 0.2, 0.6, 1.1],
        dtype=object,
    )
    dirty_i = np.array(
        [clean_i[4], clean_i[0], clean_i[0], clean_i[8], clean_i[3],
         clean_i[11], clean_i[2], clean_i[7], clean_i[7], clean_i[3],
         clean_i[6], clean_i[9], clean_i[1], clean_i[5], clean_i[10]],
        dtype=object,
    )

    rg, i0, q_fit, ln_i = guinier_analysis(dirty_q, dirty_i)
    clean_rg, clean_i0, clean_q_fit, clean_ln_i = guinier_analysis(clean_q, clean_i)

    assert np.isfinite(rg)
    assert np.isfinite(i0)
    assert np.all(np.isfinite(q_fit))
    assert np.all(q_fit > 0)
    assert np.all(np.diff(q_fit) >= 0)
    np.testing.assert_allclose((rg, i0), (clean_rg, clean_i0))
    np.testing.assert_allclose(q_fit, clean_q_fit)
    np.testing.assert_allclose(ln_i, clean_ln_i)


def test_guinier_empty_or_invalid_profile_keeps_nan_empty_contract() -> None:
    rg, i0, q_fit, ln_i = guinier_analysis(["bad", -1.0], [np.nan, 0.0])

    assert np.isnan(rg)
    assert np.isnan(i0)
    assert q_fit.size == 0
    assert ln_i.size == 0


def test_guinier_does_not_mutate_caller_arrays() -> None:
    q = np.array([0.3, 0.1, 0.2] + [0.4 + i * 0.1 for i in range(9)])
    intensity = np.linspace(5.0, 1.0, q.size)
    q_before = q.copy()
    intensity_before = intensity.copy()

    guinier_analysis(q, intensity)

    np.testing.assert_array_equal(q, q_before)
    np.testing.assert_array_equal(intensity, intensity_before)
