from __future__ import annotations

from polynexus.core.rheology_processing import compare_cox_merz, integrate_thixotropy


def test_cox_merz_comparison_preserves_pointwise_residuals():
    result = compare_cox_merz((1.0, 10.0), (100.0, 10.0), (1.0, 10.0), (90.0, 12.0))
    assert result["status"] == "computed_with_warning"
    assert result["residuals"] == (10.0, -2.0)


def test_thixotropy_integral_requires_monotonic_time():
    result = integrate_thixotropy((0.0, 1.0, 2.0), (10.0, 8.0, 6.0))
    assert result["area"] == 16.0
    invalid = integrate_thixotropy((0.0, 1.0, 0.5), (10.0, 8.0, 6.0))
    assert invalid["status"] == "unavailable"
