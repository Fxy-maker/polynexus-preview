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


def _accepted_release_record(record_id: str) -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id=record_id,
        scope="release",
        reviewer="reviewer-release",
        reviewed_at="2026-07-30",
        policy_version="release-v1",
        source_refs=("ir-run", "nmr-run", "joint-run"),
        decisions={
            "release_decision": "approve",
            "conditions_or_followups": "none",
        },
        status="accepted",
    )


def _accepted_saxs_2d_record() -> ScientificReviewRecord:
    return ScientificReviewRecord(
        record_id="review-saxs-2d-workbench",
        scope="saxs.2d",
        reviewer="reviewer-saxs",
        reviewed_at="2026-07-31",
        policy_version="saxs-2d-v1",
        source_refs=("pad8-run",),
        decisions={
            "geometry_reference": "reviewed calibration record",
            "beam_center_policy": "reviewed detector coordinates",
            "mask_policy": "reviewed beamstop mask",
            "saturation_policy": "saturation status retained",
            "orientation_applicability": "orientation evidence applicable",
            "promotion_rule": "existing gates and source-matched review",
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


def test_saxs_workbench_review_routes_to_existing_figure_sync() -> None:
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    calls: list[dict] = []

    class _Engine:
        def sync_scientific_review_to_figures(self, payload):
            calls.append(payload)
            return {"status": "ok", "updated_count": 1}

    result = AnalysisResult(technique="saxs")
    owner = type(
        "ReviewOwner",
        (),
        {
            "_current_technique": "saxs",
            "_results": {"saxs": result},
            "_engine_cache": {"saxs": _Engine()},
        },
    )()
    record_payload = {"record_id": "review-route", "scope": "saxs.1d"}
    snapshot = {"allowed": True, "reason": "review_accepted"}

    MainWindowResultsMixin._apply_scientific_review_to_current_result(
        owner,
        record_payload,
        snapshot,
    )

    assert calls == [record_payload]
    assert result.metadata["scientific_review"] == record_payload


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


def test_scientific_review_dialog_builds_a_release_decision_record() -> None:
    from polynexus.gui.scientific_review_dialog import ScientificReviewDialog

    QApplication.instance() or QApplication([])
    dialog = ScientificReviewDialog("release", source_refs=("ir-run", "joint-run"))
    dialog.set_field("record_id", "release-dialog-1")
    dialog.set_field("reviewer", "reviewer-release")
    dialog.set_field("reviewed_at", "2026-07-30")
    dialog.set_field("policy_version", "release-v1")
    dialog.set_status("conditional")
    dialog.set_decision_value("release_decision", "conditional")
    dialog.set_decision_value("conditions_or_followups", "Keep Joint conclusion diagnostic until conflict review.")

    record = dialog.build_record()

    assert record.scope == "release"
    assert record.status == "conditional"
    assert record.decisions["release_decision"] == "conditional"
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


def test_saxs_workbench_scope_choice_persists_selected_2d_snapshot(monkeypatch) -> None:
    from PySide6.QtWidgets import QDialog

    from polynexus.gui import main_window_results_mixin as results_mixin
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    record = _accepted_saxs_2d_record()

    class FakeDialog:
        def __init__(self, scope, *, source_refs, parent=None):
            del parent
            self.scope = scope
            self.source_refs = tuple(source_refs)

        def exec(self):
            return QDialog.Accepted

        def build_record(self):
            assert self.scope == "saxs.2d"
            return record

    class FakeDB:
        snapshot = None

        def update_analysis_scientific_review(self, _run_id, _record, snapshot):
            self.snapshot = snapshot
            return True

    db = FakeDB()
    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._last_persisted_run_id = "run-1"
    window._current_filepath = "pad8-run"
    window._results = {
        "saxs": AnalysisResult(
            technique="saxs",
            metadata={"source_id": "pad8-run"},
        )
    }
    window._ensure_sample_db = lambda: db
    window._apply_scientific_review_to_current_result = lambda *_args: None
    window._refresh_history = lambda: None
    window._update_results_review_panel = lambda: None
    window._update_work_memory_panel = lambda: None
    window.log = lambda _message: None
    monkeypatch.setattr(results_mixin, "ScientificReviewDialog", FakeDialog)
    monkeypatch.setattr(
        results_mixin.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: ("saxs.2d", True)),
    )

    window._open_scientific_review_dialog()

    assert db.snapshot["scope"] == "saxs.2d"
    assert db.snapshot["reason"] == "review_accepted"


def test_saxs_workbench_scope_choice_cancel_does_not_write(monkeypatch) -> None:
    from polynexus.gui import main_window_results_mixin as results_mixin
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "saxs"
    window._current_submodule_id = "saxs.static"
    window._last_persisted_run_id = "run-1"
    window._current_filepath = "pad8-run"
    window._results = {
        "saxs": AnalysisResult(
            technique="saxs",
            metadata={"source_id": "pad8-run"},
        )
    }
    window._ensure_sample_db = lambda: pytest.fail("cancelled scope must not write")
    window.log = lambda _message: None
    monkeypatch.setattr(
        results_mixin.QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: ("", False)),
    )

    window._open_scientific_review_dialog()


