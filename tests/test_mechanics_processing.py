from __future__ import annotations

import numpy as np

from polynexus.core.mechanics_processing import (
    MechanicsSignalSeries,
    analyze_mechanics_group,
)


def test_mechanics_response_descriptors_are_traceable_and_source_preserving() -> None:
    response = np.asarray((0.0, 10.0, 7.0, 0.0))
    before = response.copy()

    outcome = analyze_mechanics_group(
        (0.0, 1.0, 2.0, 3.0),
        axis_kind="strain",
        axis_unit="%",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="stress",
                signal_kind="tensile_stress",
                test_mode="tensile",
                unit="MPa",
                values=response,
            ),
        ),
    )

    descriptor = outcome.metrics["response_descriptors"]["stress"]
    assert descriptor["peak_coordinate"]["value"] == 1.0
    assert descriptor["peak_coordinate"]["unit"] == "%"
    assert descriptor["peak_response"]["value"] == 10.0
    assert descriptor["peak_response"]["unit"] == "MPa"
    assert descriptor["raw_integral"]["value"] == 17.0
    assert descriptor["raw_integral"]["unit"] == "MPa*%"
    assert descriptor["raw_integral"]["status"] == "computed_with_warning"
    assert outcome.metrics["mechanics_property_summary"]["status"] == "unavailable"
    np.testing.assert_array_equal(response, before)


def test_mechanics_nonmonotonic_axis_only_blocks_integral() -> None:
    outcome = analyze_mechanics_group(
        (0.0, 2.0, 1.0),
        axis_kind="displacement",
        axis_unit="mm",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="force",
                signal_kind="force",
                test_mode="unspecified",
                unit="N",
                values=(1.0, 3.0, 2.0),
            ),
        ),
    )

    descriptor = outcome.metrics["response_descriptors"]["force"]
    assert descriptor["peak_coordinate"]["status"] == "computed"
    assert descriptor["raw_integral"]["unavailable_reason"] == (
        "coordinate_not_strictly_monotonic"
    )


def test_mechanics_vendor_modulus_is_preserved_but_not_reinterpreted() -> None:
    outcome = analyze_mechanics_group(
        (0.0, 1.0, 2.0),
        axis_kind="strain",
        axis_unit="%",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="modulus",
                signal_kind="vendor_modulus",
                test_mode="vendor_derived",
                unit="MPa",
                values=(1000.0, 900.0, 800.0),
            ),
        ),
    )

    source = outcome.metrics["source_signals"]["modulus"]
    assert source["values"] == (1000.0, 900.0, 800.0)
    assert outcome.metrics["response_descriptors"] == {}
    assert outcome.metrics["mechanics_property_summary"][
        "unavailable_reason"
    ] == "test_semantics_and_geometry_required"
