from pathlib import Path

import pytest

from polynexus.core.canonical_experiments.ir_temperature_series import (
    build_ir_temperature_series_template,
)
from polynexus.core.canonical_experiments import default_converter_registry


def _write_spectrum(path: Path, scale: float) -> None:
    path.write_text(
        "wavenumber,absorbance\n"
        f"1000,{scale}\n"
        f"1010,{scale + 0.1}\n"
        f"1020,{scale + 0.2}\n",
        encoding="utf-8",
    )


def test_ir_temperature_series_is_one_canonical_template_with_frame_axes(tmp_path: Path) -> None:
    first = tmp_path / "PA6-100C.csv"
    second = tmp_path / "PA6-120C.csv"
    _write_spectrum(first, 0.2)
    _write_spectrum(second, 0.4)

    outcome = build_ir_temperature_series_template(
        [first, second],
        source_artifact_id="artifact-series",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "ir.temperature_series.v1"
    assert len(outcome.template.measurements) == 2
    payload = outcome.template.to_dict()["payload"]
    assert payload["axis_names"] == ["frame", "wavenumber"]
    assert [frame["temperature_C"] for frame in payload["frames"]] == [100.0, 120.0]
    assert [frame["measurement_id"] for frame in payload["frames"]] == [
        measurement.measurement_id for measurement in outcome.template.measurements
    ]


def test_ir_temperature_series_rejects_ambiguous_frame_axis(tmp_path: Path) -> None:
    first = tmp_path / "sample-a.csv"
    second = tmp_path / "sample-b.csv"
    _write_spectrum(first, 0.2)
    _write_spectrum(second, 0.4)

    outcome = build_ir_temperature_series_template(
        [first, second],
        source_artifact_id="artifact-series",
    )

    assert outcome.status == "needs_input"
    assert "temperature_axis_unresolved" in outcome.reason_codes
    assert outcome.template is None


def test_ir_temperature_series_rejects_empty_or_single_frame(tmp_path: Path) -> None:
    only = tmp_path / "PA6-100C.csv"
    _write_spectrum(only, 0.2)

    with pytest.raises(ValueError, match="at least two"):
        build_ir_temperature_series_template([], source_artifact_id="artifact-series")
    with pytest.raises(ValueError, match="at least two"):
        build_ir_temperature_series_template([only], source_artifact_id="artifact-series")


def test_converter_registry_routes_ir_temperature_directory_as_one_template(tmp_path: Path) -> None:
    _write_spectrum(tmp_path / "PA6-100C.csv", 0.2)
    _write_spectrum(tmp_path / "PA6-120C.csv", 0.4)

    outcome = default_converter_registry().convert_path(
        tmp_path,
        technique="ir",
        source_artifact_id="artifact-directory",
    )

    assert outcome.status == "ready"
    assert outcome.template is not None
    assert outcome.template.template_id == "ir.temperature_series.v1"