def test_workbench_review_snapshot_uses_canonical_source_with_multiple_refs(monkeypatch) -> None:
    from PySide6.QtWidgets import QDialog

    from polynexus.gui import main_window_results_mixin as results_mixin
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    base = _accepted_ir_record()
    record = ScientificReviewRecord(
        record_id="review-multi-source",
        scope=base.scope,
        reviewer=base.reviewer,
        reviewed_at=base.reviewed_at,
        policy_version=base.policy_version,
        source_refs=("native-synthetic-map.json", r"D:\PolyNexus\README.md"),
        decisions=dict(base.decisions),
        status=base.status,
    )

    class FakeDialog:
        def __init__(self, _scope, *, source_refs, parent=None):
            del parent
            self.source_refs = tuple(source_refs)

        def exec(self):
            return QDialog.Accepted

        def build_record(self):
            return record

    class FakeDB:
        snapshot = None

        def update_analysis_scientific_review(self, _run_id, _record, snapshot):
            self.snapshot = snapshot
            return True

    db = FakeDB()
    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "ir"
    window._current_submodule_id = "ir.mapping"
    window._last_persisted_run_id = "run-1"
    window._current_filepath = r"D:\PolyNexus\README.md"
    window._results = {
        "ir": AnalysisResult(
            technique="ir",
            metadata={"source_id": "native-synthetic-map.json"},
        )
    }
    window._ensure_sample_db = lambda: db
    window._apply_scientific_review_to_current_result = lambda *_args: None
    window._refresh_history = lambda: None
    window._update_results_review_panel = lambda: None
    window._update_work_memory_panel = lambda: None
    window.log = lambda _message: None
    monkeypatch.setattr(results_mixin, "ScientificReviewDialog", FakeDialog)

    window._open_scientific_review_dialog()

    assert db.snapshot["source_ref"] == "native-synthetic-map.json"


def test_release_storage_is_append_only_and_hydrates_latest_for_run(tmp_path) -> None:
    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "release")
    run_id = db.create_analysis_run(
        batch_id,
        "joint",
        submodule="joint.compare",
        results_summary={"result": {"metadata": {"source_id": "joint-run"}}},
    )

    first = _accepted_release_record("release-1")
    first_snapshot = review_decision_snapshot(first, expected_scope="release", source_ref="ir-run")
    second = _accepted_release_record("release-2")
    second_snapshot = review_decision_snapshot(second, expected_scope="release", source_ref="ir-run")

    assert db.save_scientific_release_review(batch_id, first.to_dict(), first_snapshot) is True
    assert db.save_scientific_release_review(batch_id, second.to_dict(), second_snapshot) is True

    records = db.list_scientific_release_reviews(batch_id)
    assert [item["record"]["record_id"] for item in records] == ["release-1", "release-2"]
    latest = db.get_latest_scientific_release_review_for_run(run_id)
    assert latest["record"]["record_id"] == "release-2"
    assert latest["snapshot"] == second_snapshot
    db.close()


