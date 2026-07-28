from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.figures.project_service import FigureProjectService
from polynexus.core.joint.coordinator import JointCoordinator
from polynexus.core.joint.dataset import JointBatchRow, JointRunRecord
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


def _rows() -> list[JointBatchRow]:
    return [
        JointBatchRow(
            sample_id="sample-a",
            sample_name="PA6-A",
            family="polyamide",
            batch_id="batch-a",
            batch_label="annealed",
            runs={
                "dsc": JointRunRecord("dsc-a", "dsc", results_summary={"Xc_pct": 42.0}),
                "waxs": JointRunRecord(
                    "waxs-a",
                    "waxs",
                    results_summary={"Xc_pct": 39.0, "D_Scherrer_nm": 7.0},
                ),
                "saxs": JointRunRecord(
                    "saxs-a",
                    "saxs",
                    results_summary={"L_nm": 12.0, "lc_nm": 5.0},
                ),
            },
        )
    ]


def test_joint_publish_editor_export_and_history_restore_are_one_run(tmp_path: Path) -> None:
    output_root = tmp_path / "joint-output"
    report = JointCoordinator().publish_hub_report(
        _rows(),
        output_root,
        run_id="joint-lifecycle-run",
    )

    entries = build_active_manifest_gallery_entries(output_root)
    assert {entry.figure_id for entry in entries} == {
        "joint.series.crystallinity",
        "joint.series.multiscale",
        "joint.series.coverage",
    }
    assert {entry.run_id for entry in entries} == {"joint-lifecycle-run"}
    selected = next(entry for entry in entries if entry.publication_role == "main")

    document = json.loads(Path(selected.document_path).read_text(encoding="utf-8"))
    project_service = FigureProjectService(output_root)
    working = project_service.save_working(
        run_id=selected.run_id,
        figure_id=selected.figure_id,
        document=document,
    )
    published = project_service.publish(run_id=selected.run_id, figure_id=selected.figure_id)
    assert working.entry.working_revision == 2
    assert published.entry.published_revision == 2

    bundle_root = tmp_path / "joint-bundle"
    bundle_dirs = create_export_bundle_dirs(bundle_root)
    copied_sections = copy_export_bundle_sections(output_root, bundle_dirs)
    manifest_path = write_export_manifest(
        bundle_root,
        project_name="Joint lifecycle",
        exported_at="2026-07-25T00:00:00Z",
        bundle_root=str(bundle_root),
        source_output_dir=str(output_root),
        source_data_path="",
        current_technique="joint",
        current_submodule="joint.compare",
        input_mode="joint",
        included_techniques=["joint"],
        copied_sections=copied_sections,
        primary_report="",
        task_context={"figure_run_id": report["figure_publication"]["run_id"]},
    )
    export_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert export_payload["directories"]["figure_runs"] == "metadata/runs"
    assert export_payload["directories"]["active_figure_run"] == "metadata/active_run.json"
    assert (bundle_root / "metadata" / "runs" / "joint-lifecycle-run").is_dir()
    assert (bundle_root / "metadata" / "active_run.json").is_file()

    QApplication.instance() or QApplication([])
    window = MainWindow()
    record = {
        "id": "joint-lifecycle-run",
        "technique": "joint",
        "submodule": "joint.compare",
        "created_at": "2026-07-25T00:00:00Z",
        "output_dir": str(output_root),
        "parameters": {},
        "results_summary": {
            "result": report,
            "figure_run_id": "joint-lifecycle-run",
            "history_context": {},
        },
    }
    assert window._restore_history_record(record)
    assert window._joint_report == report
    assert window._project_label.text() == "PA6-A"
    assert window._results_panel.profile.key == "joint"
    restored_entries = build_active_manifest_gallery_entries(window._output_dir)
    assert {entry.figure_id for entry in restored_entries} == {
        "joint.series.crystallinity",
        "joint.series.multiscale",
        "joint.series.coverage",
    }
    assert {entry.run_id for entry in restored_entries} == {"joint-lifecycle-run"}
