from __future__ import annotations

import numpy as np

from polynexus.core.dma_processing import (
    DMASignalSeries,
    analyze_dma_group,
)


def test_dma_ratio_keeps_partial_zero_denominator_as_a_local_mask() -> None:
    x = np.asarray((20.0, 40.0, 60.0, 80.0, 100.0))
    storage = np.asarray((1000.0, 800.0, 0.0, 500.0, 400.0))
    loss = np.asarray((100_000.0, 160_000.0, 300_000.0, 200_000.0, 200_000.0))
    storage_before = storage.copy()
    loss_before = loss.copy()

    outcome = analyze_dma_group(
        x,
        axis_kind="temperature",
        axis_unit="°C",
        signals=(
            DMASignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                modulus_basis="tensile",
                unit="MPa",
                values=storage,
            ),
            DMASignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                modulus_basis="tensile",
                unit="kPa",
                values=loss,
            ),
        ),
    )

    derived = outcome.metrics["derived_tan_delta"]["tensile"]
    assert derived["status"] == "computed_with_warning"
    assert derived["values"] == (0.1, 0.2, None, 0.4, 0.5)
    assert derived["validity_mask"] == (True, True, False, True, True)
    assert derived["warnings"] == ("storage_modulus_zero_at_some_points",)
    np.testing.assert_array_equal(storage, storage_before)
    np.testing.assert_array_equal(loss, loss_before)


def test_dma_incompatible_modulus_bases_and_units_are_locally_unavailable() -> None:
    x = (1.0, 10.0, 100.0, 1000.0)
    basis_mismatch = analyze_dma_group(
        x,
        axis_kind="frequency",
        axis_unit="Hz",
        signals=(
            DMASignalSeries.create(
                measurement_id="e-storage",
                signal_kind="storage_modulus",
                modulus_basis="tensile",
                unit="MPa",
                values=(10.0, 9.0, 8.0, 7.0),
            ),
            DMASignalSeries.create(
                measurement_id="g-loss",
                signal_kind="loss_modulus",
                modulus_basis="shear",
                unit="MPa",
                values=(1.0, 2.0, 3.0, 4.0),
            ),
        ),
    )
    assert basis_mismatch.metrics["derived_tan_delta"]["tensile"][
        "unavailable_reason"
    ] == "loss_modulus_missing_for_basis"
    assert basis_mismatch.metrics["derived_tan_delta"]["shear"][
        "unavailable_reason"
    ] == "storage_modulus_missing_for_basis"

    unit_mismatch = analyze_dma_group(
        x,
        axis_kind="frequency",
        axis_unit="Hz",
        signals=(
            DMASignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                modulus_basis="tensile",
                unit="MPa",
                values=(10.0, 9.0, 8.0, 7.0),
            ),
            DMASignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                modulus_basis="tensile",
                unit="N",
                values=(1.0, 2.0, 3.0, 4.0),
            ),
        ),
    )
    assert unit_mismatch.metrics["derived_tan_delta"]["tensile"][
        "unavailable_reason"
    ] == "modulus_units_incompatible"


def test_dma_tensile_and_shear_ratios_are_derived_independently() -> None:
    outcome = analyze_dma_group(
        (20.0, 40.0, 60.0),
        axis_kind="temperature",
        axis_unit="°C",
        signals=(
            DMASignalSeries.create(
                measurement_id="e-storage",
                signal_kind="storage_modulus",
                modulus_basis="tensile",
                unit="GPa",
                values=(1.0, 0.8, 0.6),
            ),
            DMASignalSeries.create(
                measurement_id="e-loss",
                signal_kind="loss_modulus",
                modulus_basis="tensile",
                unit="MPa",
                values=(100.0, 120.0, 90.0),
            ),
            DMASignalSeries.create(
                measurement_id="g-storage",
                signal_kind="storage_modulus",
                modulus_basis="shear",
                unit="MPa",
                values=(400.0, 300.0, 200.0),
            ),
            DMASignalSeries.create(
                measurement_id="g-loss",
                signal_kind="loss_modulus",
                modulus_basis="shear",
                unit="kPa",
                values=(40_000.0, 45_000.0, 30_000.0),
            ),
        ),
    )

    assert outcome.metrics["derived_tan_delta"]["tensile"]["values"] == (
        0.1,
        0.15,
        0.15,
    )
    assert outcome.metrics["derived_tan_delta"]["shear"]["values"] == (
        0.1,
        0.15,
        0.15,
    )


def test_dma_frequency_signal_does_not_create_a_thermal_transition_label() -> None:
    outcome = analyze_dma_group(
        (1.0, 10.0, 100.0, 1000.0, 10_000.0),
        axis_kind="frequency",
        axis_unit="Hz",
        signals=(
            DMASignalSeries.create(
                measurement_id="tan-delta",
                signal_kind="tan_delta",
                modulus_basis="unspecified",
                unit="1",
                values=(0.1, 0.2, 0.5, 0.2, 0.1),
            ),
        ),
    )

    candidates = outcome.metrics["transition_candidates"]["source_tan_delta"]
    assert candidates == {
        "status": "unavailable",
        "unavailable_reason": "temperature_axis_required",
    }
