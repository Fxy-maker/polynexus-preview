from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.work_memory_service import (
    collect_work_memory_db_snapshot,
    build_work_memory_payload,
    compose_current_work_memory_detail,
    compose_joint_work_memory_detail,
    compose_recent_history_work_memory_detail,
    compose_sample_work_memory_detail,
    compose_work_memory_meta_detail,
    work_memory_summary_text,
    workspace_context_summary_text,
)


class _FakeDb:
    def __init__(self, *, samples, batches_by_sample, runs_by_batch, raises=False):
        self._samples = list(samples)
        self._batches_by_sample = dict(batches_by_sample)
        self._runs_by_batch = dict(runs_by_batch)
        self._raises = raises

    def list_samples(self, limit=1000):
        if self._raises:
            raise RuntimeError("db offline")
        return self._samples[:limit]

    def get_batches(self, sample_id):
        return list(self._batches_by_sample.get(sample_id, []))

    def get_analysis_runs(self, batch_id):
        return list(self._runs_by_batch.get(batch_id, []))


class _CompactSnapshotDb:
    def __init__(self):
        self.full_run_calls = []

    def get_work_memory_snapshot(self):
        return {
            "sample_count": 1,
            "batch_count": 1,
            "recent_run": {
                "id": "run-1",
                "technique": "saxs",
                "created_at": "2026-07-08 10:00:00",
                "output_dir": r"D:\\runs\\output_b",
            },
            "recent_sample": {
                "id": "sample-1",
                "polymer_name": "PA6",
                "family": "polyamide",
                "aliases": ["nylon-6", "PA-6"],
            },
            "recent_batch": {"id": "batch-1", "label": "batch-01"},
        }

    def get_analysis_runs(self, batch_id):
        raise AssertionError("compact snapshot must not hydrate batch histories")

    def get_analysis_run(self, run_id):
        self.full_run_calls.append(run_id)
        return {
            "id": run_id,
            "technique": "saxs",
            "created_at": "2026-07-08 10:00:00",
            "output_dir": r"D:\\runs\\output_b",
            "parameters": {"L_nm": 11.2},
            "results_summary": {"Xc_pct": 0.31},
        }


class _FakeWindow:
    def __init__(self, db):
        self._db = db
        self._results = {
            "saxs": {
                "parameters": {"L_nm": 11.2},
                "results_summary": {"ai_tuned": True, "result_origin": "controlled_optimization_rerun"},
            }
        }
        self._current_technique = "saxs"
        self._current_submodule_id = "saxs.static"
        self._last_ai_tuning_context = {
            "benchmark_text": "Benchmark: objective delta +0.018",
            "history": [{"round_num": 1, "accepted": True, "r_squared_after": 0.91}],
        }
        self._joint_report = {"summary": "Cross-tech consistency for PA6"}
        self._last_export_bundle = r"D:\runs\export_pkg"
        self._output_dir = ""
        self._current_result_confirmed_flag = True
        self._results_summary_label = type("_Label", (), {"text": lambda self: "Measured result | PA6"})()

    def _ensure_sample_db(self):
        return self._db

    def _current_result_label_for_confirmation(self):
        return "PA6"

    def _current_result_origin_label(self):
        return "Recommended-parameter rerun"

    def _results_confirm_state_text(self):
        return "Confirmed"

    def _current_result_origin(self):
        return "controlled_optimization_rerun"

    def _current_result_history_context(self, current):
        return {"benchmark_summary": {"average_objective_delta": 0.018}}

    def _benchmark_summary_text(self, benchmark_summary):
        return "Benchmark summary"

    def _history_metrics_tooltip(self, record, *, limit=4):
        return "L_nm=11.2"

    def _result_review_summary(self):
        return "Cross-tech consistency for PA6 | quality guard reached"

    def _ai_tuning_chain_summary(self, report=None):
        return "Run trace | accepted 1 rounds | baseline delta +0.018"

    def _load_recent_calibration(self):
        return {"scope": "saxs.static"}

    def _current_calibration_scope_label(self):
        return "saxs.static"

    def _on_apply_recent_calibration(self):
        raise AssertionError("should not be called in payload test")

    def _on_save_recent_calibration(self):
        raise AssertionError("should not be called in payload test")

    def _history_technique_text(self, technique):
        return "SAXS"

    def _history_record_context_text(self, record):
        return "PA6 | SAXS"

    def _history_result_origin_label(self, record):
        return "Recommended-parameter rerun"

    def _history_confirmation_label(self, record):
        return "Confirmed"

    def _joint_ai_context(self):
        return {"summary": "Cross-tech consistency for PA6"}

    def _joint_ai_reminder_text(self, joint_context=None):
        return "Review phi_c inconsistency"

    def _joint_compare_hint_text(self, joint_context=None):
        return "Compare SAXS and WAXS first"

    def _jump_to_results(self):
        raise AssertionError("not used")

    def _jump_to_history(self):
        raise AssertionError("not used")

    def _jump_to_sample_library(self):
        raise AssertionError("not used")

    def _jump_to_joint_hub(self):
        raise AssertionError("not used")

    def _open_last_export_bundle(self):
        raise AssertionError("not used")


