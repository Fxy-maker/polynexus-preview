from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.sec_processing import (
    SECCalibrationSpec,
    SECSignalSeries,
    analyze_sec_group,
)


def test_sec_response_descriptors_are_traceable_and_source_preserving() -> None:
    response = np.asarray((0.0, 2.0, 1.0, 0.0))
    before = response.copy()

    outcome = analyze_sec_group(
        (1.0, 2.0, 3.0, 4.0),
        axis_kind="elution_volume",
        axis_unit="mL",
        signals=(
            SECSignalSeries.create(
                measurement_id="ri",
                signal_kind="refractive_index_response",
                detector_kind="ri",
                unit="mV",
                values=response,
            ),
        ),
    )

    descriptor = outcome.metrics["response_descriptors"]["ri"]
    assert descriptor["peak_coordinate"]["value"] == 2.0
    assert descriptor["peak_coordinate"]["unit"] == "mL"
    assert descriptor["raw_integral"]["value"] == 3.0
    assert descriptor["raw_integral"]["unit"] == "mV*mL"
    assert descriptor["raw_integral"]["status"] == "computed_with_warning"
    assert descriptor["raw_integral"]["warnings"] == (
        "baseline_and_detector_response_not_corrected",
    )
    assert outcome.metrics["molecular_weight_summary"]["status"] == "unavailable"
    np.testing.assert_array_equal(response, before)


def test_sec_nonmonotonic_axis_only_blocks_integral() -> None:
    outcome = analyze_sec_group(
        (1.0, 3.0, 2.0),
        axis_kind="retention_time",
        axis_unit="min",
        signals=(
            SECSignalSeries.create(
                measurement_id="uv",
                signal_kind="uv_response",
                detector_kind="uv",
                unit="mAU",
                values=(1.0, 3.0, 2.0),
            ),
        ),
    )

    descriptor = outcome.metrics["response_descriptors"]["uv"]
    assert descriptor["peak_coordinate"]["status"] == "computed"
    assert descriptor["raw_integral"]["unavailable_reason"] == (
        "coordinate_not_strictly_monotonic"
    )


def test_sec_vendor_molar_mass_signal_is_preserved_but_not_reinterpreted() -> None:
    outcome = analyze_sec_group(
        (1.0, 2.0, 3.0),
        axis_kind="elution_volume",
        axis_unit="mL",
        signals=(
            SECSignalSeries.create(
                measurement_id="molar-mass",
                signal_kind="molar_mass",
                detector_kind="vendor_derived",
                unit="g/mol",
                values=(100000.0, 50000.0, 10000.0),
            ),
        ),
    )

    source = outcome.metrics["source_signals"]["molar-mass"]
    assert source["values"] == (100000.0, 50000.0, 10000.0)
    assert outcome.metrics["response_descriptors"] == {}
    assert outcome.metrics["molecular_weight_summary"][
        "unavailable_reason"
    ] == "calibration_and_distribution_semantics_required"


def test_sec_explicit_calibration_computes_mass_distribution_moments() -> None:
    spec = SECCalibrationSpec.create(
        response_measurement_id="ri",
        calibration_coordinates=(1.0, 2.0, 3.0),
        calibration_molar_masses=(1000.0, 100.0, 10.0),
        calibration_id="polystyrene-kit-v1",
        standard_source="lab-record://sec-standards/2026-09",
        standard_ids=("PS-1000", "PS-100", "PS-10"),
        distribution_mode="mass",
        coordinate_kind="elution_volume",
        calibration_unit="mL",
    )
    outcome = analyze_sec_group(
        (1.0, 2.0, 3.0),
        axis_kind="elution_volume",
        axis_unit="mL",
        signals=(
            SECSignalSeries.create(
                measurement_id="ri",
                signal_kind="refractive_index_response",
                detector_kind="ri",
                unit="mV",
                values=(1.0, 2.0, 1.0),
            ),
        ),
        analysis_spec=spec,
    )

    summary = outcome.metrics["molecular_weight_summary"]
    assert summary["status"] == "computed"
    assert summary["molar_mass_unit"] == "g/mol"
    assert summary["response_measurement_id"] == "ri"
    assert summary["calibration_polynomial_degree"] == 1
    assert summary["molar_mass_distribution"]["molar_mass"] == pytest.approx(
        (1000.0, 100.0, 10.0)
    )
    assert summary["Mn"] > 0.0
    assert summary["Mw"] >= summary["Mn"]
    assert summary["Mz"] >= summary["Mw"]
    assert summary["dispersity"] == summary["Mw"] / summary["Mn"]
    assert outcome.methods["molecular_weight_summary.Mn"] == (
        "calibrated_log_molar_mass_weighted_moment"
    )


