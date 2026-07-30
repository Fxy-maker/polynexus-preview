from __future__ import annotations

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from polynexus.core.scientific_review import (
    ScientificReviewRecord,
    review_decision_snapshot,
)
from polynexus.core.engine import AnalysisResult
from polynexus.data.sample_db import SampleDB


def _accepted_ir_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-workbench-1",
        scope="ir.mapping",
        reviewer="reviewer-a",
        reviewed_at="2026-07-30",
        policy_version="ir-map-v1",
        source_refs=("map-a.json",),
        decisions={
            "coordinate_convention": "vendor X columns and Y rows",
            "roi_inclusion_policy": "explicit mask",
            "invalid_pixel_policy": "masked",
            "promotion_rule": "source-matched review",
        },
        status="accepted",
    )


def test_update_analysis_scientific_review_is_run_scoped_and_round_trips(tmp_path) -> None:
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "mapping")
    first_id = db.create_analysis_run(
        batch_id,
        "ir",
        submodule="ir.mapping",
        results_summary={"result": {"metadata": {"source_id": "map-a.json"}}},
        analysis_evidence={"existing": "keep"},
    )
    second_id = db.create_analysis_run(
        batch_id,
        "ir",
        submodule="ir.mapping",
        results_summary={"result": {"metadata": {"source_id": "map-b.json"}}},
        analysis_evidence={"existing": "second"},
    )
    before_second = copy.deepcopy(db.get_analysis_run(second_id))

    record = _accepted_ir_record()
    snapshot = review_decision_snapshot(
        record,
        expected_scope="ir.mapping",
        source_ref="map-a.json",
    )

    assert db.update_analysis_scientific_review(first_id, record.to_dict(), snapshot) is True

    first = db.get_analysis_run(first_id)
    assert first["analysis_evidence"]["existing"] == "keep"
    assert first["analysis_evidence"]["scientific_review"] == snapshot
    assert first["analysis_evidence"]["scientific_review_record"] == record.to_dict()
    assert first["results_summary"]["result"]["metadata"]["scientific_review"] == record.to_dict()
    assert first["results_summary"]["result"]["metadata"]["scientific_review_decision"] == snapshot
    assert db.get_analysis_run(second_id) == before_second
    db.close()


def test_update_analysis_scientific_review_rejects_unknown_run_without_write(tmp_path) -> None:
    db = SampleDB(tmp_path / "samples.db")
    record = _accepted_ir_record()
    snapshot = review_decision_snapshot(record, expected_scope="ir.mapping", source_ref="map-a.json")

    assert db.update_analysis_scientific_review("missing", record.to_dict(), snapshot) is False
    db.close()


def test_persisted_review_is_visible_to_existing_history_presentation(tmp_path) -> None:
    from polynexus.gui.scientific_review_presentation import scientific_review_display

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "mapping")
    run_id = db.create_analysis_run(
        batch_id,
        "ir",
        submodule="ir.mapping",
        results_summary={"result": {"metadata": {"source_id": "map-a.json"}}},
    )
    record = _accepted_ir_record()
    snapshot = review_decision_snapshot(record, expected_scope="ir.mapping", source_ref="map-a.json")
    assert db.update_analysis_scientific_review(run_id, record.to_dict(), snapshot) is True

    run = db.get_analysis_run(run_id)
    display = scientific_review_display(run, technique="ir", submodule="ir.mapping")

    assert display.status == "accepted"
    assert display.record_id == "review-workbench-1"
    assert display.source_ref == "map-a.json"
    db.close()


def test_scientific_review_dialog_builds_a_validated_record() -> None:
    from polynexus.gui.scientific_review_dialog import ScientificReviewDialog

    QApplication.instance() or QApplication([])
    dialog = ScientificReviewDialog("ir.mapping", source_refs=("map-a.json",))
    dialog.set_field("record_id", "review-dialog-1")
    dialog.set_field("reviewer", "reviewer-a")
    dialog.set_field("reviewed_at", "2026-07-30")
    dialog.set_field("policy_version", "ir-map-v1")
    dialog.set_status("accepted")
    for key, value in {
        "coordinate_convention": "vendor X columns and Y rows",
        "roi_inclusion_policy": "explicit mask",
        "invalid_pixel_policy": "masked",
        "promotion_rule": "source-matched review",
    }.items():
        dialog.set_decision_value(key, value)

    record = dialog.build_record()

    assert record.scope == "ir.mapping"
    assert record.status == "accepted"
    assert record.source_refs == ("map-a.json",)
    dialog.deleteLater()


def test_scientific_review_dialog_rejects_incomplete_accepted_record() -> None:
    from polynexus.gui.scientific_review_dialog import ScientificReviewDialog

    QApplication.instance() or QApplication([])
    dialog = ScientificReviewDialog("nmr.solid_c", source_refs=("nmr-run",))
    dialog.set_field("record_id", "review-dialog-invalid")
    dialog.set_field("reviewer", "reviewer-a")
    dialog.set_field("reviewed_at", "2026-07-30")
    dialog.set_field("policy_version", "nmr-v1")
    dialog.set_status("accepted")

    with pytest.raises(ValueError, match="missing required decisions"):
        dialog.build_record()
    dialog.deleteLater()


def test_workbench_review_application_updates_only_generic_result_provenance() -> None:
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "nmr"
    window._results = {
        "nmr": AnalysisResult(
            technique="nmr",
            metadata={"source_id": "nmr-run"},
            analysis_evidence={"existing": "keep"},
        )
    }
    record_payload = {"record_id": "review-1", "scope": "nmr.solid_c", "status": "pending"}
    snapshot = {
        "allowed": False,
        "reason": "review_pending",
        "record_id": "review-1",
        "scope": "nmr.solid_c",
    }

    window._apply_scientific_review_to_current_result(record_payload, snapshot)

    result = window._results["nmr"]
    assert result.metadata["scientific_review"] == record_payload
    assert result.metadata["scientific_review_decision"] == snapshot
    assert result.analysis_evidence["existing"] == "keep"
    assert result.analysis_evidence["scientific_review"] == snapshot
    assert result.analysis_evidence["scientific_review_record"] == record_payload


def test_workbench_source_refs_include_nested_mapping_evidence_source_id() -> None:
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "ir"
    window._current_submodule_id = "ir.mapping"
    window._current_filepath = ""
    window._results = {
        "ir": AnalysisResult(
            technique="ir",
            metadata={},
            analysis_evidence={
                "feature_evidence": {
                    "mapping_evidence": {
                        "source_id": "native-synthetic-map.json",
                    }
                }
            },
        )
    }

    assert window._current_scientific_review_source_refs() == (
        "native-synthetic-map.json",
    )
