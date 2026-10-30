from __future__ import annotations

from polynexus.core.mechanics_processing import MechanicsAnalysisSpec, MechanicsSignalSeries
from polynexus.core.mechanics_validation import (
    MechanicsReplayCase,
    run_mechanics_replay,
)


def _case(*, expected_modulus: float = 2.0e9) -> MechanicsReplayCase:
    return MechanicsReplayCase.create(
        case_id="analytical-tensile-001",
        axis_kind="strain",
        axis_unit="1",
        axis_values=(0.0, 0.001, 0.002, 0.003, 0.01),
        signals=(
            MechanicsSignalSeries.create(
                measurement_id="stress",
                signal_kind="tensile_stress",
                test_mode="tensile",
                unit="Pa",
                values=(0.0, 2.0e6, 4.0e6, 6.0e6, 5.0e6),
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
        expected_metrics={
            "tensile_modulus": expected_modulus,
            "yield_stress": 5.866666666666667e6,
            "toughness": 47500.0,
        },
        tolerances={
            "tensile_modulus": 1.0,
            "yield_stress": 1.0,
            "toughness": 1.0,
        },
        reference_kind="analytical_fixture",
    )


def test_mechanics_replay_round_trip_is_deterministic() -> None:
    case = _case()
    restored = MechanicsReplayCase.from_dict(case.to_dict())

    assert restored.replay_hash == case.replay_hash
    report = run_mechanics_replay(restored)
    assert report.status == "passed"
    assert report.replay_hash == case.replay_hash
    assert report.computed_metrics["tensile_modulus"] == 2.0e9
    assert report.mismatches == ()


def test_mechanics_replay_retains_expected_value_mismatch() -> None:
    report = run_mechanics_replay(_case(expected_modulus=2.1e9))

    assert report.status == "failed"
    assert report.reason_codes == ("replay_expected_value_mismatch",)
    mismatch = next(item for item in report.mismatches if item["metric"] == "tensile_modulus")
    assert mismatch["expected"] == 2.1e9
    assert mismatch["actual"] == 2.0e9
