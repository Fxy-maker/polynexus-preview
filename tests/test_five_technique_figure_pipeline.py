import json

import numpy as np

from polynexus.core.dsc_engine.core import DSCResult
from polynexus.core.dsc_engine.figure_provider import build_dsc_figure_definitions
from polynexus.core.figure_assets import read_figure_asset_dimensions
from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import build_ir_figure_definitions
from polynexus.core.nmr_engine.core import NMRResult
from polynexus.core.nmr_engine.figure_provider import build_nmr_figure_definitions
from polynexus.core.saxs_engine.figure_provider import (
    build_saxs_temperature_definitions,
)
from polynexus.core.saxs_engine.saxs_temperature import TempSeriesResult
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.figure_provider import build_waxs_figure_definitions


def test_five_techniques_publish_identical_paper_complete_roles(tmp_path):
    pipeline = FigurePipeline()
    for technique, definition in _representative_definitions().items():
        run_id = f"{technique}-uniform"
        manifest = pipeline.run(
            output_root=tmp_path,
            run_id=run_id,
            technique=technique,
            definitions=(definition,),
        )
        run_root = tmp_path / "runs" / run_id

        assert manifest.output_profile == "paper_complete"
        assert len(manifest.figures) == 1
        entry = manifest.figures[0]
        assert entry.status == "ready", entry.error
        assert set(entry.assets) == {"preview", "svg", "png", "pdf"}
        assert entry.capability_report["editing_mode"] == "object"
        assert read_figure_asset_dimensions(run_root / entry.assets["png"])[2] == 600
        document = json.loads((run_root / entry.document).read_text("utf-8"))
        assert document["export"]["assets"] == entry.assets


def _representative_definitions():
    ir = build_ir_figure_definitions(
        (
            IRResult(
                label="ir",
                wavenumber=np.array([1800.0, 1700.0, 1600.0]),
                absorbance=np.array([0.1, 0.4, 0.2]),
            ),
        )
    )[0]
    saxs = build_saxs_temperature_definitions(
        TempSeriesResult(
            temperatures=np.array([30.0]),
            L_array=np.array([12.0]),
            lc_array=np.array([4.0]),
            lc_effective_array=np.array([4.1]),
            Q_star_array=np.array([100.0]),
            Xc_array=np.array([1.0]),
        ),
        (np.array([0.1, 0.2, 0.3]),),
        (np.array([100.0, 70.0, 30.0]),),
    )[0]
    waxs = build_waxs_figure_definitions(
        (
            WAXSResult(
                label="waxs",
                two_theta=np.array([10.0, 15.0, 20.0]),
                I=np.array([8.0, 20.0, 9.0]),
            ),
        )
    )[0]
    dsc = build_dsc_figure_definitions(
        (
            DSCResult(
                label="dsc",
                T=np.array([20.0, 60.0, 100.0]),
                HF=np.array([0.1, 0.5, 0.2]),
            ),
        )
    )[0]
    nmr = build_nmr_figure_definitions(
        (
            NMRResult(
                label="nmr",
                ppm=np.array([180.0, 100.0, 20.0]),
                intensity=np.array([0.1, 0.5, 0.15]),
            ),
        )
    )[0]
    return {"ir": ir, "saxs": saxs, "waxs": waxs, "dsc": dsc, "nmr": nmr}
