from __future__ import annotations

from pathlib import Path

from polynexus.core.canonical_experiments import convert_one_dimensional_table, default_converter_registry
from polynexus.core.compute import ComputeRunService
from polynexus.core.engine import get_engine
from polynexus.cli.parser import parse_args


def _write_table(path: Path, *, x_header: str, y_header: str) -> Path:
    path.write_text(
        f"{x_header},{y_header}\n25,10.0\n100,9.2\n200,8.1\n400,4.0\n",
        encoding="utf-8",
    )
    return path


def test_tga_conversion_is_sample_neutral_and_preserves_thermal_semantics(tmp_path: Path) -> None:
    source = _write_table(tmp_path / "sample-a.csv", x_header="Temperature (°C)", y_header="Mass (%)")
    outcome = convert_one_dimensional_table(source, technique="tga", source_artifact_id="artifact-a")

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "thermal_curve_1d.v1"
    assert outcome.template.payload["measurement_family"] == "thermal_1d"
    measurement = outcome.template.measurements[0]
    assert measurement.family == "thermal_1d"
    assert measurement.mapping is not None
    assert measurement.mapping.x_kind == "temperature"
    assert measurement.units == {"x": "°C", "intensity": "%"}


def test_tga_time_mass_table_and_unknown_units_remain_calculable(tmp_path: Path) -> None:
    source = _write_table(tmp_path / "different-material.tsv", x_header="Elapsed time", y_header="Sample mass")
    source.write_text(source.read_text(encoding="utf-8").replace(",", "\t"), encoding="utf-8")
    outcome = default_converter_registry().convert_path(source, technique="tga", source_artifact_id="artifact-b")

    assert outcome.status == "ready"
    measurement = outcome.template.measurements[0]
    assert measurement.mapping is not None
    assert measurement.mapping.x_kind == "time"
    assert measurement.units == {"x": "unknown", "intensity": "unknown"}
    assert set(measurement.warnings) == {"coordinate_unit_unknown", "intensity_unit_unknown"}


def test_tga_engine_and_compute_run_are_shared_entry_points(tmp_path: Path) -> None:
    source = _write_table(tmp_path / "sample-b.csv", x_header="Temperature C", y_header="Weight %")
    engine = get_engine("tga")
    assert engine is not None
    run = ComputeRunService(lambda *args, **kwargs: engine).run_direct(
        technique="tga", path=source, output_dir="", engine=engine
    )
    assert run.status == "completed"
    assert run.canonical_template is not None
    assert run.canonical_template.template_id == "thermal_curve_1d.v1"
    assert run.result is not None
    assert run.result.metrics["point_count"] == 4
    assert run.result.warnings == ()
    assert any(item.capability_id == "curve.summary.v1" and item.status == "completed" for item in run.capability_items)


def test_tga_is_available_in_single_cli_batch_and_tuning_parsers() -> None:
    assert parse_args(["tga", "curve.csv"]).cmd == "tga"
    assert parse_args(["batch", "data", "--technique", "tga"]).technique == "tga"
