from __future__ import annotations

import math

import numpy as np

from polynexus.core.rheology_processing import (
    RheologyAnalysisSpec,
    RheologyLVESpec,
    RheologySignalSeries,
    RheologyYieldStressSpec,
    analyze_rheology_group,
)


def test_rheology_analysis_specs_round_trip_and_validate_explicit_semantics() -> None:
    spec = RheologyAnalysisSpec.create(
        yield_stress=RheologyYieldStressSpec.create(
            model="Bingham",
            stress_measurement_id="stress",
            rate_window=(1.0, 100.0),
            min_points=3,
        ),
        lve=RheologyLVESpec.create(
            storage_measurement_id="storage",
            loss_measurement_id="loss",
            plateau_relative_tolerance=0.1,
            plateau_reference_points=3,
            min_plateau_points=3,
        ),
    )

    assert RheologyAnalysisSpec.from_mapping(spec.to_dict()).to_dict() == spec.to_dict()
    assert spec.yield_stress is not None
    assert spec.yield_stress.model == "bingham"


def test_yield_stress_fit_supports_bingham_and_herschel_bulkley() -> None:
    rate = (1.0, 2.0, 4.0, 8.0, 16.0)
    bingham = analyze_rheology_group(
        rate,
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="stress",
                signal_kind="shear_stress",
                unit="Pa",
                values=tuple(5.0 + 2.0 * value for value in rate),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            yield_stress=RheologyYieldStressSpec.create(
                model="bingham",
                stress_measurement_id="stress",
            )
        ),
    )

    bingham_fit = bingham.metrics["yield_stress_fit"]
    assert bingham_fit["status"] == "computed"
    assert abs(bingham_fit["yield_stress"]["value"] - 5.0) < 1e-12
    assert abs(bingham_fit["consistency_index"]["value"] - 2.0) < 1e-12
    assert bingham_fit["flow_index"]["unavailable_reason"] == "not_defined_for_bingham"
    assert bingham_fit["fit_quality"]["r_squared"] == 1.0

    exponent = 0.8
    herschel_bulkley = analyze_rheology_group(
        rate,
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="stress",
                signal_kind="shear_stress",
                unit="Pa",
                values=tuple(3.0 + 1.5 * value**exponent for value in rate),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            yield_stress=RheologyYieldStressSpec.create(
                model="herschel_bulkley",
                stress_measurement_id="stress",
            )
        ),
    )

    fit = herschel_bulkley.metrics["yield_stress_fit"]
    assert fit["status"] == "computed"
    assert fit["model"] == "herschel_bulkley"
    assert abs(fit["yield_stress"]["value"] - 3.0) < 1e-6
    assert abs(fit["consistency_index"]["value"] - 1.5) < 1e-6
    assert abs(fit["flow_index"]["value"] - exponent) < 1e-6


def test_lve_plateau_and_gel_point_are_explicit_diagnostic_candidates() -> None:
    outcome = analyze_rheology_group(
        (0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
        axis_kind="strain",
        axis_unit="%",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(100.0, 101.0, 98.0, 80.0, 50.0, 20.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=(10.0, 20.0, 50.0, 100.0, 200.0, 500.0),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            lve=RheologyLVESpec.create(
                storage_measurement_id="storage",
                loss_measurement_id="loss",
                plateau_relative_tolerance=0.05,
                plateau_reference_points=3,
                min_plateau_points=3,
            )
        ),
    )

    lve = outcome.metrics["lve_analysis"]
    assert lve["status"] == "computed"
    assert lve["lve_limit"]["value"] == 0.005
    assert lve["lve_limit"]["unit"] == "1"
    assert lve["plateau_storage_modulus"]["value"] == 100.0
    assert lve["gel_point"]["status"] == "computed"
    assert 0.005 < lve["gel_point"]["value"] < 0.01
    assert lve["gel_point_candidates"]["count"] == 1


def test_lve_percentage_window_is_normalized_and_multiple_crossovers_are_warned() -> None:
    outcome = analyze_rheology_group(
        (0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0),
        axis_kind="strain",
        axis_unit="%",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(100.0, 101.0, 99.0, 100.0, 80.0, 90.0, 100.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=(10.0, 20.0, 30.0, 120.0, 70.0, 110.0, 50.0),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            lve=RheologyLVESpec.create(
                storage_measurement_id="storage",
                loss_measurement_id="loss",
                strain_window=(0.1, 5.0),
                plateau_relative_tolerance=0.05,
                plateau_reference_points=3,
                min_plateau_points=3,
                strain_unit="%",
            )
        ),
    )

    lve = outcome.metrics["lve_analysis"]
    assert lve["status"] == "computed_with_warning"
    assert lve["parameters"]["strain_to_dimensionless_factor"] == 0.01
    assert lve["parameters"]["strain_window"] == [0.1, 5.0]
    assert lve["gel_point_candidates"]["count"] == 3
    assert lve["gel_point"]["status"] == "computed_with_warning"
    assert "multiple_modulus_crossovers_observed" in lve["gel_point"]["warnings"]


def test_lve_exact_crossover_run_is_one_candidate() -> None:
    outcome = analyze_rheology_group(
        (0.1, 1.0, 10.0, 100.0),
        axis_kind="strain",
        axis_unit="1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(10.0, 10.0, 5.0, 2.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=(10.0, 10.0, 6.0, 1.0),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            lve=RheologyLVESpec.create(
                storage_measurement_id="storage",
                loss_measurement_id="loss",
                plateau_reference_points=2,
                min_plateau_points=2,
            )
        ),
    )

    candidates = outcome.metrics["lve_analysis"]["gel_point_candidates"]
    assert candidates["count"] == 2
    assert candidates["candidates"][0]["strain"] == 0.1


