from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QAbstractItemView

from polynexus.core.project_workflow.evidence_view import EvidencePackageView, load_evidence_package_view
from polynexus.gui.evidence_package_view import EvidencePackageDialog, EvidencePackageViewAdapter


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text(json.dumps({
        "package_id": "pa6", "version": 1, "status": "review_required",
        "run_ids": ["run-dsc"], "limitations": ["background_review"],
        "citation_metrics": "citation-metrics.json", "ars_writing_input": "ars-writing-input.json",
    }), encoding="utf-8")
    (package / "techniques.json").write_text(json.dumps({"techniques": {
        "dsc": {"run_ids": ["run-dsc"], "statuses": ["review_required"], "evidence_count": 1},
    }}), encoding="utf-8")
    (package / "writing-evidence.json").write_text(json.dumps({"techniques": {"dsc": {"run_ids": ["run-dsc"], "statuses": ["review_required"], "evidence": [{
        "evidence_id": "run-dsc:step", "status": "review_required", "source_runs": ["run-dsc"],
        "raw_sources": ["raw-dsc"], "figures": ["figures/dsc.svg"], "tables": [],
        "citation_metric_ids": ["metric-dsc", "metric-diagnostic"], "citation_metric_counts": {"results_candidate": 1, "diagnostic_only": 1},
        "supported_interpretations": ["observed"], "disallowed_conclusions": ["human_review_required"], "limitations": [],
    }]}}}), encoding="utf-8")
    (package / "citation-metrics.json").write_text(json.dumps({"version": 1, "records": [{
        "metric_id": "metric-dsc", "technique": "dsc", "metric_key": "t_half_min", "value": 1.2,
        "unit": "min", "method": "dsc.isothermal_avrami_fit", "source_locator": "parameters.segment_01.t_half_min",
        "evidence_id": "run-dsc:step", "run_id": "run-dsc", "raw_source_hashes": ["raw-dsc"],
        "status": "review_required", "writing_eligibility": "results_candidate", "reason_codes": [],
        "figures": ["figures/dsc.svg"], "tables": [],
    }, {
        "metric_id": "metric-diagnostic", "technique": "dsc", "metric_key": "diagnostic", "value": 2.0,
        "unit": "index", "method": "provider", "source_locator": "parameters.diagnostic",
        "evidence_id": "run-dsc:step", "run_id": "run-dsc", "raw_source_hashes": ["raw-dsc"],
        "status": "review_required", "writing_eligibility": "diagnostic_only", "reason_codes": ["review"],
        "figures": [], "tables": [],
    }]}), encoding="utf-8")
    (package / "ars-writing-input.json").write_text(json.dumps({
        "version": 1, "techniques": {"dsc": {"evidence": [{"evidence_id": "run-dsc:step", "results_metric_ids": ["metric-dsc"], "discussion_metric_ids": ["metric-diagnostic"]}]}},
        "allowed_results": ["metric-dsc"], "discussion_only": ["metric-diagnostic"], "human_review": [{"evidence_id": "run-dsc:step", "action": "human_scientific_review", "reason": "human_review_required"}],
    }), encoding="utf-8")
    (package / "limitations.json").write_text(json.dumps({"limitations": ["background_review"]}), encoding="utf-8")
    return package


def test_load_package_view_exposes_technique_neutral_rows_and_review(tmp_path: Path) -> None:
    view = load_evidence_package_view(_package(tmp_path))
    assert isinstance(view, EvidencePackageView)
    assert view.status == "review_required"
    assert view.techniques[0].key == "dsc"
    assert view.metrics[0].metric_id == "metric-dsc"
    assert view.metrics[0].source_locator.endswith("t_half_min")
    assert view.human_review[0].action == "human_scientific_review"
    assert view.evidence[0].discussion_metric_ids == ("metric-diagnostic",)


def test_load_package_view_preserves_shared_metric_metadata_and_result_tables(tmp_path: Path) -> None:
    package = _package(tmp_path)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    manifest["result_tables"] = "result-tables.json"
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    metrics = json.loads((package / "citation-metrics.json").read_text(encoding="utf-8"))
    metrics["records"][0].update({
        "descriptor_id": "dsc.Tm.v1",
        "computation_state": {
            "data_availability": "canonical",
            "computability": "computed",
            "validity": "diagnostic",
            "promotion": "diagnostic_only",
        },
        "provenance": {"algorithm": "peak.v2"},
        "uncertainty": {"kind": "std", "value": 1.5},
    })
    (package / "citation-metrics.json").write_text(json.dumps(metrics), encoding="utf-8")
    (package / "result-tables.json").write_text(json.dumps({
        "tables": [{"group_id": "dsc:step", "technique": "dsc", "rows": []}],
    }), encoding="utf-8")

    view = load_evidence_package_view(package)

    metric = view.metrics[0]
    assert metric.descriptor_id == "dsc.Tm.v1"
    assert metric.computation_state["computability"] == "computed"
    assert metric.provenance == {"algorithm": "peak.v2"}
    assert metric.uncertainty == {"kind": "std", "value": 1.5}
    assert view.result_tables[0]["group_id"] == "dsc:step"


