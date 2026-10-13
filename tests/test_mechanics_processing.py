from __future__ import annotations

import numpy as np

from polynexus.core.mechanics_processing import (
    MechanicsAnalysisSpec,
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


def test_mechanics_advanced_models_require_explicit_semantics() -> None:
    outcome = analyze_mechanics_group(
        (0.0, 0.001, 0.002),
        axis_kind="strain",
        axis_unit="1",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="stress",
                signal_kind="tensile_stress",
                test_mode="tensile",
                unit="MPa",
                values=(0.0, 2.0, 4.0),
            ),
        ),
    )

    summary = outcome.metrics["mechanics_property_summary"]
    assert summary["status"] == "unavailable"
    assert summary["tensile_modulus"]["status"] == "unavailable"
    assert summary["tensile_modulus"]["unavailable_reason"] == (
        "analysis_spec_required"
    )
    assert summary["yield_stress"]["status"] == "unavailable"
    assert summary["toughness"]["status"] == "unavailable"


def test_mechanics_explicit_stress_strain_models_are_traceable() -> None:
    stress = np.asarray((0.0, 2.0e6, 4.0e6, 6.0e6, 5.0e6))
    before = stress.copy()
    outcome = analyze_mechanics_group(
        (0.0, 0.001, 0.002, 0.003, 0.01),
        axis_kind="strain",
        axis_unit="1",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="stress",
                signal_kind="tensile_stress",
                test_mode="tensile",
                unit="Pa",
                values=stress,
            ),
        ),
        analysis_spec=MechanicsAnalysisSpec.create(
            test_mode="tensile",
            stress_measurement_id="stress",
            geometry={"gauge_length_mm": 10.0},
            stress_unit="Pa",
            strain_unit="1",
            modulus_window=(0.0, 0.002),
            yield_offset=0.001,
            toughness_endpoint="last_valid",
        ),
    )

    summary = outcome.metrics["mechanics_property_summary"]
    modulus = summary["tensile_modulus"]
    assert modulus["status"] == "computed"
    assert modulus["value"] == 2.0e9
    assert modulus["unit"] == "Pa"
    assert modulus["source_measurements"] == ["stress"]
    assert summary["yield_stress"]["status"] == "computed"
    assert summary["yield_stress"]["unit"] == "Pa"
    assert summary["yield_strain"]["unit"] == "1"
    assert summary["toughness"]["status"] == "computed"
    assert summary["toughness"]["unit"] == "Pa"
    assert outcome.methods["mechanics_property_summary.tensile_modulus.value"] == (
        "linear_least_squares_stress_strain"
    )
    assert outcome.parameters["mechanics_property_summary.tensile_modulus.value"][
        "modulus_window"
    ] == [0.0, 0.002]
    np.testing.assert_array_equal(stress, before)


def test_mechanics_yield_and_toughness_are_locally_unavailable() -> None:
    outcome = analyze_mechanics_group(
        (0.0, 0.001, 0.002),
        axis_kind="strain",
        axis_unit="1",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="stress",
                signal_kind="tensile_stress",
                test_mode="tensile",
                unit="MPa",
                values=(0.0, 2.0, 4.0),
            ),
        ),
        analysis_spec=MechanicsAnalysisSpec.create(
            test_mode="tensile",
            stress_measurement_id="stress",
            geometry={"gauge_length_mm": 10.0},
            stress_unit="MPa",
            strain_unit="1",
            modulus_window=(0.0, 0.001),
            yield_offset=0.002,
            toughness_endpoint="last_valid",
        ),
    )

    summary = outcome.metrics["mechanics_property_summary"]
    assert summary["tensile_modulus"]["status"] == "computed"
    assert summary["yield_stress"]["status"] == "unavailable"
    assert summary["yield_stress"]["unavailable_reason"] == (
        "offset_line_no_crossing"
    )
    assert summary["toughness"]["status"] == "computed"


def test_mechanics_explicit_measurement_uncertainty_is_diagnostic() -> None:
    outcome = analyze_mechanics_group(
        (0.0, 0.001, 0.002, 0.003, 0.01),
        axis_kind="strain",
        axis_unit="1",
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="stress",
                signal_kind="tensile_stress",
                test_mode="tensile",
                unit="MPa",
                values=(0.0, 2.0, 4.0, 6.0, 5.0),
            ),
        ),
        analysis_spec=MechanicsAnalysisSpec.create(
            test_mode="tensile",
            stress_measurement_id="stress",
            geometry={"gauge_length_mm": 10.0},
            stress_unit="MPa",
            strain_unit="1",
            modulus_window=(0.0, 0.002),
            yield_offset=0.001,
            toughness_endpoint="last_valid",
            stress_std=0.1,
            strain_std=0.00001,
        ),
    )

    uncertainty = outcome.uncertainty
    modulus_path = "mechanics_property_summary.tensile_modulus.value"
    assert uncertainty[modulus_path]["status"] == "computed"
    assert uncertainty[modulus_path]["kind"] == "standard_deviation"
    assert uncertainty[modulus_path]["unit"] == "Pa"
    assert uncertainty[modulus_path]["parameters"]["uncertainty_status"] == (
        "diagnostic"
    )
    assert uncertainty["mechanics_property_summary.yield_stress.value"]["value"] > 0.0
    assert uncertainty["mechanics_property_summary.toughness.value"]["value"] > 0.0
