from __future__ import annotations

import importlib
import json
from dataclasses import replace
from pathlib import Path

from polynexus.core.engine import BaseEngine


def test_production_publisher_creates_one_run_and_primary_asset_mapping(
    ir_definition,
    tmp_path,
):
    module = importlib.import_module("polynexus.core.figures.production")
    second = replace(
        ir_definition,
        figure_id="ir.frame.spectrum.002",
        title="IR Spectrum 2",
    )

    result = module.FigureProductionPublisher().publish(
        output_root=tmp_path,
        technique="ir",
        definitions=(ir_definition, second),
    )

    run_root = tmp_path / "runs" / result.run_id
    assert result.run_id.startswith("ir-")
    assert result.manifest.run_id == result.run_id
    assert result.manifest.output_profile == "paper_complete"
    assert set(result.primary_assets) == {
        "ir.frame.spectrum.001",
        "ir.frame.spectrum.002",
    }
    assert all(Path(path).is_absolute() for path in result.primary_assets.values())
    assert all(Path(path).name == "figure.svg" for path in result.primary_assets.values())
    assert all(Path(path).is_file() for path in result.primary_assets.values())
    assert json.loads((tmp_path / "active_run.json").read_text("utf-8")) == {
        "run_id": result.run_id
    }
    assert (run_root / "figure_manifest.json").is_file()


def test_base_engine_publishes_definitions_and_records_manifest_metadata(
    ir_definition,
    tmp_path,
):
    class _Engine(BaseEngine):
        name = "ir"

        def load(self, filepath):
            return True

        def preprocess(self):
            return True

        def analyze(self):
            return True

        def plot(self, output_dir=""):
            return self.publish_figure_definitions(output_dir)

        def get_parameters(self):
            return {}

        def build_figure_definitions(self):
            return (ir_definition,)

    engine = _Engine()

    figures = engine.publish_figure_definitions(tmp_path)

    assert figures == engine.result.figures
    assert set(figures) == {ir_definition.figure_id}
    assert engine.result.metadata["figure_run_id"].startswith("ir-")
    assert Path(engine.result.metadata["figure_manifest"]).is_file()


def test_base_engine_requires_explicit_figure_definition_contract(tmp_path):
    class _LegacyOnlyEngine(BaseEngine):
        name = "legacy"

        def load(self, filepath):
            return True

        def preprocess(self):
            return True

        def analyze(self):
            return True

        def plot(self, output_dir=""):
            return {}

        def get_parameters(self):
            return {}

    engine = _LegacyOnlyEngine()

    try:
        engine.publish_figure_definitions(tmp_path)
    except NotImplementedError as exc:
        assert "FigureDefinition" in str(exc)
    else:
        raise AssertionError("legacy-only engine unexpectedly published figures")
