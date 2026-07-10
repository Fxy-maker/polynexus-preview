import json
from dataclasses import replace
from pathlib import Path

import pytest

from polynexus.core.figures.data_writer import FigureDataSnapshotWriter
from polynexus.core.figures.validation import (
    FigureDefinitionValidationError,
    validate_figure_definition,
)


def test_validator_rejects_unknown_panel(ir_definition):
    broken = ir_definition.with_objects(
        (
            {
                **ir_definition.objects[0],
                "panel_id": "missing-panel",
            },
        )
    )

    with pytest.raises(FigureDefinitionValidationError, match="missing-panel"):
        validate_figure_definition(broken)


def test_data_writer_uses_run_relative_paths_and_schema(ir_definition, tmp_path):
    run_root = tmp_path / "runs" / "run-1"
    figure_dir = run_root / "figures" / ir_definition.figure_id
    writer = FigureDataSnapshotWriter(run_root)

    records = writer.write(ir_definition, figure_dir)

    assert records[0]["path_kind"] == "run_relative"
    assert records[0]["path"].startswith("figures/")
    assert not Path(records[0]["path"]).is_absolute()
    csv_path = run_root / records[0]["path"]
    assert csv_path.read_text(encoding="utf-8").splitlines()[0] == (
        "wavenumber_cm1,absorbance"
    )
    schema = json.loads((figure_dir / "data" / "data_schema.json").read_text("utf-8"))
    assert schema["sources"][0]["columns"][0]["unit"] == "cm^-1"
    assert len(records[0]["sha256"]) == 64


def test_data_writer_rejects_figure_directory_outside_run(ir_definition, tmp_path):
    writer = FigureDataSnapshotWriter(tmp_path / "runs" / "run-1")

    with pytest.raises(ValueError, match="escapes run root"):
        writer.write(ir_definition, tmp_path / "outside")


def test_data_writer_rejects_unsafe_source_id(ir_definition, tmp_path):
    unsafe_source = replace(ir_definition.data_sources[0], source_id="../escape")
    unsafe_definition = replace(ir_definition, data_sources=(unsafe_source,))
    writer = FigureDataSnapshotWriter(tmp_path / "runs" / "run-1")

    with pytest.raises(ValueError, match="unsafe data source id"):
        writer.write(
            unsafe_definition,
            tmp_path / "runs" / "run-1" / "figures" / ir_definition.figure_id,
        )
