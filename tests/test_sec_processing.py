from __future__ import annotations

import numpy as np

from polynexus.core.sec_processing import SECSignalSeries, analyze_sec_group


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