def test_load_package_view_exposes_indexed_logical_figures(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (package / "figures").mkdir()
    (package / "figures" / "dsc.svg").write_text("<svg/>", encoding="utf-8")
    (package / "figure-index.json").write_text(json.dumps({
        "version": 1,
        "figures": [{
            "id": "dsc", "role": "supporting", "technique": "DSC",
            "group": None, "writing_eligibility": "Results",
            "svg": "figures/dsc.svg", "document": None, "data": None,
            "metadata": "figures/dsc.metadata.json",
        }],
    }), encoding="utf-8")
    view = load_evidence_package_view(package)
    assert len(view.figure_views) == 1
    assert view.figure_views[0].svg == "figures/dsc.svg"
    assert view.figure_views[0].document is None
    assert view.package_root == str(package.resolve())


def test_gui_adapter_returns_only_the_view_model(tmp_path: Path) -> None:
    view = load_evidence_package_view(_package(tmp_path))
    summary = EvidencePackageViewAdapter(view).summary()
    assert summary == {"status": "review_required", "techniques": ("dsc",), "metric_count": 2, "human_review_count": 1}


def test_gui_adapter_projects_package_gallery_from_index(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (package / "figures").mkdir()
    (package / "figures" / "dsc.svg").write_text("<svg/>", encoding="utf-8")
    view = load_evidence_package_view(package)
    entries = EvidencePackageViewAdapter(view).gallery_entries()

    assert [entry.figure_id for entry in entries] == ["dsc"]
    assert entries[0].primary_path.endswith("figures\\dsc.svg")
    assert entries[0].state == "static_background"


def test_dialog_renders_read_only_package_tabs_and_metric_provenance(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    package = _package(tmp_path)
    (package / "figures").mkdir()
    (package / "figures" / "dsc.svg").write_text("<svg/>", encoding="utf-8")
    view = load_evidence_package_view(package)
    dialog = EvidencePackageDialog(view)

    assert [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())] == [
        "Overview", "Evidence", "Metrics", "Review", "Gallery",
    ]
    assert dialog.gallery.figure_ids() == ["dsc"]
    assert dialog.gallery.is_read_only
    edit_requests: list[object] = []
    dialog.gallery.edit_requested.connect(edit_requests.append)
    dialog.gallery._thumbnails[0]._emit_primary_action()
    assert edit_requests == []
    dialog.gallery._on_batch_checked("dsc", True)
    assert dialog.gallery._btn_batch_edit.isHidden()
    assert dialog.metrics_table.columnCount() == 7
    assert dialog.metrics_table.item(0, 3).text() == "dsc.isothermal_avrami_fit"
    assert dialog.review_table.item(0, 1).text() == "human_scientific_review"
    assert dialog.metrics_table.editTriggers() == QAbstractItemView.NoEditTriggers
    assert dialog.review_table.editTriggers() == QAbstractItemView.NoEditTriggers
    assert dialog.package_limitations.wordWrap()


def test_dialog_gallery_exposes_technique_and_group_filters(tmp_path: Path) -> None:
    QApplication.instance() or QApplication([])
    package = _package(tmp_path)
    (package / "figures").mkdir()
    (package / "figures" / "dsc.svg").write_text("<svg/>", encoding="utf-8")
    (package / "figures" / "ir.svg").write_text("<svg/>", encoding="utf-8")
    (package / "figures" / "dsc.metadata.json").write_text("{}", encoding="utf-8")
    (package / "figures" / "ir.metadata.json").write_text("{}", encoding="utf-8")
    (package / "figure-index.json").write_text(json.dumps({
        "version": 1,
        "figures": [
            {
                "id": "dsc",
                "role": "supporting",
                "technique": "dsc",
                "group": "thermal",
                "writing_eligibility": "Results",
                "svg": "figures/dsc.svg",
                "document": None,
                "data": None,
                "metadata": "figures/dsc.metadata.json",
            },
            {
                "id": "ir",
                "role": "diagnostic",
                "technique": "ir",
                "group": "JW",
                "writing_eligibility": "Discussion",
                "svg": "figures/ir.svg",
                "document": None,
                "data": None,
                "metadata": "figures/ir.metadata.json",
            },
        ],
    }), encoding="utf-8")
    view = load_evidence_package_view(package)
    dialog = EvidencePackageDialog(view)

    assert dialog._gallery_technique_combo.findData("dsc") >= 0
    assert dialog._gallery_group_combo.findData("JW") >= 0
    dialog._gallery_technique_combo.setCurrentIndex(
        dialog._gallery_technique_combo.findData("ir")
    )
    QApplication.processEvents()
    assert dialog.gallery.figure_ids() == ["ir"]
    dialog._gallery_group_combo.setCurrentIndex(
        dialog._gallery_group_combo.findData("JW")
    )
    QApplication.processEvents()
    assert dialog.gallery.figure_ids() == ["ir"]
    dialog._gallery_technique_combo.setCurrentIndex(
        dialog._gallery_technique_combo.findData("")
    )
    dialog._gallery_group_combo.setCurrentIndex(
        dialog._gallery_group_combo.findData("")
    )
    QApplication.processEvents()
    assert dialog.gallery.figure_ids() == ["dsc", "ir"]


def test_loader_rejects_metric_evidence_mismatch(tmp_path: Path) -> None:
    package = _package(tmp_path)
    payload = json.loads((package / "citation-metrics.json").read_text(encoding="utf-8"))
    payload["records"][0]["evidence_id"] = "tampered"
    (package / "citation-metrics.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="metric"):
        load_evidence_package_view(package)
