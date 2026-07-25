from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.figures.production import FigureProductionPublisher
from polynexus.core.figures.project_service import FigureProjectService
from polynexus.core.figures.reactive_project_service import ReactiveFigureProjectService
from polynexus.core.figure_object_store import FigureObjectStore
from polynexus.core.waxs_engine.core import WAXSResult
from polynexus.core.waxs_engine.figure_provider import build_waxs_figure_definitions
from polynexus.gui.export_context_service import (
    copy_export_bundle_sections,
    create_export_bundle_dirs,
    write_export_manifest,
)
from polynexus.gui.main_window import MainWindow
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries
from polynexus.plot_runtime.commands import EditWorksheetCells
from polynexus.plot_runtime.matplotlib_renderer import PublicationProfile


@pytest.fixture(autouse=True)
def _cleanup_qt_widgets():
    yield
    app = QApplication.instance()
    if app is None:
        return
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _result(label: str, offset: float = 0.0) -> WAXSResult:
    source = Path(__file__).parent / "eval" / "synth_data" / "waxs_synth_pa6_alpha.xy"
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


def _engine_for(mode: str):
    if mode == "waxs.static":
        return SimpleNamespace(active_submodule=mode, _results=[_result("static")])
    if mode == "waxs.temperature":
        results = [_result(f"T={20 + index * 10} C", offset=index) for index in range(4)]
        temperature_result = SimpleNamespace(
            temperatures=[20.0, 30.0, 40.0, 50.0],
            results=results,
            Xc_vs_T=[result.Xc_pct for result in results],
            D_Scherrer_vs_T=[result.D_Scherrer_nm for result in results],
            parameters={"temperature_axis_ready": True},
            transitions=[],
        )
        return SimpleNamespace(
            active_submodule=mode,
            _temperature_result=temperature_result,
            _results=results,
        )

    points = []
    for index in range(4):
        result = _result(f"strain-{index}", offset=index)
        points.append(
            SimpleNamespace(
                strain_pct=index * 10.0,
                Xc_pct=result.Xc_pct,
                D_Scherrer_nm=result.D_Scherrer_nm,
                D_WH_nm=result.D_Scherrer_nm,
                epsilon_WH_pct=0.2 + index * 0.1,
                f_Herman_avg=0.3 + index * 0.01,
                lattice_strain_per_peak={"200": 0.1 + index * 0.01},
                r_squared=result.r_squared,
                waxs_result=result,
            )
        )
    series = SimpleNamespace(point_results=points, strains=[0.0, 10.0, 20.0, 30.0], phase_boundaries={})
    dataset = SimpleNamespace(
        scans=[SimpleNamespace(image=np.ones((2, 2)) * (index + 1)) for index in range(4)]
    )
    return SimpleNamespace(active_submodule=mode, _strain_result=series, _dataset=dataset)


@pytest.mark.parametrize("mode", ("waxs.static", "waxs.temperature", "waxs.strain"))
def test_waxs_modes_complete_manifest_editor_export_history_lifecycle(tmp_path: Path, mode: str):
    source = Path(__file__).parent / "eval" / "synth_data" / "waxs_synth_pa6_alpha.xy"
    output_root = tmp_path / "output"
    engine = _engine_for(mode)
    definitions = build_waxs_figure_definitions(engine)
    publication = FigureProductionPublisher().publish(
        output_root=output_root,
        technique="waxs",
        definitions=definitions,
        profile_id="waxs_publication",
    )

    entries = build_active_manifest_gallery_entries(output_root)
    assert entries
    assert {entry.figure_id for entry in entries} == {
        item.figure_id for item in publication.manifest.figures
    }
    assert all(entry.run_id == publication.run_id for entry in entries)
    assert all(entry.publication_role in {"main", "si", "diagnostic"} for entry in entries)
    selected = next(entry for entry in entries if entry.publication_role == "main")

    if mode == "waxs.strain":
        document = json.loads(Path(selected.document_path).read_text(encoding="utf-8"))
        assert FigureObjectStore(document).get("pattern-grid")["type"] == "image_grid"
        service = ReactiveFigureProjectService(output_root)
        handle = service.load(run_id=publication.run_id, figure_id=selected.figure_id)
        assert handle.session.execute(
            EditWorksheetCells({"waxs-strain-image-grid::intensity": {0: 99.0}})
        ).ok
        saved = service.save_working(handle)
        published = service.publish(handle, profile=PublicationProfile(dpi=100))
        assert saved.working_revision == 1
        assert published.published_revision == 1
    else:
        document = json.loads(Path(selected.document_path).read_text(encoding="utf-8"))
        service = FigureProjectService(output_root)
        saved = service.save_working(
            run_id=publication.run_id,
            figure_id=selected.figure_id,
            document=document,
        )
        published = service.publish(run_id=publication.run_id, figure_id=selected.figure_id)
        assert saved.entry.working_revision == 2
        assert published.entry.published_revision == 2

    refreshed = next(
        entry
        for entry in build_active_manifest_gallery_entries(output_root)
        if entry.figure_id == selected.figure_id
    )
    assert refreshed.run_id == publication.run_id
    assert refreshed.working_revision >= 1
    assert refreshed.published_revision >= 1

    bundle_root = tmp_path / "bundle"
    bundle_dirs = create_export_bundle_dirs(bundle_root)
    copied_sections = copy_export_bundle_sections(output_root, bundle_dirs)
    manifest_path = write_export_manifest(
        bundle_root,
        project_name="WAXS lifecycle",
        exported_at="2026-07-25T00:00:00Z",
        bundle_root=str(bundle_root),
        source_output_dir=str(output_root),
        source_data_path=str(source),
        current_technique="waxs",
        current_submodule=mode,
        input_mode="single",
        included_techniques=["waxs"],
        copied_sections=copied_sections,
        primary_report="",
        task_context={"submodule_id": mode},
    )
    export_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert export_payload["directories"]["figure_runs"] == "metadata/runs"
    assert export_payload["directories"]["active_figure_run"] == "metadata/active_run.json"
    assert (bundle_root / "metadata" / "runs" / publication.run_id).is_dir()
    assert (bundle_root / "metadata" / "active_run.json").is_file()

    QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window._restore_history_record(
        {
            "id": f"history-{mode}",
            "technique": "waxs",
            "submodule": mode,
            "created_at": "2026-07-25 00:00:00",
            "output_dir": str(output_root),
            "parameters": {},
            "results_summary": {"data_file": str(source)},
        }
    )
    restored_entries = build_active_manifest_gallery_entries(window._output_dir)
    assert [entry.figure_id for entry in restored_entries] == [entry.figure_id for entry in entries]
    assert window._current_submodule_id == mode
