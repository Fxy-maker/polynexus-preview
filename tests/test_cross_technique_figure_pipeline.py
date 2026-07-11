import json

import numpy as np

from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import build_ir_figure_definitions
from polynexus.core.ir_engine.io import IRSpectrum
from polynexus.core.saxs_engine.figure_provider import (
    build_saxs_temperature_definitions,
)
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult


def test_ir_and_saxs_runs_publish_uniform_paper_complete_projects(tmp_path):
    pipeline = FigurePipeline()
    ir_manifest = pipeline.run(
        output_root=tmp_path,
        run_id="ir-uniform",
        technique="ir",
        definitions=_ir_definitions(),
    )
    saxs_manifest = pipeline.run(
        output_root=tmp_path,
        run_id="saxs-uniform",
        technique="saxs",
        definitions=_saxs_definitions(),
    )

    for manifest in (ir_manifest, saxs_manifest):
        run_root = tmp_path / "runs" / manifest.run_id
        assert manifest.figures
        for entry in manifest.figures:
            _assert_paper_complete(run_root, entry)

    saxs_run_root = tmp_path / "runs" / saxs_manifest.run_id
    assert any(entry.category == "per_frame" for entry in saxs_manifest.figures)
    assert all(
        entry.capability_report["editing_mode"] == "object"
        for entry in saxs_manifest.figures
    )
    documents = {
        entry.figure_id: json.loads(
            (saxs_run_root / entry.document).read_text("utf-8")
        )
        for entry in saxs_manifest.figures
    }
    assert len(documents["saxs.series.temperature.parameters"]["layout"]["panels"]) == 4
    assert documents["saxs.series.temperature.heatmap"]["objects"][0]["type"] == (
        "heatmap"
    )


def _assert_paper_complete(run_root, entry):
    assert entry.status == "ready", entry.error
    assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
    assert entry.document.endswith("figure.pnfig.json")
    assert all((run_root / path).is_file() for path in entry.assets.values())
    assert read_figure_asset_dimensions(run_root / entry.assets["png"])[2] == 600
    document = json.loads((run_root / entry.document).read_text("utf-8"))
    assert document["export"]["profile"] == "paper_complete"
    assert document["export"]["published_revision"] == entry.published_revision
    assert document["export"]["assets"] == entry.assets


def _ir_definitions():
    result = IRResult(
        label="uniform-ir",
        wavenumber=np.array([1800.0, 1700.0, 1600.0]),
        absorbance=np.array([0.1, 0.4, 0.2]),
        absorbance_fit=np.array([0.11, 0.38, 0.21]),
        simulated_spectrum=IRSpectrum(
            label="computed",
            wavenumber=np.array([1810.0, 1705.0, 1595.0]),
            absorbance=np.array([0.08, 0.34, 0.18]),
            source="computation",
        ),
        Xc_pct=37.0,
    )
    return build_ir_figure_definitions((result,))


def _saxs_definitions():
    result = TempSeriesResult(
        temperatures=np.array([30.0, 80.0]),
        L_array=np.array([12.0, 11.2]),
        lc_array=np.array([4.0, 3.4]),
        lc_effective_array=np.array([4.1, 3.6]),
        Q_star_array=np.array([100.0, 82.0]),
        Xc_array=np.array([1.0, 0.82]),
    )
    return build_saxs_temperature_definitions(
        result,
        (
            np.array([0.1, 0.2, 0.3, 0.4]),
            np.array([0.12, 0.22, 0.32, 0.42, 0.52]),
        ),
        (
            np.array([100.0, 80.0, 45.0, 20.0]),
            np.array([90.0, 70.0, 38.0, 18.0, 9.0]),
        ),
    )