def test_sec_calibration_is_local_when_curve_requires_extrapolation() -> None:
    outcome = analyze_sec_group(
        (0.0, 1.0, 2.0),
        axis_kind="retention_time",
        axis_unit="min",
        signals=(
            SECSignalSeries.create(
                measurement_id="ri",
                signal_kind="refractive_index_response",
                detector_kind="ri",
                unit="mV",
                values=(1.0, 2.0, 1.0),
            ),
        ),
        analysis_spec={
            "response_measurement_id": "ri",
            "calibration_coordinates": (1.0, 2.0, 3.0),
            "calibration_molar_masses": (1000.0, 100.0, 10.0),
            "calibration_id": "polystyrene-kit-v1",
            "standard_source": "lab-record://sec-standards/2026-09",
            "standard_ids": ("PS-1000", "PS-100", "PS-10"),
            "distribution_mode": "mass",
            "coordinate_kind": "retention_time",
            "calibration_unit": "min",
        },
    )

    summary = outcome.metrics["molecular_weight_summary"]
    assert summary["status"] == "unavailable"
    assert summary["unavailable_reason"] == "calibration_extrapolation_not_allowed"
    assert outcome.metrics["response_descriptors"]["ri"]["peak_coordinate"]["status"] == "computed"


def test_sec_invalid_distribution_semantics_remain_unavailable() -> None:
    outcome = analyze_sec_group(
        (1.0, 2.0, 3.0),
        axis_kind="elution_volume",
        axis_unit="mL",
        signals=(
            SECSignalSeries.create(
                measurement_id="ri",
                signal_kind="refractive_index_response",
                detector_kind="ri",
                unit="mV",
                values=(1.0, 2.0, 1.0),
            ),
        ),
        analysis_spec={
            "response_measurement_id": "ri",
            "calibration_coordinates": (1.0, 2.0, 3.0),
            "calibration_molar_masses": (1000.0, 100.0, 10.0),
            "calibration_id": "polystyrene-kit-v1",
            "standard_source": "lab-record://sec-standards/2026-09",
            "standard_ids": ("PS-1000", "PS-100", "PS-10"),
            "distribution_mode": "intensity",
        },
    )
    assert outcome.metrics["molecular_weight_summary"]["unavailable_reason"] == "calibration_spec_invalid"


def test_sec_calibration_rejects_duplicate_or_nonmonotonic_standard_semantics() -> None:
    with pytest.raises(ValueError, match="coordinates must be unique"):
        SECCalibrationSpec.create(
            response_measurement_id="ri",
            calibration_coordinates=(1.0, 1.0, 2.0),
            calibration_molar_masses=(1000.0, 100.0, 10.0),
            calibration_id="kit",
            standard_source="record",
            standard_ids=("a", "b", "c"),
            distribution_mode="mass",
        )
    with pytest.raises(ValueError, match="vary monotonically"):
        SECCalibrationSpec.create(
            response_measurement_id="ri",
            calibration_coordinates=(1.0, 2.0, 3.0),
            calibration_molar_masses=(1000.0, 10.0, 100.0),
            calibration_id="kit",
            standard_source="record",
            standard_ids=("a", "b", "c"),
            distribution_mode="mass",
        )
