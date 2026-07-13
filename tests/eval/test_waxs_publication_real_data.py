from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from polynexus.core.figures.production import FigureProductionPublisher
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.figure_provider import build_waxs_figure_definitions


def _result(label: str, offset: float = 0.0) -> WAXSResult:
    source = Path(__file__).parent / "synth_data" / "waxs_synth_pa6_alpha.xy"
    data = np.loadtxt(source)
    return WAXSResult(
        label=label,
        two_theta=data[:, 0],
        I=data[:, 1] + offset,
        peaks=[{"two_theta": 20.0 + offset, "fwhm_deg": 0.4, "area": 100.0}],
        Xc_pct=35.0 + offset,
        D_Scherrer_nm=12.0 + offset,
        r_squared=0.95,
        size_reliability_status="reliable",
    )


def _assert_ready_manifest(root: Path, run_id: str) -> None:
    run_root = root / "runs" / run_id
    payload = json.loads((run_root / "figure_manifest.json").read_text(encoding="utf-8"))
    assert payload["figures"]
    for entry in payload["figures"]:
        assert entry["status"] == "ready"
        assert entry["capability_report"]["object_editing"] is True
        assert {"preview", "png", "pdf", "svg", "tiff"}.issubset(entry["assets"])
        tiff = run_root / entry["assets"]["tiff"]
        with Image.open(tiff) as image:
            dpi = image.info.get("dpi", (0, 0))
            assert round(float(dpi[0])) == 600
            assert round(float(dpi[1])) == 600


def test_repository_waxs_static_case_publishes_ready_assets(tmp_path: Path) -> None:
    engine = SimpleNamespace(active_submodule="waxs.static", _results=[_result("static")])
    definitions = build_waxs_figure_definitions(engine)
    publication = FigureProductionPublisher().publish(output_root=tmp_path, technique="waxs", definitions=definitions, profile_id="waxs_publication")
    _assert_ready_manifest(tmp_path, publication.run_id)


def test_repository_waxs_temperature_case_publishes_ready_assets(tmp_path: Path) -> None:
    results = [_result(f"T={20 + index * 10} C", offset=index) for index in range(4)]
    temperature_result = SimpleNamespace(
        temperatures=[20.0, 30.0, 40.0, 50.0],
        results=results,
        Xc_vs_T=[result.Xc_pct for result in results],
        D_Scherrer_vs_T=[result.D_Scherrer_nm for result in results],
        parameters={"temperature_axis_ready": True},
        transitions=[],
    )
    engine = SimpleNamespace(active_submodule="waxs.temperature", _temperature_result=temperature_result, _results=results)
    definitions = build_waxs_figure_definitions(engine)
    publication = FigureProductionPublisher().publish(output_root=tmp_path, technique="waxs", definitions=definitions, profile_id="waxs_publication")
    _assert_ready_manifest(tmp_path, publication.run_id)


def test_repository_waxs_strain_case_publishes_ready_assets_with_1d_fallback(tmp_path: Path) -> None:
    points = []
    for index in range(4):
        result = _result(f"strain-{index}", offset=index)
        points.append(SimpleNamespace(
            strain_pct=index * 10.0,
            Xc_pct=result.Xc_pct,
            D_Scherrer_nm=result.D_Scherrer_nm,
            D_WH_nm=result.D_Scherrer_nm,
            epsilon_WH_pct=0.2 + index * 0.1,
            f_Herman_avg=np.nan,
            lattice_strain_per_peak={"200": 0.1 + index * 0.01},
            r_squared=result.r_squared,
            waxs_result=result,
        ))
    series = SimpleNamespace(point_results=points, strains=[0.0, 10.0, 20.0, 30.0], phase_boundaries={}, stress_induced_cryst=False, polymorph_transition=None)
    dataset = SimpleNamespace(scans=[SimpleNamespace(image=None) for _ in points])
    engine = SimpleNamespace(active_submodule="waxs.strain", _strain_result=series, _dataset=dataset)
    definitions = build_waxs_figure_definitions(engine)
    assert all(item["type"] != "image_grid" for definition in definitions for item in definition.objects)
    publication = FigureProductionPublisher().publish(output_root=tmp_path, technique="waxs", definitions=definitions, profile_id="waxs_publication")
    _assert_ready_manifest(tmp_path, publication.run_id)