def test_collect_work_memory_db_snapshot_counts_samples_and_keeps_first_recent_entries():
    snapshot = collect_work_memory_db_snapshot(
        _FakeDb(
            samples=[
                {"id": "sample-1", "polymer_name": "PA6"},
                {"id": "sample-2", "polymer_name": "PET"},
            ],
            batches_by_sample={
                "sample-1": [{"id": "batch-1", "label": "B1"}, {"id": "batch-2", "label": "B2"}],
                "sample-2": [{"id": "batch-3", "label": "B3"}],
            },
            runs_by_batch={
                "batch-1": [{"id": "run-1"}],
                "batch-2": [{"id": "run-2"}],
                "batch-3": [{"id": "run-3"}],
            },
        )
    )

    assert snapshot.sample_count == 2
    assert snapshot.batch_count == 3
    assert snapshot.recent_sample == {"id": "sample-1", "polymer_name": "PA6"}
    assert snapshot.recent_batch == {"id": "batch-1", "label": "B1"}
    assert snapshot.recent_run == {"id": "run-1"}


def test_collect_work_memory_db_snapshot_returns_empty_on_sample_error():
    snapshot = collect_work_memory_db_snapshot(
        _FakeDb(samples=[{"id": "sample-1"}], batches_by_sample={}, runs_by_batch={}, raises=True)
    )

    assert snapshot.sample_count == 0
    assert snapshot.batch_count == 0
    assert snapshot.recent_sample is None
    assert snapshot.recent_batch is None
    assert snapshot.recent_run is None


def test_collect_work_memory_db_snapshot_prefers_compact_header_snapshot():
    db = _CompactSnapshotDb()

    snapshot = collect_work_memory_db_snapshot(db)

    assert snapshot.sample_count == 1
    assert snapshot.batch_count == 1
    assert snapshot.recent_run == {
        "id": "run-1",
        "technique": "saxs",
        "created_at": "2026-07-08 10:00:00",
        "output_dir": r"D:\\runs\\output_b",
    }
    assert db.full_run_calls == []


def test_build_work_memory_payload_hydrates_only_the_selected_compact_run_for_metrics():
    previous = get_language()
    set_language("en")
    try:
        db = _CompactSnapshotDb()

        build_work_memory_payload(_FakeWindow(db))

        assert db.full_run_calls == ["run-1"]
    finally:
        set_language(previous)


def test_compose_current_work_memory_detail_appends_review_summary_once():
    detail = compose_current_work_memory_detail(
        summary_text="Measured result | PA6",
        context_text="PA6",
        origin_text="Recommended-parameter rerun",
        confirmed_text="Confirmed",
        benchmark_text="Benchmark: objective delta +0.018",
        chain_text="Run trace | accepted 2 rounds",
        review_summary="Cross-tech consistency for PA6 | quality guard reached",
    )

    assert detail == " | ".join(
        [
            "Measured result | PA6",
            "PA6",
            "Recommended-parameter rerun",
            "Confirmed",
            "Benchmark: objective delta +0.018",
            "Run trace | accepted 2 rounds",
            "Cross-tech consistency for PA6 | quality guard reached",
        ]
    )

    deduped = compose_current_work_memory_detail(
        summary_text=detail,
        review_summary="quality guard reached",
    )
    assert deduped == detail


def test_compose_recent_history_work_memory_detail_appends_output_dir_leaf():
    detail = compose_recent_history_work_memory_detail(
        context_text="PA6 | SAXS",
        created_text="2026-07-08 10:00",
        origin_text="Recommended-parameter rerun",
        confirmed_text="Confirmed",
        summary_text="L_nm=11.2 | Xc_pct=0.31",
        output_dir=r"D:\runs\output_b",
    )

    assert detail == " | ".join(
        [
            "PA6 | SAXS",
            "2026-07-08 10:00",
            "Recommended-parameter rerun",
            "Confirmed",
            "L_nm=11.2 | Xc_pct=0.31",
            "output_b",
        ]
    )


def test_compose_sample_work_memory_detail_uses_family_aliases_and_batch_label():
    detail = compose_sample_work_memory_detail(
        {"polymer_name": "PA6", "family": "polyamide", "aliases": ["nylon-6", "PA-6", "extra"]},
        {"label": "batch-01"},
    )

    assert detail == "PA6 | polyamide | nylon-6, PA-6 | batch-01"


