from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.engine import get_engine
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


def _nmr_sources() -> dict[str, Path]:
    root = Path(__file__).parent.parent / "测试数据" / "NMR"
    return {
        "nmr.liquid_h": root / "液体核磁" / "H谱",
        "nmr.liquid_c": root / "液体核磁" / "C谱",
        "nmr.solid_h": root / "固体nmr氢谱",
        "nmr.solid_c": root / "固体nmr碳谱",
    }


@pytest.mark.parametrize("mode", ("nmr.liquid_h", "nmr.liquid_c", "nmr.solid_h", "nmr.solid_c"))
def test_nmr_partitions_complete_real_data_lifecycle(tmp_path: Path, mode: str):
    source = _nmr_sources()[mode]
    if not source.exists():
        pytest.skip(f"NMR fixture unavailable: {source}")

    output_root = tmp_path / "output"
    engine = get_engine("nmr", config={"max_peaks": 18, "fig_format": "png"}, submodule_id=mode)
    result = engine.run_pipeline(str(source), str(output_root))
    assert result.validation_passed is True
    assert result.analysis_evidence["technique"] == "NMR"
    assert result.metadata["submodule"] == mode
    if mode == "nmr.solid_c":
        assert str(result.parameters.get("Xc_assignment_status") or "").lower() not in {"supported", "ready"}
        assert result.analysis_evidence["scientific_review"]["reason"] == "review_missing"

    entries = build_active_manifest_gallery_entries(output_root)
    assert entries
    assert all(entry.run_id for entry in entries)
    assert any(entry.publication_role == "diagnostic" for entry in entries)
    if mode == "nmr.solid_c":
        assert not any(entry.publication_role == "main" for entry in entries)
        selected = entries[0]
    else:
        assert any(entry.publication_role == "main" for entry in entries)
        selected = next(entry for entry in entries if entry.publication_role == "main")

    document = json.loads(Path(selected.document_path).read_text(encoding="utf-8"))
    service = FigureProjectService(output_root)
    saved = service.save_working(
        run_id=selected.run_id,
        figure_id=selected.figure_id,
        document=document,
    )
    published = service.publish(run_id=selected.run_id, figure_id=selected.figure_id)
    assert saved.entry.working_revision == 2
    assert published.entry.published_revision == 2

    refreshed = next(
        entry
        for entry in build_active_manifest_gallery_entries(output_root)
        if entry.figure_id == selected.figure_id
    )
    assert refreshed.working_revision == 2
    assert refreshed.published_revision == 2

    bundle_root = tmp_path / "bundle"
    bundle_dirs = create_export_bundle_dirs(bundle_root)
    copied_sections = copy_export_bundle_sections(output_root, bundle_dirs)
    manifest_path = write_export_manifest(
        bundle_root,
        project_name="NMR lifecycle",
        exported_at="2026-07-25T00:00:00Z",
        bundle_root=str(bundle_root),
        source_output_dir=str(output_root),
        source_data_path=str(source),
        current_technique="nmr",
        current_submodule=mode,
        input_mode="single",
        included_techniques=["nmr"],
        copied_sections=copied_sections,
        primary_report="",
        task_context={"submodule_id": mode},
    )
    export_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert export_payload["directories"]["figure_runs"] == "metadata/runs"
    assert export_payload["directories"]["active_figure_run"] == "metadata/active_run.json"
    assert (bundle_root / "metadata" / "runs" / selected.run_id).is_dir()
    assert (bundle_root / "metadata" / "active_run.json").is_file()

    QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window._restore_history_record(
        {
            "id": f"history-{mode}",
            "technique": "nmr",
            "submodule": mode,
            "created_at": "2026-07-25 00:00:00",
            "output_dir": str(output_root),
            "parameters": {},
            "results_summary": {"data_file": str(source)},
        }
    )
    restored_entries = build_active_manifest_gallery_entries(window._output_dir)
    assert restored_entries
    assert {entry.figure_id for entry in restored_entries} == {
        entry.figure_id for entry in entries
    }
    assert window._current_submodule_id == mode
