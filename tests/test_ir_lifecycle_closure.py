from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from polynexus.core.figures.production import FigureProductionPublisher
from polynexus.core.figures.project_service import FigureProjectService
from polynexus.core.ir_engine.core import IRResult
from polynexus.core.ir_engine.figure_provider import (
    build_ir_figure_definitions,
    build_ir_temperature_2d_figure_definitions,
)
from polynexus.core.ir_engine.io import IRSpectrum
from polynexus.core.ir_engine.ir_mapping import IRMappingROISpectrum, IRMappingResult, build_ir_mapping_figure_definitions
from polynexus.core.ir_engine.ir_temperature import IRTemp2DResult, IRTempFrame
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


def _standard_definitions():
    results = (
        IRResult(
            label="sample-a",
            wavenumber=np.array([1800.0, 1700.0, 1600.0]),
            absorbance=np.array([0.1, 0.4, 0.2]),
            absorbance_fit=np.array([0.12, 0.38, 0.21]),
            simulated_spectrum=IRSpectrum(
                label="computed-a",
                wavenumber=np.array([1820.0, 1710.0, 1590.0]),
                absorbance=np.array([0.08, 0.35, 0.18]),
                source="computation",
            ),
            peaks=[{"wavenumber": 1700.0, "height": 0.4, "prominence": 0.3, "assignment": "amide I"}],
            Xc_pct=31.0,
        ),
        IRResult(
            label="sample-b",
            wavenumber=np.array([1800.0, 1700.0, 1600.0]),
            absorbance=np.array([0.09, 0.32, 0.17]),
            Xc_pct=46.5,
        ),
    )
    return build_ir_figure_definitions(results)


def _temperature_definitions():
    result = IRTemp2DResult(
        frames=[
            IRTempFrame(label="H100", stage="heating", temperature_C=100.0, time_min=2.5, sequence_order_source="metadata"),
            IRTempFrame(label="H110", stage="hold", temperature_C=110.0, time_min=5.0, sequence_order_source="metadata"),
        ],
        wavenumber=np.array([1000.0, 1100.0]),
        absorbance_matrix=np.array([[0.1, 0.2], [0.2, 0.3]]),
        band_intensity_vs_frame={"amide": [0.1, 0.2]},
        band_indices_vs_frame={"ratio": [1.0, 1.1]},
        sync_corr=np.eye(2),
        async_corr=np.eye(2),
    )
    return build_ir_temperature_2d_figure_definitions(result)


def _mapping_definitions():
    result = IRMappingResult(
        label="map-a",
        map_values=np.array([[0.1, 0.2], [0.3, np.nan]]),
        row_coordinates=np.array([10.0, 20.0]),
        column_coordinates=np.array([1000.0, 1100.0]),
        invalid_pixel_mask=np.array([[False, False], [False, True]]),
        map_metric="absorbance at 1650 cm^-1",
        roi_spectra=(
            IRMappingROISpectrum(
                roi_id="roi-1",
                label="center",
                wavenumber=np.array([1800.0, 1700.0, 1600.0]),
                absorbance=np.array([0.1, 0.2, 0.15]),
                valid_pixel_count=3,
                assignments=("amide I",),
            ),
        ),
        provenance={
            "source_kind": "explicit_mapping_payload",
            "source_id": "map-a.json",
            "scientific_review": {
                "record_id": "review-ir-map-lifecycle",
                "scope": "ir.mapping",
                "reviewer": "lifecycle-reviewer",
                "reviewed_at": "2026-07-29T00:00:00Z",
                "policy_version": "ir-map-v1",
                "source_refs": ["map-a.json"],
                "decisions": {
                    "coordinate_convention": "consume supplied row/column coordinates",
                    "roi_inclusion_policy": "explicit ROI only",
                    "invalid_pixel_policy": "preserve mask; no interpolation",
                    "promotion_rule": "accepted source-matching review",
                },
                "status": "accepted",
                "conditions": [],
            },
        },
    )
    return build_ir_mapping_figure_definitions(result)


@pytest.mark.parametrize("mode", ("ir.standard", "ir.temperature_2d", "ir.mapping"))
def test_ir_modes_complete_manifest_editor_export_history_lifecycle(tmp_path: Path, mode: str):
    source = tmp_path / "ir_input.spc"
    source.write_text("explicit test source\n", encoding="utf-8")
    definitions = {
        "ir.standard": _standard_definitions,
        "ir.temperature_2d": _temperature_definitions,
        "ir.mapping": _mapping_definitions,
    }[mode]()
    output_root = tmp_path / "output"
    publication = FigureProductionPublisher().publish(
        output_root=output_root,
        technique="ir",
        definitions=definitions,
        profile_id="paper_complete",
    )
    entries = build_active_manifest_gallery_entries(output_root)
    assert entries
    assert {entry.figure_id for entry in entries} == {
        item.figure_id for item in publication.manifest.figures
    }
    assert all(entry.run_id == publication.run_id for entry in entries)
    assert any(entry.publication_role == "main" for entry in entries)

    selected = next(entry for entry in entries if entry.publication_role == "main")
    document = json.loads(Path(selected.document_path).read_text(encoding="utf-8"))
    if mode == "ir.mapping":
        assert document["recipe"]["provenance"]["source_id"] == "map-a.json"
        assert document["recipe"]["invalid_pixel_count"] == 1
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
    assert refreshed.working_revision == 2
    assert refreshed.published_revision == 2

    bundle_root = tmp_path / "bundle"
    bundle_dirs = create_export_bundle_dirs(bundle_root)
    copied_sections = copy_export_bundle_sections(output_root, bundle_dirs)
    manifest_path = write_export_manifest(
        bundle_root,
        project_name="IR lifecycle",
        exported_at="2026-07-25T00:00:00Z",
        bundle_root=str(bundle_root),
        source_output_dir=str(output_root),
        source_data_path=str(source),
        current_technique="ir",
        current_submodule=mode,
        input_mode="single",
        included_techniques=["ir"],
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
            "technique": "ir",
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