def test_compose_joint_work_memory_detail_prefers_summary_then_context_bits():
    previous = get_language()
    set_language("en")
    try:
        detail = compose_joint_work_memory_detail(
            summary_text="Cross-tech consistency for PA6",
            reminder_text="Review phi_c inconsistency",
            compare_hint_text="Compare SAXS and WAXS first",
        )
        assert detail == "Cross-tech consistency for PA6 | Review phi_c inconsistency | Compare SAXS and WAXS first"

        ready_only = compose_joint_work_memory_detail(summary_text="", reminder_text="", compare_hint_text="")
        assert ready_only == tr("WORK_MEMORY_JOINT_READY")
    finally:
        set_language(previous)


def test_compose_work_memory_meta_detail_uses_default_when_counts_are_empty():
    previous = get_language()
    set_language("en")
    try:
        assert compose_work_memory_meta_detail(sample_count=2, batch_count=3) == "2 samples  |  3 batches"
        assert compose_work_memory_meta_detail(sample_count=0, batch_count=0) == tr("WORK_MEMORY_DEFAULT_DETAIL")
    finally:
        set_language(previous)


def test_build_work_memory_payload_includes_current_recent_and_joint_slices():
    previous = get_language()
    set_language("en")
    try:
        db = _FakeDb(
            samples=[{"id": "sample-1", "polymer_name": "PA6", "family": "polyamide", "aliases": ["nylon-6", "PA-6"]}],
            batches_by_sample={"sample-1": [{"id": "batch-1", "label": "batch-01"}]},
            runs_by_batch={"batch-1": [{"id": "run-1", "technique": "saxs", "created_at": "2026-07-08 10:00:00", "output_dir": r"D:\\runs\\output_b"}]},
        )
        window = _FakeWindow(db)

        payload = build_work_memory_payload(window)

        assert payload["title"] == tr("WORK_MEMORY_TITLE")
        assert payload["detail"] == "1 samples  |  1 batches"
        labels = [item["label"] for item in payload["slices"]]
        assert labels == [
            tr("WORK_MEMORY_CURRENT"),
            tr("WORK_MEMORY_CALIBRATION"),
            tr("WORK_MEMORY_HISTORY"),
            tr("WORK_MEMORY_SAMPLE"),
            tr("WORK_MEMORY_JOINT"),
            tr("WORK_MEMORY_EXPORT"),
        ]
        current_slice = payload["slices"][0]
        assert "Confirmed" in current_slice["detail"]
        assert "Benchmark: objective delta +0.018" in current_slice["detail"]
        assert "Cross-tech consistency for PA6" in current_slice["detail"]
        assert "quality guard reached" in current_slice["detail"]
        assert payload["slices"][2]["detail"].endswith("output_b")
        assert payload["slices"][3]["detail"] == "PA6 | polyamide | nylon-6, PA-6 | batch-01"
        assert payload["slices"][4]["detail"] == "Cross-tech consistency for PA6 | Review phi_c inconsistency | Compare SAXS and WAXS first"
        assert payload["slices"][5]["detail"] == "export_pkg"
    finally:
        set_language(previous)


def test_work_memory_summary_text_uses_first_slices_and_deduplicates_extra_lines():
    assert work_memory_summary_text(
        [
            {"label": "Current", "detail": "Measured"},
            {"label": "History", "detail": "Recent"},
            {"label": "Joint", "detail": "Cross-tech"},
            {"label": "Ignored", "detail": "Later"},
        ],
        extra_lines=["Recent", "Extra"],
    ) == "Current: Measured | History: Recent | Joint: Cross-tech | Recent | Extra"


def test_workspace_context_summary_text_combines_current_joint_and_work_memory_lines():
    text = workspace_context_summary_text(
        {
            "results_summary": {"project_label": "PA6"},
            "confirmed": True,
            "ai_tuned": False,
        },
        confirm_state_text="Confirmed",
        origin_label="Recommended rerun",
        current_note="Measured result | PA6",
        joint_report={"summary": "Joint summary", "rows": [1], "validations": [1, 2]},
        joint_context={"summary": "Fallback joint"},
        joint_label="Joint",
        joint_count_text_fn=lambda rows, validations: f"{rows} rows, {validations} validations",
        work_memory={
            "slices": [
                {"label": "Current", "detail": "Measured"},
                {"label": "History", "detail": "Recent"},
                {"label": "Export", "detail": "bundle"},
            ]
        },
        empty_text="N/A",
        current_label="Current result",
    )

    assert text == "\n".join(
        [
            "Current result: PA6 | Confirmed | confirmed=True | ai_tuned=False | Recommended rerun | Measured result | PA6",
            "Joint: Joint summary",
            "1 rows, 2 validations",
            "Current: Measured",
            "History: Recent",
        ]
    )