def test_lve_explicit_units_can_complete_unknown_canonical_units() -> None:
    outcome = analyze_rheology_group(
        (1.0, 2.0, 3.0),
        axis_kind="strain",
        axis_unit="unknown",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="unknown",
                values=(100.0, 100.0, 80.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="unknown",
                values=(10.0, 20.0, 100.0),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            lve=RheologyLVESpec.create(
                storage_measurement_id="storage",
                loss_measurement_id="loss",
                strain_unit="%",
                storage_unit="kPa",
                loss_unit="kPa",
                plateau_reference_points=2,
                min_plateau_points=2,
            )
        ),
    )

    lve = outcome.metrics["lve_analysis"]
    assert lve["status"] in {"computed", "computed_with_warning"}
    assert lve["parameters"]["storage_source_unit"] == "kPa"
    assert lve["parameters"]["loss_source_unit"] == "kPa"


def test_lve_crossover_remains_available_when_plateau_is_not_computable() -> None:
    outcome = analyze_rheology_group(
        (0.1, 1.0, 10.0, 100.0),
        axis_kind="strain",
        axis_unit="1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="storage",
                signal_kind="storage_modulus",
                unit="Pa",
                values=(0.0, 0.0, 1.0, 3.0),
            ),
            RheologySignalSeries.create(
                measurement_id="loss",
                signal_kind="loss_modulus",
                unit="Pa",
                values=(0.0, 0.0, 2.0, 1.0),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            lve=RheologyLVESpec.create(
                storage_measurement_id="storage",
                loss_measurement_id="loss",
                plateau_reference_points=3,
                min_plateau_points=3,
            )
        ),
    )

    lve = outcome.metrics["lve_analysis"]
    assert lve["status"] == "computed_with_warning"
    assert lve["plateau_storage_modulus"]["status"] == "unavailable"
    assert lve["plateau_storage_modulus"]["unavailable_reason"] == (
        "storage_modulus_plateau_nonpositive"
    )
    assert lve["gel_point"]["status"] == "computed_with_warning"


def test_advanced_rheology_metrics_are_locally_unavailable_when_semantics_fail() -> None:
    outcome = analyze_rheology_group(
        (1.0, 2.0),
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="stress",
                signal_kind="shear_stress",
                unit="Pa",
                values=(1.0, 2.0),
            ),
        ),
        analysis_spec=RheologyAnalysisSpec.create(
            yield_stress=RheologyYieldStressSpec.create(
                model="bingham",
                stress_measurement_id="missing",
            )
        ),
    )

    assert outcome.metrics["yield_stress_fit"]["status"] == "unavailable"
    assert outcome.metrics["yield_stress_fit"]["unavailable_reason"] == (
        "stress_measurement_not_found"
    )
    assert outcome.metrics["lve_analysis"]["unavailable_reason"] == "not_requested"


def test_invalid_lve_spec_does_not_block_a_valid_yield_fit() -> None:
    outcome = analyze_rheology_group(
        (1.0, 2.0, 4.0, 8.0),
        axis_kind="shear_rate",
        axis_unit="s^-1",
        signals=(
            RheologySignalSeries.create(
                measurement_id="stress",
                signal_kind="shear_stress",
                unit="Pa",
                values=(7.0, 9.0, 13.0, 21.0),
            ),
        ),
        analysis_spec={
            "yield_stress": {
                "model": "bingham",
                "stress_measurement_id": "stress",
            },
            "lve": {
                "storage_measurement_id": "",
                "loss_measurement_id": "loss",
            },
        },
    )

    assert outcome.metrics["yield_stress_fit"]["status"] == "computed"
    assert outcome.metrics["lve_analysis"]["status"] == "unavailable"
    assert outcome.metrics["lve_analysis"]["unavailable_reason"] == (
        "lve_analysis_spec_invalid"
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
