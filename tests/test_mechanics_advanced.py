from __future__ import annotations

from polynexus.core.mechanics_processing import (
    MechanicsAdvancedSpec,
    MechanicsSignalSeries,
    analyze_mechanics_advanced,
    analyze_mechanics_cycles,
    analyze_mechanics_fatigue,
    integrate_fracture_energy,
    integrate_mechanics_creep,
)
from polynexus.core.compute.service import ComputeRunService


def test_mechanics_cycle_and_fatigue_candidates():
    cycles = analyze_mechanics_cycles((1, 1, 2, 2), (10, 8, 9, 7))
    assert cycles["peak_response"] == (10.0, 9.0)
    fatigue = analyze_mechanics_fatigue((1, 2, 3), (10, 9, 7))
    assert fatigue["status"] == "computed_with_warning"


def test_mechanics_creep_and_fracture_integrals():
    assert integrate_mechanics_creep((0, 1, 2), (0, 2, 2))["area"] == 3.0
    assert integrate_fracture_energy((0, 1, 2), (0, 2, 0))["energy"] == 2.0


def test_mechanics_advanced_spec_binds_cross_curve_models():
    spec = MechanicsAdvancedSpec.create(
        cycle_measurement_id="cycle",
        fatigue_measurement_id="fatigue",
        creep_measurement_id="creep",
        fracture_measurement_id="fracture",
    )
    signals = tuple(
        MechanicsSignalSeries.create(
            measurement_id=identifier,
            signal_kind="force",
            test_mode="unspecified",
            unit="N",
            values=(1.0, 2.0, 3.0),
            x_values=(0.0, 1.0, 2.0),
            x_unit="s",
        )
        for identifier in ("cycle", "fatigue", "creep", "fracture")
    )
    result = analyze_mechanics_advanced(signals, spec)
    assert result.metrics["cycles"]["status"] == "computed_with_warning"
    assert result.metrics["fatigue"]["status"] == "computed_with_warning"
    assert result.metrics["creep"]["area"] == 4.0
    assert result.metrics["fracture"]["energy"] == 4.0


def test_mechanics_advanced_compute_run_and_figure_share_one_projection(tmp_path):
    source = tmp_path / "fatigue.csv"
    source.write_text("Cycle,Force (N)\n1,10\n2,8\n3,7\n", encoding="utf-8")
    run = ComputeRunService().run_direct(
        technique="mechanics",
        path=source,
        output_dir=tmp_path / "figures",
        pipeline_options={
            "mechanics_advanced": {
                "cycle_measurement_id": "sheet-0-table-0",
                "fatigue_measurement_id": "sheet-0-table-0",
            }
        },
    )
    assert run.status == "completed"
    assert run.canonical_template.payload["mechanics_advanced"]["cycle_measurement_id"] == "sheet-0-table-0"
    assert run.result.metrics["mechanics_advanced"]["cycles"]["status"] == "computed_with_warning"
    manifest = {row["path"]: row for row in run.result.metric_manifest()}
    assert manifest["mechanics_advanced.cycles.peak_response"]["unit"] == "N"
    assert "mechanics.series.cycle-envelope.001" in run.result.figures
