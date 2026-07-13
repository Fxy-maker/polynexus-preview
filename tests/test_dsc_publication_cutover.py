from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from polynexus.core.dsc_engine.figure_provider import build_dsc_figure_definitions
from polynexus.core.dsc import DSCEngine
from polynexus.core.figures.profiles import get_figure_output_profile


def _engine(submodule: str) -> SimpleNamespace:
    return SimpleNamespace(active_submodule=submodule, _results=[], _kinetics_data={})


def test_dispatcher_uses_active_submodule_without_cross_mode_recipes() -> None:
    isothermal = build_dsc_figure_definitions(_engine("dsc.isothermal"))
    assert {item.figure_id for item in isothermal} == {"dsc.isothermal.fit.diagnostic"}
    nonisothermal = build_dsc_figure_definitions(_engine("dsc.nonisothermal"))
    assert {item.figure_id for item in nonisothermal} == {"dsc.nonisothermal.kinetics.diagnostic"}
    assert not any(item.figure_id.startswith("dsc.standard") for item in isothermal + nonisothermal)


def test_standard_dispatcher_projects_completed_result_data() -> None:
    result = SimpleNamespace(
        label="scan",
        T=np.arange(5.0),
        HF=np.arange(5.0),
        parameters={"Tm_peak_C": 2.0},
        quality_score=0.9,
        quality_flags=[],
    )
    definitions = build_dsc_figure_definitions(SimpleNamespace(active_submodule="dsc.standard", _results=[result]))
    assert any(item.figure_id == "dsc.standard.thermogram" for item in definitions)
    assert all(item.technique == "dsc" for item in definitions)


def test_dsc_engine_plot_passes_mode_definitions_to_shared_publisher(tmp_path) -> None:
    result = SimpleNamespace(
        label="scan",
        T=np.arange(5.0),
        HF=np.arange(5.0),
        parameters={"Tm_peak_C": 2.0},
        quality_score=0.9,
        quality_flags=[],
    )
    engine = DSCEngine()
    engine._results = [result]
    captured = {}

    def publish(output_dir, definitions=None, **_kwargs):
        captured["output_dir"] = output_dir
        captured["definitions"] = tuple(definitions or ())
        return {item.figure_id: str(tmp_path / f"{item.figure_id}.svg") for item in captured["definitions"]}

    engine.publish_figure_definitions = publish

    assets = engine.plot(str(tmp_path))

    assert captured["output_dir"] == str(tmp_path)
    assert any(item.figure_id == "dsc.standard.thermogram" for item in captured["definitions"])
    assert assets["dsc.standard.thermogram"].endswith(".svg")


def test_dsc_publication_profile_includes_600_dpi_tiff() -> None:
    profile = get_figure_output_profile("dsc_publication")

    assert profile.formal_assets["tiff"] == "figure.tiff"
    assert profile.publication_png_dpi == 600
