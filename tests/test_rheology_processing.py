from __future__ import annotations

import math

import numpy as np

from polynexus.core.rheology_processing import (
    RheologySignalSeries,
    analyze_rheology_group,
)


def test_steady_shear_stress_over_axis_rate_preserves_zero_rate_mask() -> None:
    shear_rate = np.asarray((0.0, 1.0, 10.0, 100.0))
    stress = np.asarray((0.0, 10.0, 50.0, 200.0))
    stress_before = stress.copy()

    outcome = analyze_rheology_group(
        shear_rate,
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="stress",
                signal_kind="shear_stress",
                unit="Pa",
                values=stress,
            ),
        ),
    )

    viscosity = outcome.metrics["derived_apparent_viscosity"]
    assert viscosity["status"] == "computed_with_warning"
    assert viscosity["values"] == (None, 10.0, 5.0, 2.0)
    assert viscosity["validity_mask"] == (False, True, True, True)
    assert viscosity["unit"] == "Pa*s"
    assert viscosity["method"] == "shear_stress_divided_by_shear_rate"
    assert viscosity["warnings"] == ("shear_rate_zero_at_some_points",)
    np.testing.assert_array_equal(stress, stress_before)


def test_source_viscosity_and_axis_rate_derive_shear_stress_with_unit_conversion() -> None:
    outcome = analyze_rheology_group(
        (1.0, 10.0, 100.0),
        axis_kind="shear_rate",
        axis_unit="1/s",
        signals=(
            RheologySignalSeries.create(
                measurement_id="viscosity",
                signal_kind="viscosity",
                unit="cP",
                values=(1000.0, 500.0, 200.0),
            ),
        ),
    )

    stress = outcome.metrics["derived_shear_stress"]
    assert stress["status"] == "computed"
    assert stress["values"] == (1.0, 5.0, 20.0)
    assert stress["unit"] == "Pa"
    assert stress["parameters"]["viscosity_to_pa_s_factor"] == 0.001


def test_viscosity_unit_prefix_case_is_not_collapsed() -> None:
    millipascal = analyze_rheology_group(
        (1.0, 2.0),
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="milli",
                signal_kind="viscosity",
                unit="mPa*s",
                values=(1.0, 1.0),
            ),
        ),
    )
    megapascal = analyze_rheology_group(
        (1.0, 2.0),
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="mega",
                signal_kind="viscosity",
                unit="MPa*s",
                values=(1.0, 1.0),
            ),
        ),
    )

    assert millipascal.metrics["derived_shear_stress"]["values"] == (0.001, 0.002)
    assert megapascal.metrics["derived_shear_stress"]["values"] == (
        1_000_000.0,
        2_000_000.0,
    )


def test_oscillatory_moduli_derive_tan_delta_complex_modulus_and_viscosity() -> None:
    frequency = np.asarray((1.0, 10.0, 100.0))
    storage = np.asarray((1.0, 2.0, 3.0))
    loss = np.asarray((100.0, 500.0, 600.0))
    storage_before = storage.copy()
    loss_before = loss.copy()

    outcome = analyze_rheology_group(
        frequency,
        axis_kind="frequency",
        axis_unit="Hz",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="kPa",
                values=storage,
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=loss,
            ),
        ),
    )

    oscillatory = outcome.metrics["oscillatory"]
    assert oscillatory["tan_delta"]["values"] == (0.1, 0.25, 0.2)
    expected_modulus = tuple(
        math.hypot(e_storage * 1000.0, e_loss)
        for e_storage, e_loss in zip(storage, loss, strict=True)
    )
    np.testing.assert_allclose(
        oscillatory["complex_modulus_magnitude"]["values"], expected_modulus
    )
    np.testing.assert_allclose(
        oscillatory["complex_viscosity_magnitude"]["values"],
        tuple(
            modulus / (2.0 * math.pi * value)
            for modulus, value in zip(expected_modulus, frequency, strict=True)
        ),
    )
    assert oscillatory["complex_modulus_magnitude"]["unit"] == "Pa"
    assert oscillatory["complex_viscosity_magnitude"]["unit"] == "Pa*s"
    assert oscillatory["complex_viscosity_magnitude"]["parameters"][
        "frequency_to_angular_frequency"
    ] == "omega=2*pi*f"
    np.testing.assert_array_equal(storage, storage_before)
    np.testing.assert_array_equal(loss, loss_before)


def test_oscillatory_units_or_frequency_missing_are_locally_unavailable() -> None:
    incompatible = analyze_rheology_group(
        (1.0, 10.0, 100.0),
        axis_kind="frequency",
        axis_unit="Hz",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(10.0, 20.0, 30.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="N",
                values=(1.0, 2.0, 3.0),
            ),
        ),
    )
    assert incompatible.metrics["oscillatory"]["tan_delta"][
        "unavailable_reason"
    ] == "modulus_units_incompatible"

    temperature = analyze_rheology_group(
        (20.0, 40.0, 60.0),
        axis_kind="temperature",
        axis_unit="°C",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(10.0, 20.0, 30.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=(1.0, 2.0, 3.0),
            ),
        ),
    )
    assert temperature.metrics["oscillatory"]["tan_delta"]["status"] == "computed"
    assert temperature.metrics["oscillatory"]["complex_viscosity_magnitude"][
        "unavailable_reason"
    ] == "angular_frequency_required"


def test_zero_angular_frequency_is_a_local_complex_viscosity_mask() -> None:
    outcome = analyze_rheology_group(
        (0.0, 1.0, 10.0),
        axis_kind="angular_frequency",
        axis_unit="rad/s",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(10.0, 20.0, 30.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=(1.0, 2.0, 3.0),
            ),
        ),
    )

    complex_viscosity = outcome.metrics["oscillatory"][
        "complex_viscosity_magnitude"
    ]
    assert complex_viscosity["status"] == "computed_with_warning"
    assert complex_viscosity["values"][0] is None
    assert complex_viscosity["validity_mask"] == (False, True, True)
    assert complex_viscosity["warnings"] == (
        "angular_frequency_zero_at_some_points",
    )
