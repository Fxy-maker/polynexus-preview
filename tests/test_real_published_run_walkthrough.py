from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.engine import get_engine
from polynexus.core.figure_document import load_figure_document
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


def _real_cases() -> tuple[tuple[str, str, Path], ...]:
    repository_root = Path(__file__).resolve().parents[1]
    data_root = repository_root / "\u6d4b\u8bd5\u6570\u636e"
    dsc_source = next((data_root / "dsc").rglob("FXY-PA6.txt"))
    waxs_static_source = next((data_root / "waxs").rglob("PA6.raw"))
    waxs_temperature_source = next(
        path.parent
        for path in (data_root / "waxs").rglob("PA6-250-170-W_0_00002.edf")
    )
    ir_standard_source = next((data_root / "IR").rglob("YL.SPA"))
    nmr_root = data_root / "NMR"
    return (
        ("dsc", "dsc.standard", dsc_source),
        ("waxs", "waxs.static", waxs_static_source),
        ("waxs", "waxs.temperature", waxs_temperature_source),
        ("ir", "ir.standard", ir_standard_source),
        (
            "nmr",
            "nmr.liquid_h",
            nmr_root / "\u6db2\u4f53\u6838\u78c1" / "H\u8c31" / "fid",
        ),
        (
            "nmr",
            "nmr.liquid_c",
            nmr_root / "\u6db2\u4f53\u6838\u78c1" / "C\u8c31" / "fid",
        ),
        (
            "nmr",
            "nmr.solid_h",
            nmr_root
            / "\u56fa\u4f53nmr\u6c22\u8c31"
            / "CXD_20250410_H_single_pulse-1-1.jdf",
        ),
        (
            "nmr",
            "nmr.solid_c",
            nmr_root
            / "\u56fa\u4f53nmr\u78b3\u8c31"
            / "CXD_20250409_HC_cpmas-1-1.jdf",
        ),
    )


@pytest.mark.parametrize("technique,mode,source", _real_cases())
def test_real_published_run_preserves_shared_lifecycle(
    tmp_path: Path,
    technique: str,
    mode: str,
    source: Path,
) -> None:
    if not source.exists():
        pytest.skip(f"real fixture unavailable: {source}")

    output_root = tmp_path / "output"
    config = {"fig_format": "png"}
    if technique == "nmr":
        config["max_peaks"] = 18
    engine = get_engine(technique, config=config, submodule_id=mode)
    result = engine.run_pipeline(str(source), str(output_root))

    run_id = str(result.metadata.get("figure_run_id") or "")
    manifest_path = Path(str(result.metadata.get("figure_manifest") or ""))
    assert run_id
    assert manifest_path.is_file()
    assert hasattr(result, "validation_passed")

    entries = build_active_manifest_gallery_entries(output_root)
    assert entries
    assert {entry.run_id for entry in entries} == {run_id}
    selected = next(entry for entry in entries if entry.publication_role == "main")

    document = load_figure_document(selected.document_path)
    project = FigureProjectService(output_root)
    saved = project.save_working(
        run_id=run_id,
        figure_id=selected.figure_id,
        document=document,
    )
    published = project.publish(run_id=run_id, figure_id=selected.figure_id)
    assert saved.entry.working_revision >= 2
    assert published.entry.published_revision >= saved.entry.working_revision

    refreshed = next(
        entry
        for entry in build_active_manifest_gallery_entries(output_root)
        if entry.figure_id == selected.figure_id
    )
    assert refreshed.run_id == run_id
    assert refreshed.working_revision == saved.entry.working_revision
    assert refreshed.published_revision == published.entry.published_revision

    bundle_root = tmp_path / "bundle"
    bundle_dirs = create_export_bundle_dirs(bundle_root)
    copied_sections = copy_export_bundle_sections(output_root, bundle_dirs)
    export_manifest = write_export_manifest(
        bundle_root,
        project_name=f"{technique} real walkthrough",
        exported_at="2026-07-26T00:00:00Z",
        bundle_root=str(bundle_root),
        source_output_dir=str(output_root),
        source_data_path=str(source),
        current_technique=technique,
        current_submodule=mode,
        input_mode="directory" if source.is_dir() else "single",
        included_techniques=[technique],
        copied_sections=copied_sections,
        primary_report="",
        task_context={"submodule_id": mode, "validation_passed": result.validation_passed},
    )
    export_payload = json.loads(export_manifest.read_text(encoding="utf-8"))
    assert export_payload["directories"]["figure_runs"] == "metadata/runs"
    assert export_payload["directories"]["active_figure_run"] == "metadata/active_run.json"
    assert (bundle_root / "metadata" / "runs" / run_id).is_dir()
    assert (bundle_root / "metadata" / "active_run.json").is_file()

    QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window._restore_history_record(
        {
            "id": f"real-{mode}",
            "technique": technique,
            "submodule": mode,
            "created_at": "2026-07-26 00:00:00",
            "output_dir": str(output_root),
            "parameters": {},
            "results_summary": {"data_file": str(source)},
        }
    )
    restored_entries = build_active_manifest_gallery_entries(window._output_dir)
    assert {entry.figure_id for entry in restored_entries} == {
        entry.figure_id for entry in entries
    }
    assert {entry.run_id for entry in restored_entries} == {run_id}
    assert window._current_submodule_id == mode
