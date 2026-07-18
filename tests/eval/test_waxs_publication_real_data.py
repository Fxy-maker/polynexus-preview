from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from polynexus.core.figures.production import FigureProductionPublisher
from polynexus.core.figures.reactive_project_service import ReactiveFigureProjectService
from polynexus.core.figure_object_store import FigureObjectStore
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries
from polynexus.plot_runtime.commands import EditWorksheetCells
from polynexus.plot_runtime.matplotlib_renderer import PublicationProfile
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
        assert entry["publication_role"] in {"main", "si", "diagnostic"}
        assert "display_order" in entry
        assert entry["capability_report"]["object_editing"] is True
        assert entry["capability_report"]["audit_passed"] is True
        assert entry["capability_report"]["v2_runtime"] == "ready"
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


def test_repository_waxs_strain_case_publishes_editable_2d_grid_and_roundtrips_document(tmp_path: Path) -> None:
    points = []
    for index in range(4):
        result = _result(f"strain-2d-{index}", offset=index)
        points.append(SimpleNamespace(
            strain_pct=index * 10.0,
            Xc_pct=result.Xc_pct,
            D_Scherrer_nm=result.D_Scherrer_nm,
            D_WH_nm=result.D_Scherrer_nm,
            epsilon_WH_pct=0.2 + index * 0.1,
            f_Herman_avg=0.3 + index * 0.01,
            lattice_strain_per_peak={"200": 0.1 + index * 0.01},
            r_squared=result.r_squared,
            waxs_result=result,
        ))
    series = SimpleNamespace(point_results=points, strains=[0.0, 10.0, 20.0, 30.0], phase_boundaries={})
    dataset = SimpleNamespace(scans=[SimpleNamespace(image=np.ones((2, 2)) * (index + 1)) for index in range(4)])
    engine = SimpleNamespace(active_submodule="waxs.strain", _strain_result=series, _dataset=dataset)
    definitions = build_waxs_figure_definitions(engine)
    main = next(item for item in definitions if item.figure_id == "waxs.strain.evolution")
    assert any(item["type"] == "image_grid" for item in main.objects)

    publication = FigureProductionPublisher().publish(output_root=tmp_path, technique="waxs", definitions=definitions, profile_id="waxs_publication")
    _assert_ready_manifest(tmp_path, publication.run_id)

    gallery_entries = build_active_manifest_gallery_entries(tmp_path)
    assert [entry.publication_role for entry in gallery_entries] == ["main", "main", "si"]

    run_root = tmp_path / "runs" / publication.run_id
    entry = next(item for item in publication.manifest.figures if item.figure_id == "waxs.strain.evolution")
    document = json.loads((run_root / entry.document).read_text(encoding="utf-8"))
    store = FigureObjectStore(document)
    assert store.get("pattern-grid")["type"] == "image_grid"
    assert store.rename("pattern-grid", "Selected strain patterns") is True
    assert store.get("pattern-grid")["name"] == "Selected strain patterns"

    project = ReactiveFigureProjectService(tmp_path)
    handle = project.load(run_id=publication.run_id, figure_id="waxs.strain.evolution")
    assert handle.session.execute(
        EditWorksheetCells({"waxs-strain-image-grid::intensity": {0: 99.0}})
    ).ok
    saved = project.save_working(handle)
    republished = project.publish(handle, profile=PublicationProfile(dpi=100))
    assert saved.working_revision == 1
    assert republished.published_revision == 1
    assert len(republished.assets) == 4
