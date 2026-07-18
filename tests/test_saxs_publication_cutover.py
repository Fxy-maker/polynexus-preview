from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.saxs import SAXSEngine
from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.figures.contracts import (
    AxisDefinition,
    DataColumnDefinition,
    FigureDataSourceDefinition,
    FigureDefinition,
    FigureLayoutDefinition,
    PanelDefinition,
)


def _saxs_definition(*, figure_id: str = "saxs.cutover.main") -> FigureDefinition:
    return FigureDefinition(
        figure_id=figure_id,
        technique="saxs",
        scope="series",
        category="series_overview",
        title="SAXS cutover",
        layout=FigureLayoutDefinition(
            width_in=2.0,
            height_in=1.2,
            rows=1,
            columns=1,
            panels=(
                PanelDefinition(
                    panel_id="main",
                    row=0,
                    column=0,
                    x_axis=AxisDefinition("x", "q", "nm^-1"),
                    y_axis=AxisDefinition("y", "Intensity", "a.u."),
                ),
            ),
        ),
        data_sources=(
            FigureDataSourceDefinition(
                source_id="profile",
                columns=(
                    DataColumnDefinition("q", "nm^-1"),
                    DataColumnDefinition("intensity", "a.u."),
                ),
                values={
                    "q": (0.1, 0.2),
                    "intensity": (1.0, 0.5),
                },
            ),
        ),
        objects=(
            {
                "id": "profile-line",
                "type": "plot_series",
                "panel_id": "main",
                "data_ref": "profile",
                "x_column": "q",
                "y_column": "intensity",
                "chart_kind": "line",
                "style": {"color": "#0072B2", "line_width": 0.8},
            },
        ),
        recipe={
            "module": "tests.test_saxs_publication_cutover",
            "function": "_saxs_definition",
            "inputs": {},
            "parameters": {},
        },
        style_profile="sci_default",
    )


def _series_engine(mode: str) -> SAXSEngine:
    engine = SAXSEngine(SAXSConfig(experiment_type=mode))
    engine._condition_type = mode
    engine._analysis = SimpleNamespace()
    if mode == "temperature":
        engine._temperature_result = SimpleNamespace()
    else:
        engine._strain_result = SimpleNamespace()
    return engine


def test_temperature_plot_publishes_shared_manifest_and_result_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = _series_engine("temperature")
    definition = _saxs_definition()
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: (definition,))

    assets = engine.plot(str(tmp_path))

    manifest = Path(engine.result.metadata["figure_manifest"])
    assert manifest.is_file()
    assert assets == engine.result.figures
    assert assets[definition.figure_id].endswith(".svg")
    assert json.loads((tmp_path / "active_run.json").read_text("utf-8"))["run_id"]


def test_saxs_plot_uses_publication_profile_with_tiff_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = _series_engine("temperature")
    definition = _saxs_definition(figure_id="saxs.temperature.publication")
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: (definition,))

    engine.plot(str(tmp_path))

    manifest = json.loads(
        (tmp_path / "runs" / next((tmp_path / "runs").iterdir()).name / "figure_manifest.json")
        .read_text("utf-8")
    )
    assert manifest["output_profile"] == "saxs_publication"
    tiff = tmp_path / "runs" / next((tmp_path / "runs").iterdir()).name / manifest["figures"][0]["assets"]["tiff"]
    assert tiff.name == "figure.tiff"
    assert read_figure_asset_dimensions(tiff)[2] == 600


def test_strain_plot_publishes_shared_manifest_and_result_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    engine = _series_engine("strain")
    definition = _saxs_definition(figure_id="saxs.strain.evolution.1d")
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: (definition,))

    assets = engine.plot(str(tmp_path))

    assert assets == engine.result.figures
    assert Path(engine.result.metadata["figure_manifest"]).is_file()


def test_active_series_without_definitions_returns_no_assets(monkeypatch) -> None:
    for mode in ("temperature", "strain"):
        engine = _series_engine(mode)
        monkeypatch.setattr(engine, "build_figure_definitions", lambda: ())

        assert engine.plot() == {}


def test_unsupported_mixed_series_does_not_publish(monkeypatch) -> None:
    engine = SAXSEngine(SAXSConfig(experiment_type="temperature"))
    engine._condition_type = "strain"
    engine._analysis = SimpleNamespace()
    engine._temperature_result = SimpleNamespace()
    engine._strain_result = SimpleNamespace()
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: ())

    assert engine.plot() == {}


def test_static_without_definitions_returns_no_assets(monkeypatch) -> None:
    engine = SAXSEngine(SAXSConfig(experiment_type="static"))
    engine._condition_type = "static"
    engine._analysis = SimpleNamespace()
    monkeypatch.setattr(engine, "build_figure_definitions", lambda: ())

    assert engine.plot() == {}
