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

from polynexus.core.dsc import DSCEngine
from polynexus.core.dsc_engine.figure_provider import build_dsc_figure_definitions
from polynexus.core.figure_document import load_figure_document
from polynexus.core.figures.production import FigureProductionPublisher
from polynexus.core.figures.project_service import FigureProjectService
from polynexus.gui.export_context_service import (
    copy_export_bundle_sections,
    create_export_bundle_dirs,
    write_export_manifest,
)
from polynexus.gui.main_window import MainWindow
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries


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


def _isothermal_engine():
    avrami = SimpleNamespace(
        label="150 C",
        t_data=np.arange(6.0),
        Xt_data=np.array([0.02, 0.12, 0.35, 0.60, 0.82, 0.95]),
        Xt_fit=np.array([0.01, 0.13, 0.34, 0.59, 0.81, 0.94]),
        n=2.0,
        k=0.1,
        t_half_min=3.0,
        r_squared=0.97,
        quality_flags=[],
    )
    return SimpleNamespace(
        active_submodule="dsc.isothermal",
        _results=[],
        _kinetics_data={"avrami": avrami, "avrami_series": [avrami]},
    )


def _nonisothermal_engine():
    curves = [
        SimpleNamespace(label="1 K/min", T_xt_C=np.arange(5.0), Xt=np.linspace(0.1, 0.9, 5)),
        SimpleNamespace(label="2 K/min", T_xt_C=np.arange(5.0) + 1.0, Xt=np.linspace(0.1, 0.9, 5)),
    ]
    series = SimpleNamespace(curves=curves)
    kissinger = SimpleNamespace(
        rates=[1.0, 2.0, 5.0],
        r_squared=0.96,
        kissinger_Ea_kJmol=120.0,
        quality_flags=[],
    )
    return SimpleNamespace(
        active_submodule="dsc.nonisothermal",
        _results=[],
        _kinetics_data={"non_isothermal": series, "kissinger": kissinger},
    )


def _completed_engine(mode: str, source: Path):
    if mode == "dsc.standard":
        engine = DSCEngine()
        engine.active_submodule = mode
        assert engine.load(str(source))
        assert engine.preprocess()
        assert engine.analyze()
        return engine
    if mode == "dsc.isothermal":
        return _isothermal_engine()
    return _nonisothermal_engine()


@pytest.mark.parametrize("mode", ("dsc.standard", "dsc.isothermal", "dsc.nonisothermal"))
def test_dsc_modes_complete_manifest_editor_export_history_lifecycle(tmp_path: Path, mode: str):
    if mode == "dsc.standard":
        source = Path(__file__).parent / "eval" / "synth_data" / "dsc_synth_heating_standard.xy"
    else:
        source = tmp_path / f"{mode.replace('.', '_')}.xy"
        source.write_text("0 1\n1 2\n2 1\n", encoding="utf-8")
    output_root = tmp_path / "output"
    engine = _completed_engine(mode, source)
    definitions = build_dsc_figure_definitions(engine)

    production = FigureProductionPublisher().publish(
        output_root=output_root,
        technique="dsc",
        definitions=definitions,
        profile_id="dsc_publication",
    )
    entries = build_active_manifest_gallery_entries(output_root)
    assert entries
    assert {entry.figure_id for entry in entries} == {
        item.figure_id for item in production.manifest.figures
    }
    assert all(entry.run_id == production.run_id for entry in entries)
    assert any(entry.publication_role == "main" for entry in entries)

    selected = next(entry for entry in entries if entry.publication_role == "main")
    document = load_figure_document(selected.document_path)
    document["objects"] = list(document.get("objects", ()))
    saved = FigureProjectService(output_root).save_working(
        run_id=production.run_id,
        figure_id=selected.figure_id,
        document=document,
    )
    assert saved.entry.working_revision == 2
    working_entry = next(
        entry
        for entry in build_active_manifest_gallery_entries(output_root)
        if entry.figure_id == selected.figure_id
    )
    assert working_entry.working_revision == 2
    assert working_entry.published_revision == 1
    assert "/revisions/r0002/" in working_entry.document_path.replace("\\", "/")
    published = FigureProjectService(output_root).publish(
        run_id=production.run_id,
        figure_id=selected.figure_id,
    )
    assert published.entry.published_revision == 2
    published_entry = next(
        entry
        for entry in build_active_manifest_gallery_entries(output_root)
        if entry.figure_id == selected.figure_id
    )
    assert published_entry.working_revision == 2
    assert published_entry.published_revision == 2
    assert "/publications/r0002/" in published_entry.document_path.replace("\\", "/")

    bundle_root = tmp_path / "bundle"
    bundle_dirs = create_export_bundle_dirs(bundle_root)
    copied_sections = copy_export_bundle_sections(output_root, bundle_dirs)
    manifest_path = write_export_manifest(
        bundle_root,
        project_name="DSC lifecycle",
        exported_at="2026-07-25T00:00:00Z",
        bundle_root=str(bundle_root),
        source_output_dir=str(output_root),
        source_data_path=str(source),
        current_technique="dsc",
        current_submodule=mode,
        input_mode="single",
        included_techniques=["dsc"],
        copied_sections=copied_sections,
        primary_report="",
        task_context={"submodule_id": mode},
    )
    export_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "figure_runs" in export_payload["directories"]
    assert "active_figure_run" in export_payload["directories"]
    assert (bundle_root / "metadata" / "runs" / production.run_id).is_dir()
    assert (bundle_root / "metadata" / "active_run.json").is_file()

    QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window._restore_history_record(
        {
            "id": f"history-{mode}",
            "technique": "dsc",
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
