from __future__ import annotations

from polynexus.core.rheology_processing import (
    RheologyAdvancedSpec,
    RheologySignalSeries,
    analyze_rheology_advanced,
    compare_cox_merz,
    integrate_thixotropy,
)


def test_cox_merz_comparison_preserves_pointwise_residuals():
    result = compare_cox_merz((1.0, 10.0), (100.0, 10.0), (1.0, 10.0), (90.0, 12.0))
    assert result["status"] == "computed_with_warning"
    assert result["residuals"] == (10.0, -2.0)


def test_thixotropy_integral_requires_monotonic_time():
    result = integrate_thixotropy((0.0, 1.0, 2.0), (10.0, 8.0, 6.0))
    assert result["area"] == 16.0
    invalid = integrate_thixotropy((0.0, 1.0, 0.5), (10.0, 8.0, 6.0))
    assert invalid["status"] == "unavailable"


def test_rheology_advanced_binds_time_response_and_cox_merz_series():
    spec = RheologyAdvancedSpec.create(
        complex_viscosity_measurement_id="complex",
        steady_viscosity_measurement_id="steady",
        thixotropy_measurement_id="thix",
        creep_measurement_id="creep",
        relaxation_measurement_id="relax",
        tts_curve_measurement_ids=("tts25", "tts35"),
        temperatures=(25.0, 35.0),
        shift_factors=(1.0, 10.0),
    )
    signals = (
        RheologySignalSeries.create(measurement_id="complex", signal_kind="complex_viscosity", unit="Pa*s", values=(10, 8, 6), x_values=(1, 2, 3)),
        RheologySignalSeries.create(measurement_id="steady", signal_kind="viscosity", unit="Pa*s", values=(9, 8, 7), x_values=(1, 2, 3)),
        RheologySignalSeries.create(measurement_id="thix", signal_kind="viscosity", unit="Pa*s", values=(10, 8, 6), x_values=(0, 1, 2)),
        RheologySignalSeries.create(measurement_id="creep", signal_kind="compliance", unit="1/Pa", values=(0, 1, 2), x_values=(0, 1, 2)),
        RheologySignalSeries.create(measurement_id="relax", signal_kind="stress", unit="Pa", values=(3, 2, 1), x_values=(0, 1, 2)),
        RheologySignalSeries.create(measurement_id="tts25", signal_kind="viscosity", unit="Pa*s", values=(10, 8, 6), x_values=(1, 2, 3), temperature=25),
        RheologySignalSeries.create(measurement_id="tts35", signal_kind="viscosity", unit="Pa*s", values=(10, 8, 6), x_values=(1, 2, 3), temperature=35),
    )
    result = analyze_rheology_advanced(signals, spec)
    assert result.metrics["cox_merz"]["status"] == "computed_with_warning"
    assert result.metrics["thixotropy"]["area"] == 16.0
    assert result.metrics["creep"]["method"] == "creep_linear_time_fit"
    assert result.metrics["tts"]["status"] == "computed_with_warning"
