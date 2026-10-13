from __future__ import annotations

import numpy as np
import pytest

from polynexus.core.tga_validation import (
    TGAReplayCase,
    TGAUncertaintyReport,
    TGAValidationReport,
    default_tga_replay_cases,
    run_tga_replay_suite,
)


def test_replay_case_omitted_expectations_are_immutable_and_independent() -> None:
    first = TGAReplayCase(case_id="first", x_values=(20.0, 30.0), mass_values=(100.0, 99.0))
    second = TGAReplayCase(case_id="second", x_values=(20.0, 30.0), mass_values=(100.0, 99.0))
    assert dict(first.expected) == dict(second.expected) == {}
    assert first.expected is not second.expected
    with pytest.raises(TypeError):
        first.expected["residue"] = 99.0


def test_default_tga_replay_suite_covers_normal_and_anomalous_curves() -> None:
    cases = default_tga_replay_cases()
    assert {
        "single_step",
        "double_step",
        "noisy_curve",
        "too_few_points",
        "non_monotonic_axis",
        "nonpositive_initial_mass",
        "time_axis",
        "unknown_temperature_unit",
        "residue_target_out_of_range",
    } == {case.case_id for case in cases}

    report = run_tga_replay_suite(cases)

    assert isinstance(report, TGAValidationReport)
    assert report.status == "passed"
    assert report.validation_scope == "algorithm_boundary_only"
    assert report.independent_validation is False
    assert report.promotion_eligible is False
    assert all(item.status == "passed" for item in report.observations)
    by_id = {item.case_id: item for item in report.observations}
    assert by_id["non_monotonic_axis"].observed["dtg_status"] == "unavailable"
    assert by_id["nonpositive_initial_mass"].observed["normalization_status"] == "unavailable"
    assert by_id["residue_target_out_of_range"].observed["residue_target_status"] == "unavailable"


def test_tga_replay_is_deterministic_and_preserves_source_values() -> None:
    case = TGAReplayCase.create(
        case_id="small_curve",
        x_values=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0),
        mass_values=(100.0, 99.0, 97.0, 95.0, 94.0, 93.0),
        axis_kind="temperature",
        axis_unit="°C",
        signal_unit="%",
        expected={"dtg_status": "computed"},
    )

    report = run_tga_replay_suite((case,))
    observation = report.observations[0]
    assert observation.checks["source_arrays_preserved"] is True
    assert observation.checks["replay_deterministic"] is True
    assert observation.observed["input_hash"]
    assert observation.observed["first_output_hash"] == observation.observed["second_output_hash"]
    assert TGAValidationReport.from_dict(report.to_dict()).content_hash == report.content_hash


def test_tga_uncertainty_boundary_is_explicit_and_never_fabricates_error_bars() -> None:
    report = run_tga_replay_suite()
    uncertainty = report.uncertainty

    assert isinstance(uncertainty, TGAUncertaintyReport)
    assert uncertainty.status == "unavailable"
    assert "replicate_measurements_required" in uncertainty.reason_codes
    assert uncertainty.intervals == {}
    assert uncertainty.method_sensitivity_is_measurement_uncertainty is False
    assert report.to_dict()["uncertainty"]["intervals"] == {}

    evidence_ready = TGAUncertaintyReport.unavailable(
        replicate_measurements=3,
        instrument_error=True,
        calibration_error=True,
        standard_sample=True,
    )
    assert evidence_ready.status == "unavailable"
    assert evidence_ready.reason_codes == ("measurement_uncertainty_model_not_implemented",)
    assert evidence_ready.intervals == {}


def test_tga_replay_case_rejects_mismatched_arrays_and_round_trips() -> None:
    try:
        TGAReplayCase.create(
            case_id="bad",
            x_values=(0.0, 1.0),
            mass_values=(1.0,),
        )
    except ValueError as exc:
        assert "equal" in str(exc)
    else:
        raise AssertionError("mismatched replay arrays must be rejected")

    case = TGAReplayCase.create(
        case_id="roundtrip",
        x_values=np.arange(6, dtype=float),
        mass_values=np.linspace(100.0, 90.0, 6),
        expected={"dtg_status": "computed"},
    )
    restored = TGAReplayCase.from_dict(case.to_dict())
    assert restored == case
