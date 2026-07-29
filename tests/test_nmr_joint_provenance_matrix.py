from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from dataclasses import replace

from polynexus.core.figures.pipeline import FigurePipeline
from polynexus.core.joint.coordinator import JointCoordinator
from polynexus.core.joint.dataset import JointBatchRow, JointRunRecord
from polynexus.core.nmr import NMREngine
from polynexus.core.nmr_engine.core import NMRResult
from polynexus.core.nmr_engine.figure_provider import build_nmr_figure_definitions
from polynexus.gui.plot_gallery_service import build_active_manifest_gallery_entries


def _nmr_engine() -> NMREngine:
    engine = NMREngine()
    engine.active_submodule = "nmr.liquid_c"
    engine._results = [
        NMRResult(
            label="liquid-c",
            nucleus="13C",
            sample_state="liquid",
            ppm=np.array([180.0, 100.0, 20.0]),
            intensity=np.array([0.1, 0.5, 0.15]),
            intensity_fit=np.array([0.11, 0.48, 0.16]),
            peaks=[{"ppm": 100.0, "height": 0.5, "prominence": 0.4, "assignment": "backbone"}],
        )
    ]
    return engine


def _joint_rows() -> list[JointBatchRow]:
    review = {
        "record_id": "review-joint-provenance",
        "scope": "joint",
        "reviewer": "reviewer-a",
        "reviewed_at": "2026-07-29T00:00:00Z",
        "policy_version": "joint-v1",
        "source_refs": ["batch-a"],
        "decisions": {
            "conflict_precedence": "retain source-specific values and surface conflicts",
            "minimum_evidence": "accepted technique evidence for selected batch",
            "unresolved_conflict_policy": "diagnostic until human resolution",
        },
        "status": "accepted",
        "conditions": [],
    }
    return [
        JointBatchRow(
            sample_id="sample-a",
            sample_name="PA6-A",
            family="polyamide",
            batch_id="batch-a",
            batch_label="annealed",
            runs={
                "dsc": JointRunRecord("dsc-a", "dsc", results_summary={"Xc_pct": 42.0}),
                "waxs": JointRunRecord("waxs-a", "waxs", results_summary={"Xc_pct": 39.0, "D_Scherrer_nm": 7.0}),
                "saxs": JointRunRecord("saxs-a", "saxs", results_summary={"L_nm": 12.0, "lc_nm": 5.0}),
            },
            scientific_review=review,
        )
    ]


def _assert_gallery_documents_are_run_relative(output_root: Path, expected_ids: set[str]) -> None:
    entries = build_active_manifest_gallery_entries(output_root)
    assert {entry.figure_id for entry in entries} == expected_ids
    assert all(entry.run_id for entry in entries)
    assert all(entry.state == "object_editing" for entry in entries)
    for entry in entries:
        run_root = Path(entry.run_root)
        document = json.loads(Path(entry.document_path).read_text(encoding="utf-8"))
        assert Path(entry.document_path).is_relative_to(run_root)
        assert all(Path(path).is_relative_to(run_root) for path in entry.asset_paths)
        assert all(
            str(source["path"]).startswith("figures/")
            and source["path_kind"] == "run_relative"
            for source in document["data_sources"]
        )


def test_nmr_plot_publishes_manifest_gallery_and_main_role(tmp_path: Path) -> None:
    engine = _nmr_engine()

    engine.plot(str(tmp_path))

    _assert_gallery_documents_are_run_relative(
        tmp_path,
        {"nmr.frame.spectrum.001", "nmr.frame.deconvolution.001"},
    )
    entries = build_active_manifest_gallery_entries(tmp_path)
    by_id = {entry.figure_id: entry for entry in entries}
    assert by_id["nmr.frame.spectrum.001"].publication_role == "main"
    assert by_id["nmr.frame.deconvolution.001"].publication_role == "diagnostic"


def test_joint_coordinator_publishes_manifest_gallery_and_role_provenance(tmp_path: Path) -> None:
    report = JointCoordinator().publish_hub_report(_joint_rows(), tmp_path, run_id="joint-provenance")

    assert report["figure_publication"]["run_id"] == "joint-provenance"
    _assert_gallery_documents_are_run_relative(
        tmp_path,
        {
            "joint.series.crystallinity",
            "joint.series.multiscale",
            "joint.series.coverage",
        },
    )
    entries = build_active_manifest_gallery_entries(tmp_path)
    by_id = {entry.figure_id: entry for entry in entries}
    assert by_id["joint.series.crystallinity"].publication_role == "main"
    assert by_id["joint.series.multiscale"].publication_role == "si"
    assert by_id["joint.series.coverage"].publication_role == "diagnostic"


def test_failed_diagnostic_definition_stays_visible_in_manifest(tmp_path: Path) -> None:
    definition = build_nmr_figure_definitions(_nmr_engine()._results)[1]
    invalid = replace(
        definition,
        figure_id="nmr.frame.deconvolution.invalid",
        objects=({"id": "broken", "type": "plot_series", "panel_id": "main", "data_ref": "missing", "x_column": "ppm", "y_column": "intensity"},),
    )

    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id="nmr-failure-visible",
        technique="nmr",
        definitions=(invalid,),
    )

    entry = manifest.figures[0]
    assert entry.status == "generation_failed"
    assert entry.publication_role == "diagnostic"
    assert entry.error