def test_release_storage_rejects_unknown_batch_without_write(tmp_path) -> None:
    db = SampleDB(tmp_path / "samples.db")
    record = _accepted_release_record("release-missing-batch")
    snapshot = review_decision_snapshot(record, expected_scope="release", source_ref="ir-run")

    assert db.save_scientific_release_review("missing-batch", record.to_dict(), snapshot) is False
    assert db.list_scientific_release_reviews("missing-batch") == []
    db.close()


def test_release_workbench_saves_batch_record_without_run_review_update(monkeypatch) -> None:
    from PySide6.QtWidgets import QDialog

    from polynexus.gui import main_window_results_mixin as results_mixin
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    record = _accepted_release_record("release-workbench-1")

    class FakeDialog:
        def __init__(self, scope, *, source_refs, parent=None):
            del parent
            assert scope == "release"
            self.source_refs = tuple(source_refs)

        def exec(self):
            return QDialog.Accepted

        def build_record(self):
            return record

    class FakeDB:
        saved = None

        def save_scientific_release_review(self, batch_id, payload, snapshot):
            self.saved = (batch_id, payload, snapshot)
            return True

    db = FakeDB()
    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "joint"
    window._current_submodule_id = "joint.compare"
    window._current_batch_id = "batch-1"
    window._last_persisted_run_id = "run-1"
    window._current_filepath = "joint-run"
    window._results = {
        "joint": AnalysisResult(
            technique="joint",
            metadata={"source_id": "joint-run"},
        )
    }
    window._ensure_sample_db = lambda: db
    window._apply_scientific_release_to_current_result = lambda *_args: None
    window._refresh_history = lambda: None
    window._update_results_review_panel = lambda: None
    window._update_work_memory_panel = lambda: None
    window.log = lambda _message: None
    monkeypatch.setattr(results_mixin, "ScientificReviewDialog", FakeDialog)

    window._open_scientific_release_dialog()

    assert db.saved[0] == "batch-1"
    assert db.saved[1]["scope"] == "release"
    assert db.saved[2]["source_ref"] == "ir-run"


def test_release_provenance_is_applied_without_changing_analysis_values() -> None:
    from polynexus.gui.main_window_results_mixin import MainWindowResultsMixin

    window = object.__new__(MainWindowResultsMixin)
    window._current_technique = "joint"
    window._results = {
        "joint": AnalysisResult(
            technique="joint",
            metadata={"existing": "keep"},
            analysis_evidence={"existing": "evidence"},
            parameters={"metric": 1.0},
        )
    }
    record_payload = {"record_id": "release-1", "scope": "release", "status": "accepted"}
    snapshot = {
        "allowed": True,
        "reason": "review_accepted",
        "record_id": "release-1",
        "scope": "release",
        "source_ref": "joint-run",
    }

    window._apply_scientific_release_to_current_result(record_payload, snapshot)

    result = window._results["joint"]
    assert result.parameters == {"metric": 1.0}
    assert result.metadata["scientific_release"] == record_payload
    assert result.metadata["scientific_release_decision"] == snapshot
    assert result.analysis_evidence["existing"] == "evidence"
    assert result.analysis_evidence["scientific_release"] == snapshot


def test_release_display_is_visible_to_history_consumers() -> None:
    from polynexus.gui.scientific_review_presentation import scientific_release_display

    display = scientific_release_display(
        {
            "scientific_release": {
                "allowed": True,
                "reason": "review_accepted",
                "record_id": "release-1",
                "scope": "release",
                "source_ref": "joint-run",
                "policy_version": "release-v1",
            }
        },
        language="en",
    )

    assert display.status == "accepted"
    assert display.allowed is True
    assert display.record_id == "release-1"
    assert "release-1" in display.text


def test_release_display_is_fail_closed_when_record_is_missing() -> None:
    from polynexus.gui.scientific_review_presentation import scientific_release_display

    display = scientific_release_display({}, language="en")

    assert display.allowed is False
    assert display.status == "required"
    assert display.reason == "release_missing"
