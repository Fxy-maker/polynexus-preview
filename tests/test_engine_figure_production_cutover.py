from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path

import pytest

from polynexus.core.figures.manifest import RunFigureManifestRepository


_ENGINE_CASES = (
    (
        "saxs",
        "SAXSEngine",
        ("generate_all_figures", "fig_temperature_overview", "fig_strain_overview"),
    ),
    (
        "waxs",
        "WAXSEngine",
        (
            "generate_all_figures",
            "generate_temperature_figures",
            "generate_strain_figures",
            "fig_waxs_temperature",
        ),
    ),
    ("dsc", "DSCEngine", ("generate_all_figures",)),
    (
        "ir",
        "IREngine",
        ("generate_all_figures", "generate_temperature_2d_figures"),
    ),
    ("nmr", "NMREngine", ("generate_all_figures",)),
)


def _mark_engine_as_analyzed(engine, technique):
    if technique == "saxs":
        engine._analysis = object()
    else:
        engine._results = [object()]


@pytest.mark.parametrize(
    ("technique", "engine_name", "legacy_writer_names"),
    _ENGINE_CASES,
)
def test_engine_plot_publishes_one_complete_manifest_without_legacy_writers(
    technique,
    engine_name,
    legacy_writer_names,
    ir_definition,
    monkeypatch,
    tmp_path,
):
    wrapper = importlib.import_module(f"polynexus.core.{technique}")
    engine_type = getattr(wrapper, engine_name)
    engine = engine_type(log_fn=lambda _message: None)
    _mark_engine_as_analyzed(engine, technique)

    definition = replace(
        ir_definition,
        figure_id=f"{technique}.frame.profile.001",
        technique=technique,
        title=f"{technique.upper()} Profile",
    )
    build_calls = 0

    def build_definitions():
        nonlocal build_calls
        build_calls += 1
        return (definition,)

    monkeypatch.setattr(engine, "build_figure_definitions", build_definitions)

    def reject_legacy_writer(*_args, **_kwargs):
        raise AssertionError(f"{technique} plot() called a legacy figure writer")

    for writer_name in legacy_writer_names:
        monkeypatch.setattr(
            wrapper,
            writer_name,
            reject_legacy_writer,
            raising=False,
        )

    output_root = tmp_path / technique
    figures = engine.plot(str(output_root))

    run_root, manifest = RunFigureManifestRepository(output_root).read_active_manifest()
    assert build_calls == 1
    assert manifest.technique == technique
    assert manifest.output_profile == "paper_complete"
    assert len(manifest.figures) == 1
    entry = manifest.figures[0]
    assert entry.figure_id == definition.figure_id
    assert entry.status == "ready"
    assert {"preview", "svg", "png", "pdf"} <= set(entry.assets)
    assert figures == {definition.figure_id: str((run_root / entry.assets["svg"]).resolve())}
    assert Path(figures[definition.figure_id]).name == "figure.svg"
