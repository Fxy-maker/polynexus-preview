from types import SimpleNamespace

import importlib

from polynexus.gui.analysis_history_service import (
    ai_tuning_benchmark_delta_text,
    ai_tuning_benchmark_rate_text,
    ai_tuning_chain_summary,
    ai_tuning_chain_stats,
    ai_tuning_previous_round_summary_text,
    ai_tuning_report_context,
    ai_tuning_tunable_summary_text,
    batch_fallback_summary_parts,
    collect_history_rows,
    context_suggestion_spec,
    controlled_optimization_review_parts,
    saxs_lc_status_summary_parts,
    saxs_lc_status_text,
    saxs_reason_text,
    saxs_structure_status_snapshot,
    saxs_strain_evidence_snapshot,
    saxs_strain_next_step_text,
    saxs_strain_risk_summary_text,
    saxs_strain_summary_text,
    current_result_origin,
    ai_tuning_change_summary_text,
    ai_tuning_remaining_risks_text,
    ai_tuning_stability_summary_parts,
    ai_tuning_constraint_summary_parts,
    has_condition_axis_risk,
    has_fallback_conflict_risk,
    current_result_history_context,
    current_result_tuning_context,
    current_results_payload,
    current_results_record,
    flatten_params,
    format_history_timestamp,
    format_r2_value,
    gui_display_text,
    gui_display_text_value,
    gui_format_score_value,
    gui_coerce_summary_float,
    history_compare_counts,
    history_compare_record,
    history_compare_rows,
    history_compare_state_key,
    history_compare_state_translation_key,
    history_context_snapshot,
    build_history_context_snapshot_from_window,
    history_context_line_parts,
    history_export_rows,
    history_filter_items,
    history_action_state,
    history_compare_tooltip_key,
    history_has_available_source,
    history_metrics_summary,
    history_confirmation_translation_key,
    history_record_confirmed,
    history_record_analysis_evidence,
    history_restore_tooltip_key,
    history_rerun_tooltip_key,
    history_copy_summary_tooltip_key,
    history_result_origin,
    history_result_metrics,
    history_run_r2,
    history_status_label_parts,
    history_status_text_parts,
    history_record_context_ref,
    history_summary_lines,
    history_tooltip_translation_key,
    history_validation_summary_text,
    current_result_confirmation_label,
    joint_ai_context,
    joint_ai_reminder_parts,
    joint_compare_hint_parts,
    measured_result_metric_parts,
    result_comparison_summary,
    result_comparison_record_label,
    result_compare_candidate_id,
    result_compare_candidate_label,
    result_comparison_baseline,
    result_comparison_candidates,
    quality_flag_summary_text,
    result_origin_translation_key,
    results_has_critical_risk,
    results_next_step_translation_key,
    result_mask_summary_text,
    ordered_results_columns,
    result_review_metric_summary,
    result_source_summary_text,
    result_to_jsonable,
    validation_summary_parts,
    workflow_task_context_spec,
    workflow_task_tech_label,
    workspace_context_summary_text,
    work_memory_summary_text,
)
from polynexus.gui.analysis_history_risk_helpers import (
    gui_coerce_summary_float as helper_gui_coerce_summary_float,
    gui_display_text as helper_gui_display_text,
    gui_display_text_value as helper_gui_display_text_value,
    gui_format_score_value as helper_gui_format_score_value,
    has_condition_axis_risk as helper_has_condition_axis_risk,
    has_fallback_conflict_risk as helper_has_fallback_conflict_risk,
    measured_result_metric_parts as helper_measured_result_metric_parts,
    ordered_results_columns as helper_ordered_results_columns,
    result_mask_summary_text as helper_result_mask_summary_text,
    results_has_critical_risk as helper_results_has_critical_risk,
    results_next_step_translation_key as helper_results_next_step_translation_key,
)
from polynexus.gui.i18n import tr


class FakeDB:
    def __init__(self):
        self.samples = [{"id": "sample-a"}, {"id": ""}, {"id": "sample-b"}]
        self.batches = {
            "sample-a": [{"id": "batch-a"}, {"id": ""}],
            "sample-b": [{"id": "batch-b"}],
        }
        self.runs = {
            "batch-a": [
                {"id": "old", "technique": "custom", "created_at": "2026-01-01T00:00:00"},
                {"id": "new", "technique": "saxs", "created_at": "2026-02-01T00:00:00"},
            ],
            "batch-b": [
                {"id": "middle", "technique": "waxs", "created_at": "2026-01-15T00:00:00"},
                {"id": "missing-time", "technique": "ir"},
            ],
        }

    def list_samples(self, limit=50):
        assert limit == 10000
        return list(self.samples)

    def get_batches(self, sample_id):
        return list(self.batches.get(sample_id, []))

    def get_analysis_runs(self, batch_id):
        return list(self.runs.get(batch_id, []))


class FakeCompareDB:
    def __init__(self):
        self.samples = [
            {"id": "sample-a", "polymer_name": "PA6"},
            {"id": "sample-b", "polymer_name": "PET"},
        ]
        self.batches = {
            "sample-a": [{"id": "batch-a"}],
            "sample-b": [{"id": "batch-b"}],
        }
        self.runs = {
            "batch-a": [
                {"id": "same-old", "technique": "saxs", "submodule": "saxs.static", "created_at": "2026-07-01 10:00:00"},
                {"id": "same-new", "technique": "saxs", "submodule": "saxs.static", "created_at": "2026-07-03 10:00:00"},
                {"id": "same-empty-sub", "technique": "saxs", "submodule": "", "created_at": "2026-07-04 10:00:00"},
                {"id": "wrong-sub", "technique": "saxs", "submodule": "saxs.temperature", "created_at": "2026-07-05 10:00:00"},
                {"id": "wrong-tech", "technique": "waxs", "submodule": "waxs.static", "created_at": "2026-07-06 10:00:00"},
            ],
            "batch-b": [
                {"id": "fallback-new", "technique": "saxs", "submodule": "saxs.static", "created_at": "2026-07-07 10:00:00"},
            ],
        }

    def list_samples(self, limit=50):
        assert limit == 100
        return list(self.samples)

    def get_batches(self, sample_id):
        return list(self.batches.get(sample_id, []))

    def get_analysis_runs(self, batch_id):
        return list(self.runs.get(batch_id, []))


class HeaderOnlyComparisonDB:
    def __init__(self):
        self.header_calls = 0
        self.full_run_calls = 0

    def list_analysis_run_headers(self, *, limit=500):
        self.header_calls += 1
        assert limit == 500
        return [
            {"id": "same-old", "technique": "saxs", "submodule": "saxs.static", "created_at": "2026-07-01 10:00:00"},
            {"id": "same-new", "technique": "saxs", "submodule": "saxs.static", "created_at": "2026-07-03 10:00:00"},
            {"id": "same-empty-sub", "technique": "saxs", "submodule": "", "created_at": "2026-07-04 10:00:00"},
            {"id": "wrong-sub", "technique": "saxs", "submodule": "saxs.temperature", "created_at": "2026-07-05 10:00:00"},
            {"id": "wrong-tech", "technique": "waxs", "submodule": "waxs.static", "created_at": "2026-07-06 10:00:00"},
            {"id": "fallback-new", "technique": "saxs", "submodule": "saxs.static", "created_at": "2026-07-07 10:00:00"},
        ]

    def list_samples(self, limit=50):
        raise AssertionError("header query should avoid sample traversal")

    def get_analysis_runs(self, batch_id):
        self.full_run_calls += 1
        raise AssertionError("header query should avoid full run reads")


class UnavailableHeaderComparisonDB:
    def __init__(self):
        self.full_run_calls = 0

    def list_analysis_run_headers(self, *, limit=500):
        assert limit == 500
        return None

    def list_samples(self, limit=50):
        return [{"id": "sample-a", "polymer_name": "PA6"}]

    def get_batches(self, sample_id):
        return [{"id": "batch-a"}]

    def get_analysis_runs(self, batch_id):
        self.full_run_calls += 1
        raise AssertionError("an available header API must not fall back to full run reads")


class FakeParamRule:
    def __init__(self, constraint):
        self.constraint = constraint


class HeaderOnlyHistoryDB:
    def __init__(self):
        self.header_calls = 0

    def list_analysis_run_headers(self):
        self.header_calls += 1
        return [{"id": "run-1", "technique": "saxs"}]

    def list_samples(self, limit=50):
        raise AssertionError("header query should avoid sample traversal")


def test_collect_history_rows_flattens_and_sorts_runs_newest_first():
    rows = collect_history_rows(FakeDB())

    assert [row["id"] for row in rows] == ["new", "middle", "old", "missing-time"]


def test_collect_history_rows_prefers_header_query_when_available():
    db = HeaderOnlyHistoryDB()

    assert collect_history_rows(db) == [{"id": "run-1", "technique": "saxs"}]
    assert db.header_calls == 1


def test_history_filter_items_keeps_base_order_and_appends_custom_techniques():
    rows = [
        {"technique": "custom"},
        {"technique": "saxs"},
        {"technique": "another"},
        {"technique": ""},
    ]

    assert history_filter_items(rows) == [
        "saxs",
        "waxs",
        "dsc",
        "ir",
        "nmr",
        "another",
        "custom",
    ]


def test_format_r2_value_rounds_numbers_and_marks_invalid_values():
    assert format_r2_value(0.987654) == "0.9877"
    assert format_r2_value("0.1") == "0.1000"
    assert format_r2_value(None) == "nan"
    assert format_r2_value("bad") == "nan"


def test_format_history_timestamp_normalizes_known_database_formats():
    assert format_history_timestamp("2026-07-06T10:11:12.123456") == "2026-07-06 10:11"
    assert format_history_timestamp("2026-07-06 10:11:12") == "2026-07-06 10:11"
    assert format_history_timestamp("") == ""
    assert format_history_timestamp("not-a-date") == "not-a-date"


def test_history_run_r2_reads_summary_and_nested_parameters():
    assert history_run_r2({"results_summary": {"r2": "0.91"}}) == 0.91
    assert history_run_r2({"results_summary": {"parameters": {"R2": 0.82}}}) == 0.82

    value = history_run_r2({"results_summary": {"r2": "bad"}})

    assert value != value


def test_history_result_origin_prefers_explicit_origin_and_falls_back_to_ai_tuned():
    assert (
        history_result_origin(
            {"results_summary": {"result_origin": "controlled_optimization_rerun", "ai_tuned": True}}
        )
        == "controlled_optimization_rerun"
    )
    assert history_result_origin({"results_summary": {"ai_tuned": True}}) == "controlled_optimization_rerun"
    assert history_result_origin({"results_summary": {"result_origin": "manual_run"}}) == "manual_run"
    assert history_result_origin({"results_summary": {}}) == ""
    assert history_result_origin(None) == ""


def test_current_result_origin_uses_summary_ai_flag_then_last_run_flag():
    assert current_result_origin(
        {"results_summary": {"result_origin": "manual_run", "ai_tuned": True}},
        last_ai_tuned_run=True,
    ) == "manual_run"
    assert current_result_origin(
        {"results_summary": {"ai_tuned": True}},
        last_ai_tuned_run=False,
    ) == "controlled_optimization_rerun"
    assert current_result_origin({}, last_ai_tuned_run=True) == "controlled_optimization_rerun"
    assert current_result_origin({}, last_ai_tuned_run=False) == "manual_run"


def test_current_result_history_context_reads_nonempty_summary_context_only():
    context = {"review_summary": "Review"}

    assert current_result_history_context({"results_summary": {"history_context": context}}) == context
    assert current_result_history_context({"results_summary": {"history_context": {}}}) == {}
    assert current_result_history_context({"results_summary": {}}) == {}
    assert current_result_history_context(None) == {}


def test_current_result_tuning_context_prefers_live_context():
    live_context = {"tuning_goal": "risk"}
    record = {
        "results_summary": {
            "history_context": {
                "tuning_context": {"tuning_goal": "history"},
            }
        }
    }

    assert current_result_tuning_context(record, live_tuning_context=live_context) is live_context


def test_current_result_tuning_context_restores_history_and_merges_joint_context():
    record = {
        "results_summary": {
            "history_context": {
                "tuning_context": {"tuning_goal": "risk"},
                "joint_ai_context": {"summary": "Joint"},
            }
        }
    }

    restored = current_result_tuning_context(record, live_tuning_context={})

    assert restored == {
        "tuning_goal": "risk",
        "joint_ai_context": {"summary": "Joint"},
    }
    assert restored is not record["results_summary"]["history_context"]["tuning_context"]
    assert current_result_tuning_context({"results_summary": {"history_context": {}}}) == {}


def test_current_results_payload_normalizes_dict_and_to_dict_results(tmp_path):
    class ResultObject:
        def to_dict(self):
            return {"parameters": {"path": tmp_path / "sample.csv"}}

    assert current_results_payload({"parameters": {"r2": 0.9}}) == {"parameters": {"r2": 0.9}}
    assert current_results_payload(ResultObject()) == {"parameters": {"path": str(tmp_path / "sample.csv")}}


def test_current_results_payload_uses_public_dict_or_fallback_attributes():
    class DictResult:
        def __init__(self):
            self.parameters = {"r2": 0.8}
            self.extra = "kept"

    class FallbackResult:
        __slots__ = (
            "parameters",
            "validation_summary",
            "validation_warnings",
            "validation_passed",
            "quality_flags",
            "results_summary",
            "analysis_evidence",
        )

        def __init__(self):
            self.parameters = {"r2": 0.7}
            self.validation_summary = "ok"
            self.validation_warnings = ["warn"]
            self.validation_passed = True
            self.quality_flags = {"warning": []}
            self.results_summary = {"project_label": "sample"}
            self.analysis_evidence = {"support": 1}

    assert current_results_payload(DictResult()) == {"parameters": {"r2": 0.8}, "extra": "kept"}
    assert current_results_payload(FallbackResult()) == {
        "parameters": {"r2": 0.7},
        "validation_summary": "ok",
        "validation_warnings": ["warn"],
        "validation_passed": True,
        "quality_flags": {"warning": []},
        "results_summary": {"project_label": "sample"},
        "analysis_evidence": {"support": 1},
    }
    assert current_results_payload(None) == {}


def test_current_results_record_builds_standard_current_record_from_payload():
    payload = {
        "parameters": {
            "validation_passed": False,
            "quality_flags": {"warning": ["param quality"]},
        },
        "validation_summary": "Payload warning",
        "validation_warnings": [" w1 ", "", "w2"],
        "history_context": {"review_summary": "Review"},
        "results_summary": {
            "project_label": "Untitled project",
            "validation_summary": "summary ignored",
        },
    }

    record = current_results_record(
        payload,
        technique="saxs",
        submodule="saxs.static",
        project_label="Untitled project",
        inferred_sample_name="sample-a",
        current_file="D:/data/a.csv",
        output_dir="D:/out",
        result_origin="controlled_optimization_rerun",
        confirmed=True,
        created_at="2026-07-06 10:11:12",
        is_default_project_label_fn=lambda label: label == "Untitled project",
    )

    assert record["id"] == "current"
    assert record["technique"] == "saxs"
    assert record["submodule"] == "saxs.static"
    assert record["created_at"] == "2026-07-06 10:11:12"
    assert record["parameters"] == payload["parameters"]
    assert record["output_dir"] == "D:/out"
    assert record["source_data"] == "D:/data/a.csv"
    assert record["confirmed"] is True
    assert record["validation_summary"] == "Payload warning"
    assert record["validation_warnings"] == ["w1", "w2"]
    assert record["validation_passed"] is False
    assert record["quality_flags"] == {"warning": ["param quality"]}

    summary = record["results_summary"]
    assert summary["project_label"] == "sample-a"
    assert summary["data_file"] == "D:/data/a.csv"
    assert summary["result_origin"] == "controlled_optimization_rerun"
    assert summary["ai_tuned"] is True
    assert summary["history_context"] == {"review_summary": "Review"}
    assert summary["result"]["validation_summary"] == "Payload warning"
    assert summary["result"]["validation_warnings"] == ["w1", "w2"]
    assert summary["result"]["validation_passed"] is False


def test_current_results_record_can_bind_to_persisted_run_id():
    record = current_results_record(
        {"parameters": {"r2": 0.91}},
        technique="ir",
        run_id="run-123",
    )

    assert record["id"] == "run-123"


def test_result_comparison_candidates_excludes_current_sentinel_in_fallback(
    tmp_path,
):
    from polynexus.data.sample_db import SampleDB
    from polynexus.gui.analysis_history_service import result_comparison_candidates

    db = SampleDB(tmp_path / "samples.db")
    sample_id = db.create_sample("PA6")
    batch_id = db.create_batch(sample_id, "run")
    db.create_analysis_run(batch_id, "ir", results_summary={"project_label": "PA6"})

    candidates = result_comparison_candidates(
        {"id": "current", "technique": "ir", "results_summary": {"project_label": "missing"}},
        db,
        inferred_sample_name="missing",
    )

    assert all(candidate.get("id") != "current" for candidate in candidates)
    db.close()


def test_current_results_record_returns_empty_for_invalid_payload():
    assert current_results_record({}, technique="saxs") == {}
    assert current_results_record(None, technique="saxs") == {}


def test_ai_tuning_benchmark_formatters_handle_numbers_and_invalid_values():
    assert ai_tuning_benchmark_delta_text(0.0184) == "+0.018"
    assert ai_tuning_benchmark_delta_text(-0.0021) == "-0.002"
    assert ai_tuning_benchmark_delta_text(0) == "0.000"
    assert ai_tuning_benchmark_delta_text("bad") == "N/A"

    assert ai_tuning_benchmark_rate_text(0.125) == "12.5%"
    assert ai_tuning_benchmark_rate_text("0.8") == "80.0%"
    assert ai_tuning_benchmark_rate_text(None) == "0.0%"


def test_ai_tuning_chain_stats_counts_rounds_best_latest_and_risks():
    stats = ai_tuning_chain_stats(
        {
            "benchmark_summary": {"average_objective_delta": 0.018},
            "history": [
                {"round_num": 1, "accepted": True, "r_squared_after": 0.91},
                {
                    "round_num": 2,
                    "accepted": False,
                    "r_squared_after": 0.89,
                    "llm_advice": {"rollback_reason": "quality guard reached"},
                },
                {
                    "round_num": 3,
                    "accepted": False,
                    "r_squared_after": 0.88,
                    "llm_advice": {"rollback_reason": "quality guard reached"},
                },
                {"round_idx": 4, "accepted": True, "r_squared": 0.94},
            ],
        },
        benchmark_delta_text_fn=lambda value: f"+{float(value):.3f}",
    )

    assert stats.baseline_hint == "+0.018"
    assert stats.accepted_rounds == 2
    assert stats.rolled_back_rounds == 2
    assert stats.best_round == 4
    assert stats.best_r2 == 0.94
    assert stats.last_accepted_round == 4
    assert stats.rollback_reasons == ["quality guard reached"]


def test_ai_tuning_chain_summary_counts_rounds_best_round_and_risks():
    context = {
        "benchmark_summary": {"average_objective_delta": 0.018},
        "history": [
            {"round_num": 1, "accepted": True, "r_squared_after": 0.91},
            {
                "round_num": 2,
                "accepted": False,
                "r_squared_after": 0.89,
                "llm_advice": {"rollback_reason": "quality guard reached"},
            },
            {"round_idx": 3, "accepted": True, "r_squared": 0.94},
        ],
    }

    summary = ai_tuning_chain_summary(
        context,
        current_origin="controlled_optimization_rerun",
        language="en",
        benchmark_delta_text_fn=lambda value: f"+{float(value):.3f}",
    )

    assert "baseline delta +0.018" in summary
    assert "accepted 2 rounds, rolled back 1 rounds" in summary
    assert "best candidate round 3" in summary
    assert "remaining risks: quality guard reached" in summary


def test_ai_tuning_chain_summary_uses_chinese_copy_and_skips_manual_empty_context():
    assert ai_tuning_chain_summary({}, current_origin="manual_run", language="en") == ""

    summary = ai_tuning_chain_summary(
        {"history": [{"round_num": 1, "accepted": True, "r_squared_after": 0.91}]},
        current_origin="controlled_optimization_rerun",
        language="zh",
    )

    assert "基线变化：N/A" in summary
    assert "接受 1 轮，回滚 0 轮" in summary
    assert "当前最佳：第 1 轮" in summary


def test_ai_tuning_report_context_builds_summary_and_dedupes_rollback_risks():
    history = [
        {"accepted": True},
        {"accepted": False, "llm_advice": {"rollback_reason": "axis outlier"}},
        {"accepted": False, "llm_advice": {"rollback_reason": "axis outlier"}},
        {"accepted": False, "llm_advice": {"rollback_reason": "quality guard"}},
    ]

    context = ai_tuning_report_context(
        {
            "best_r_squared": 0.981,
            "improvement": {"r_squared_abs": 0.012},
            "rounds": 4,
            "convergence_reason": "stable",
            "benchmark_summary": {"average_objective_delta": 0.015},
            "history": history,
        },
        benchmark_summary_text_fn=lambda summary: f"Benchmark {summary['average_objective_delta']}",
        accepted_summary_text_fn=lambda accepted, best_r2, delta, rounds: (
            f"accepted={accepted}; best={best_r2}; delta={delta}; rounds={rounds}"
        ),
        empty_text_fn=lambda: "empty",
        stop_text_fn=lambda reason: f"stop={reason}",
        risks_text_fn=lambda risks: f"risks={risks}",
        goal_body_fn=lambda focus, watch: f"focus {focus}; watch {watch}",
        goal_text_fn=lambda goal: f"goal={goal}",
    )

    assert context == {
        "summary": (
            "accepted=1; best=0.981; delta=0.012; rounds=4\n"
            "Benchmark 0.015\n"
            "stop=stable\n"
            "risks=axis outlier; quality guard\n"
            "goal=focus stable; watch axis outlier; quality guard"
        ),
        "accepted_summary": "accepted=1; best=0.981; delta=0.012; rounds=4",
        "benchmark_summary": {"average_objective_delta": 0.015},
        "benchmark_text": "Benchmark 0.015",
        "history": history,
        "stop_reason": "stable",
        "remaining_risks": "axis outlier; quality guard",
        "next_goal": "focus stable; watch axis outlier; quality guard",
    }


def test_ai_tuning_report_context_handles_invalid_report_shapes():
    context = ai_tuning_report_context(
        {"history": "bad", "benchmark_summary": "bad"},
        benchmark_summary_text_fn=lambda summary: "unused",
        accepted_summary_text_fn=lambda accepted, best_r2, delta, rounds: f"accepted={accepted}",
        empty_text_fn=lambda: "empty",
        goal_body_fn=lambda focus, watch: f"{focus}/{watch}",
        goal_text_fn=lambda goal: f"goal={goal}",
    )

    assert context["summary"] == "accepted=0\ngoal=empty/empty"
    assert context["benchmark_summary"] == {}
    assert context["benchmark_text"] == ""
    assert context["history"] == []
    assert context["remaining_risks"] == ""
    assert context["next_goal"] == "empty/empty"


def test_ai_tuning_previous_round_summary_text_returns_empty_text_for_missing_context():
    assert ai_tuning_previous_round_summary_text(
        None,
        label_text="Previous:",
        empty_text="No context",
        stop_text_fn=lambda value: f"stop={value}",
        risks_text_fn=lambda value: f"risks={value}",
        goal_text_fn=lambda value: f"goal={value}",
    ) == "No context"
    assert ai_tuning_previous_round_summary_text(
        {},
        label_text="Previous:",
        empty_text="No context",
        stop_text_fn=lambda value: f"stop={value}",
        risks_text_fn=lambda value: f"risks={value}",
        goal_text_fn=lambda value: f"goal={value}",
    ) == "No context"


def test_ai_tuning_previous_round_summary_text_builds_ordered_deduped_lines():
    text = ai_tuning_previous_round_summary_text(
        {
            "summary": "Round summary",
            "accepted_summary": "Accepted summary",
            "benchmark_text": "Accepted summary",
            "stop_reason": "stable",
            "remaining_risks": "quality guard",
            "next_goal": "tighten window",
        },
        label_text="Previous:",
        empty_text="No context",
        stop_text_fn=lambda value: f"stop={value}",
        risks_text_fn=lambda value: f"risks={value}",
        goal_text_fn=lambda value: f"goal={value}",
    )

    assert text == "\n".join(
        [
            "Previous:",
            "Round summary",
            "Accepted summary",
            "stop=stable",
            "risks=quality guard",
            "goal=tighten window",
        ]
    )


def test_ai_tuning_tunable_summary_text_formats_constraints_and_remaining_count():
    param_map = {
        "mode": FakeParamRule(("fast", "balanced", "accurate", "manual")),
        "alpha": FakeParamRule((0.1, 0.9)),
        "beta": FakeParamRule([1, 3]),
        "gamma": FakeParamRule(("low", "high")),
        "delta": FakeParamRule((5, 7)),
    }

    text = ai_tuning_tunable_summary_text(
        param_map,
        current_value_fn=lambda name: {"mode": "balanced", "alpha": 0.4}.get(name, "-"),
        none_text="none",
        row_text_fn=lambda name, current, constraint: f"{name}={current} [{constraint}]",
        more_text_fn=lambda remaining: f"+{remaining} more",
    )

    assert text == "\n".join(
        [
            "mode=balanced [fast, balanced, accurate, ...]",
            "alpha=0.4 [0.1 -> 0.9]",
            "beta=- [1 -> 3]",
            "gamma=- [low, high]",
            "+1 more",
        ]
    )


def test_ai_tuning_tunable_summary_text_returns_none_text_without_params():
    assert ai_tuning_tunable_summary_text(
        {},
        current_value_fn=lambda name: "-",
        none_text="none",
        row_text_fn=lambda name, current, constraint: "unused",
        more_text_fn=lambda remaining: "unused",
    ) == "none"
    assert ai_tuning_tunable_summary_text(
        None,
        current_value_fn=lambda name: "-",
        none_text="none",
        row_text_fn=lambda name, current, constraint: "unused",
        more_text_fn=lambda remaining: "unused",
    ) == "none"


def test_controlled_optimization_review_parts_prefer_live_tuning_context():
    parts = controlled_optimization_review_parts(
        {
            "tuning_goal": "risk",
            "benchmark_text": "Benchmark: current",
            "stop_reason": "stop now",
            "remaining_risks": "risk remains",
            "next_goal": "next current",
        },
        {
            "tuning_goal_label": "history goal",
            "benchmark_text": "Benchmark: history",
            "stop_reason": "history stop",
            "remaining_risks": "history risk",
            "next_goal": "history next",
        },
        tuning_goal_label_fn=lambda goal: f"goal:{goal}",
        benchmark_summary_text_fn=lambda summary: "summary text",
    )

    assert parts.tuning_goal == "goal:risk"
    assert parts.benchmark_text == "Benchmark: current"
    assert parts.stop_reason == "stop now"
    assert parts.remaining_risks == "risk remains"
    assert parts.next_goal == "next current"


def test_controlled_optimization_review_parts_fall_back_to_history_context():
    parts = controlled_optimization_review_parts(
        {},
        {
            "tuning_goal": "joint",
            "benchmark_summary": {"average_objective_delta": 0.018},
            "remaining_risks": "history risk",
            "next_goal": "history next",
        },
        tuning_goal_label_fn=lambda goal: f"goal:{goal}",
        benchmark_summary_text_fn=lambda summary: "Benchmark summary",
    )

    assert parts.tuning_goal == "goal:joint"
    assert parts.benchmark_text == "Benchmark summary"
    assert parts.stop_reason == ""
    assert parts.remaining_risks == "history risk"
    assert parts.next_goal == "history next"


def test_history_record_confirmed_uses_record_or_summary_flag():
    assert history_record_confirmed({"confirmed": True, "results_summary": {}}) is True
    assert history_record_confirmed({"confirmed": False, "results_summary": {"confirmed": True}}) is True
    assert history_record_confirmed({"confirmed": False, "results_summary": {"confirmed": False}}) is False
    assert history_record_confirmed(None) is False


def test_history_confirmation_translation_key_selects_confirmed_or_pending_key():
    assert history_confirmation_translation_key(True) == "RESULTS_CONFIRM_STATUS_CONFIRMED"
    assert history_confirmation_translation_key(False) == "RESULTS_CONFIRM_STATUS_PENDING"


def test_current_result_confirmation_label_prefers_project_then_fallbacks():
    assert current_result_confirmation_label(
        {"results_summary": {"project_label": "PA6"}},
        inferred_sample_name="sample-a",
        technique_label="SAXS",
    ) == "PA6"
    assert current_result_confirmation_label(
        {"results_summary": {"project_label": ""}},
        inferred_sample_name="sample-a",
        technique_label="SAXS",
    ) == "sample-a"
    assert current_result_confirmation_label(
        {},
        inferred_sample_name="",
        technique_label="SAXS",
    ) == "SAXS"


def test_history_action_state_summarizes_button_enablement():
    empty = history_action_state(None, has_source=False, has_compare=False)

    assert empty.can_copy_summary is False
    assert empty.can_restore is False
    assert empty.can_rerun is False
    assert empty.can_compare is False
    assert empty.can_confirm is False

    missing_source = history_action_state({"id": "run-a"}, has_source=False, has_compare=True)

    assert missing_source.can_copy_summary is True
    assert missing_source.can_restore is False
    assert missing_source.can_rerun is False
    assert missing_source.can_compare is True
    assert missing_source.can_confirm is True

    ready = history_action_state({"id": "run-a"}, has_source=True, has_compare=False)

    assert ready.can_copy_summary is True
    assert ready.can_restore is True
    assert ready.can_rerun is True
    assert ready.can_compare is False
    assert ready.can_confirm is True


def test_history_tooltip_keys_follow_record_source_and_compare_state():
    record = {"id": "run-a"}

    assert history_copy_summary_tooltip_key(None) == "select"
    assert history_copy_summary_tooltip_key(record) == "copy_summary"
    assert history_restore_tooltip_key(None, has_source=False) == "select"
    assert history_restore_tooltip_key(record, has_source=False) == "source_missing"
    assert history_restore_tooltip_key(record, has_source=True) == "restore"
    assert history_rerun_tooltip_key(record, has_source=True) == "rerun"
    assert history_compare_tooltip_key(None, has_compare=False) == "select"
    assert history_compare_tooltip_key(record, has_compare=False) == "compare_unavailable"
    assert history_compare_tooltip_key(record, has_compare=True) == "compare"


def test_history_tooltip_translation_key_maps_stable_tooltip_states():
    assert history_tooltip_translation_key("select") == "HISTORY_TOOLTIP_SELECT"
    assert history_tooltip_translation_key("source_missing") == "HISTORY_TOOLTIP_SOURCE_MISSING"
    assert history_tooltip_translation_key("compare_unavailable") == "HISTORY_TOOLTIP_COMPARE_UNAVAILABLE"
    assert history_tooltip_translation_key("restore") == "HISTORY_RESTORE_TOOLTIP"
    assert history_tooltip_translation_key("rerun") == "HISTORY_RERUN_TOOLTIP"
    assert history_tooltip_translation_key("compare") == "HISTORY_COMPARE_TOOLTIP"
    assert history_tooltip_translation_key("copy_summary") == "HISTORY_COPY_SUMMARY_TOOLTIP"
    assert history_tooltip_translation_key("unknown") == "HISTORY_TOOLTIP_SELECT"


def test_history_status_label_parts_maps_known_statuses_and_flags_saxs_suffix():
    completed_saxs = history_status_label_parts({"status": "completed", "technique": "saxs"})
    assert completed_saxs.translation_key == "SAMPLE_RUN_STATUS_COMPLETED"
    assert completed_saxs.fallback_label == ""
    assert completed_saxs.include_saxs_suffix is True

    pending_waxs = history_status_label_parts({"status": "pending", "technique": "waxs"})
    assert pending_waxs.translation_key == "SAMPLE_RUN_STATUS_PENDING"
    assert pending_waxs.include_saxs_suffix is False

    custom = history_status_label_parts({"status": "archived", "technique": "saxs"})
    assert custom.translation_key == ""
    assert custom.fallback_label == "archived"
    assert custom.include_saxs_suffix is False


def test_history_status_text_parts_keeps_labels_order_and_marks_missing_source():
    available = history_status_text_parts("Completed", "AI rerun", source_available=True)
    assert available.labels == ["Completed", "AI rerun"]
    assert available.source_missing is False

    missing = history_status_text_parts("Completed", "", source_available=False)
    assert missing.labels == ["Completed"]
    assert missing.source_missing is True


def test_history_validation_summary_text_appends_warnings_and_limits_them():
    record = {
        "results_summary": {
            "validation_summary": "Check issues",
            "validation_warnings": ["w1", "w2", "w3", "w4", "w5"],
        }
    }

    assert history_validation_summary_text(record) == "Check issues | w1, w2, w3, w4"


def test_history_validation_summary_text_prefers_quality_flags_when_summary_empty_or_all_passed():
    empty_record = {
        "results_summary": {
            "result": {"quality_flags": {"warning": ["low support"]}},
        }
    }
    passed_record = {
        "results_summary": {
            "validation_summary": "All checks passed",
            "result": {"quality_flags": {"warning": ["manual review"]}},
        }
    }

    quality_texts = []

    def quality_summary(payload):
        quality_texts.append(payload)
        return "Quality flags"

    assert history_validation_summary_text(empty_record, quality_flag_summary_fn=quality_summary) == "Quality flags"
    assert history_validation_summary_text(passed_record, quality_flag_summary_fn=quality_summary) == "Quality flags"
    assert quality_texts == [
        empty_record["results_summary"]["result"],
        passed_record["results_summary"]["result"],
    ]


def test_history_validation_summary_text_keeps_all_passed_without_quality_flags():
    assert history_validation_summary_text(
        {"results_summary": {"validation_summary": "All checks passed", "result": {}}},
        quality_flag_summary_fn=lambda payload: "",
    ) == "All checks passed"


def test_history_record_context_ref_prefers_submodule_then_technique():
    submodule = history_record_context_ref({"submodule": "saxs.temperature", "technique": "saxs"})
    assert submodule.kind == "submodule"
    assert submodule.value == "saxs.temperature"

    technique = history_record_context_ref({"submodule": "", "technique": "waxs"})
    assert technique.kind == "technique"
    assert technique.value == "waxs"

    empty = history_record_context_ref(None)
    assert empty.kind == ""
    assert empty.value == ""


def test_history_metrics_summary_orders_preferred_keys_by_technique():
    metrics = {
        "extra": "tail",
        "Xc_pct": "41.5",
        "n_peaks": "3",
        "waxs_support_score": "0.72",
        "D_Scherrer_nm": "8.2",
    }

    assert history_metrics_summary(metrics, technique="waxs", limit=2) == (
        "n_peaks=3 | Xc_pct=41.5 | D_Scherrer_nm=8.2 | waxs_support_score=0.72 | extra=tail"
    )

    saxs_metrics = {
        "Tm_peak_C": "221.0",
        "lc_reliability_status": "diagnostic_only",
        "lc_nm": "12.3",
        "extra": "tail",
    }

    assert history_metrics_summary(saxs_metrics, technique="saxs", limit=3) == (
        "lc_nm=12.3 | lc_reliability_status=diagnostic_only | Tm_peak_C=221.0"
    )
    assert history_metrics_summary({}, technique="waxs") == ""


def test_flatten_params_handles_nested_scalars_and_lists():
    params = {
        "scan_a": {"Xc": 42.0, "peaks": [1, 2, 3]},
        "points": [(1.0, 2.0), (3.0, 4.0)],
        "_private": "skip",
        "batch_frames": 3,
    }

    assert flatten_params(params) == [
        ("scan_a.Xc", 42.0),
        ("scan_a.peaks", "[1, 2, 3]"),
        ("points", "1.0:2.00, 3.0:4.00"),
    ]


def test_history_record_analysis_evidence_normalizes_waxs_temperature_sections():
    evidence = {
        "analysis_evidence": {
            "temperature_axis_confidence": 0.9,
            "peak_family_continuity_score": 0.8,
            "feature_evidence": {},
        }
    }
    record = {
        "technique": "waxs",
        "submodule": "waxs.temperature",
        "results_summary": {"result": evidence},
    }

    normalized = history_record_analysis_evidence(record)

    feature = normalized["feature_evidence"]
    assert feature["sequence_evidence"]["temperature_axis_confidence"] == 0.9
    assert feature["peak_family_evidence"]["peak_family_continuity_score"] == 0.8


def test_history_result_metrics_merges_parameters_summary_and_evidence():
    record = {
        "technique": "waxs",
        "parameters": {"nested": {"D_Scherrer_nm": 8.2}},
        "analysis_evidence": {"n_peaks": 3, "waxs_support_score": 0.72},
        "results_summary": {
            "result": {
                "parameters": {"Xc_pct": 41.5},
                "validation_summary": "All checks passed",
            },
            "r2": 0.991,
            "validation_summary": "skip as metric",
            "quality_flags": {"x": "WARN"},
        },
    }

    metrics = history_result_metrics(record)

    assert metrics["Xc_pct"] == "41.5"
    assert metrics["nested.D_Scherrer_nm"] == "8.2"
    assert metrics["n_peaks"] == "3"
    assert metrics["waxs_support_score"] == "0.72"
    assert metrics["r2"] == "0.991"
    assert "validation_summary" not in metrics
    assert "quality_flags" not in metrics


def test_validation_summary_parts_prefers_summary_and_deduplicates_warnings():
    record = {
        "validation_summary": "record-level",
        "validation_warnings": ["record warn"],
        "results_summary": {
            "validation_summary": "summary-level",
            "validation_warnings": ["summary warn", "record warn"],
            "result": {
                "validation_summary": "result-level",
                "validation_warnings": ["result warn", "summary warn"],
            },
        },
    }

    parts = validation_summary_parts(record)

    assert parts.summary == "summary-level"
    assert parts.warnings == ["summary warn", "record warn", "result warn"]


def test_validation_summary_parts_returns_empty_for_invalid_record():
    parts = validation_summary_parts(None)

    assert parts.summary == ""
    assert parts.warnings == []


def test_history_compare_record_prefers_previous_same_submodule_neighbor():
    current = {"id": "current", "batch_id": "batch-1", "technique": "saxs", "submodule": "saxs.static"}
    runs = [
        {"id": "current", "technique": "saxs", "submodule": "saxs.static"},
        {"id": "same-submodule", "technique": "saxs", "submodule": "saxs.static"},
        {"id": "other-submodule", "technique": "saxs", "submodule": "saxs.temperature"},
        {"id": "other-technique", "technique": "waxs", "submodule": "waxs.static"},
    ]

    assert history_compare_record(current, runs) == runs[1]


def test_history_compare_record_falls_back_to_any_same_technique_without_submodule():
    current = {"id": "current", "batch_id": "batch-1", "technique": "saxs", "submodule": ""}
    runs = [
        {"id": "other", "technique": "saxs", "submodule": "saxs.temperature"},
        {"id": "current", "technique": "saxs", "submodule": ""},
    ]

    assert history_compare_record(current, runs) == runs[0]


def test_history_compare_rows_use_stable_state_keys_and_priority_sort():
    assert history_compare_state_key("1", "1") == "same"
    assert history_compare_state_key("1", "") == "new"
    assert history_compare_state_key("", "1") == "removed"
    assert history_compare_state_key("1", "2") == "changed"
    assert history_compare_state_translation_key("changed") == "HISTORY_COMPARE_STATE_CHANGED"
    assert history_compare_state_translation_key("new") == "HISTORY_COMPARE_STATE_NEW"
    assert history_compare_state_translation_key("removed") == "HISTORY_COMPARE_STATE_REMOVED"
    assert history_compare_state_translation_key("same") == "HISTORY_COMPARE_STATE_SAME"
    assert history_compare_state_translation_key("weird") == "HISTORY_COMPARE_STATE_CHANGED"

    rows = history_compare_rows(
        {"same": "1", "new": "3", "changed": "2"},
        {"same": "1", "removed": "4", "changed": "0"},
    )

    assert rows == [
        ("changed", "2", "0", "changed"),
        ("new", "3", "", "new"),
        ("removed", "", "4", "removed"),
        ("same", "1", "1", "same"),
    ]
    assert history_compare_counts(rows) == {
        "changed": 1,
        "new": 1,
        "removed": 1,
        "same": 1,
    }


def test_result_origin_translation_key_maps_known_origins_and_leaves_unknown_blank():
    assert result_origin_translation_key("controlled_optimization_rerun") == "RESULT_ORIGIN_AI_TUNED"
    assert result_origin_translation_key("manual_run") == "RESULT_ORIGIN_MANUAL"
    assert result_origin_translation_key("external") == ""
    assert result_origin_translation_key("") == ""


def test_result_comparison_record_label_joins_sample_context_time_and_origin():
    label = result_comparison_record_label(
        {
            "created_at": "2026-07-06T10:11:12",
            "results_summary": {"project_label": "PA6"},
        },
        context_label="SAXS static",
        origin_label="AI tuned",
    )

    assert label == "PA6 | SAXS static | 2026-07-06 10:11 | AI tuned"
    assert result_comparison_record_label(None, context_label="SAXS", origin_label="Manual") == ""
    assert result_comparison_record_label({"results_summary": {}}, context_label="", origin_label="Manual") == "Manual"


def test_result_compare_candidate_helpers_select_id_label_and_baseline():
    candidates = [
        {"id": "run-a"},
        {"id": "run-b"},
    ]

    assert result_compare_candidate_id(candidates[0]) == "run-a"
    assert result_compare_candidate_id(None) == ""
    assert result_compare_candidate_label("Baseline", index=1, empty_label="Empty") == "2. Baseline"
    assert result_compare_candidate_label("", index=None, empty_label="Empty") == "Empty"
    assert result_comparison_baseline(candidates, selected_id="run-b") == candidates[1]
    assert result_comparison_baseline(candidates, selected_id="missing") == candidates[0]
    assert result_comparison_baseline([], selected_id="run-a") is None


def test_result_comparison_candidates_prefers_same_sample_submodule_and_newer_runs():
    current = {
        "id": "current",
        "technique": "saxs",
        "submodule": "saxs.static",
        "results_summary": {"project_label": "PA6"},
    }

    candidates = result_comparison_candidates(current, FakeCompareDB(), inferred_sample_name="")

    assert [item["id"] for item in candidates] == ["same-new", "same-old", "same-empty-sub"]


def test_result_comparison_candidates_falls_back_to_matching_technique_without_same_sample():
    current = {
        "id": "current",
        "technique": "saxs",
        "submodule": "saxs.static",
        "results_summary": {"project_label": "Missing"},
    }

    candidates = result_comparison_candidates(current, FakeCompareDB(), inferred_sample_name="")

    assert [item["id"] for item in candidates] == ["fallback-new", "same-new", "same-old", "same-empty-sub"]
    assert result_comparison_candidates({}, FakeCompareDB(), inferred_sample_name="") == []
    assert result_comparison_candidates(current, None, inferred_sample_name="") == []


def test_result_comparison_candidates_prefers_headers_without_full_run_reads():
    current = {
        "id": "current",
        "technique": "saxs",
        "submodule": "saxs.static",
        "results_summary": {"project_label": "PA6"},
    }
    db = HeaderOnlyComparisonDB()

    candidates = result_comparison_candidates(current, db)

    assert [item["id"] for item in candidates] == ["fallback-new", "same-new", "same-old", "same-empty-sub"]
    assert db.header_calls == 1
    assert db.full_run_calls == 0
    assert all("parameters" not in item for item in candidates)


def test_result_comparison_candidates_prefer_same_sample_headers_without_payload_reads():
    class SameSampleHeaderDB:
        def get_analysis_runs(self, batch_id):
            raise AssertionError("header query should avoid full run reads")

        def list_analysis_run_headers(self, *, limit=500):
            assert limit == 500
            return [
                {
                    "id": "pet-new",
                    "technique": "saxs",
                    "submodule": "saxs.static",
                    "sample_name": "PET",
                    "created_at": "2026-07-05 10:00:00",
                },
                {
                    "id": "pa6-old",
                    "technique": "saxs",
                    "submodule": "saxs.static",
                    "sample_name": "PA6",
                    "created_at": "2026-07-01 10:00:00",
                },
            ]

    current = {
        "id": "current",
        "technique": "saxs",
        "submodule": "saxs.static",
        "results_summary": {"project_label": "PA6"},
    }

    candidates = result_comparison_candidates(current, SameSampleHeaderDB())

    assert [item["id"] for item in candidates] == ["pa6-old"]


def test_result_comparison_candidates_does_not_fall_back_when_header_query_is_unavailable():
    current = {"id": "current", "technique": "saxs", "submodule": "saxs.static"}
    db = UnavailableHeaderComparisonDB()

    assert result_comparison_candidates(current, db) == []
    assert db.full_run_calls == 0


def test_result_to_jsonable_normalizes_nested_containers_paths_and_array_like_values(tmp_path):
    class ArrayLike:
        def tolist(self):
            return (tmp_path / "a.csv", {"answer": ScalarLike()})

    class ScalarLike:
        def item(self):
            return 42

    payload = {
        1: tmp_path / "root",
        "nested": [ArrayLike(), {3, 1}],
    }

    converted = result_to_jsonable(payload)

    assert converted["1"] == str(tmp_path / "root")
    assert converted["nested"][0] == [str(tmp_path / "a.csv"), {"answer": 42}]
    assert sorted(converted["nested"][1]) == [1, 3]


def test_result_to_jsonable_warns_and_falls_back_when_array_like_conversion_fails():
    class Broken:
        def tolist(self):
            raise RuntimeError("bad list")

        def item(self):
            raise RuntimeError("bad item")

        def __str__(self):
            return "broken-value"

    warnings = []

    assert result_to_jsonable(Broken(), warning_fn=warnings.append) == "broken-value"
    assert warnings == [
        "Failed to convert array-like value with tolist().",
        "Failed to unwrap scalar value with item().",
    ]


def test_result_comparison_summary_reports_current_only_without_baseline():
    assert result_comparison_summary(
        current_label="Current run",
        baseline_label="",
        current_metrics={"L_nm": "12.0"},
        baseline_metrics={},
        technique="saxs",
    ) == "Current: Current run"


def test_result_comparison_summary_lists_key_changes_for_technique():
    summary = result_comparison_summary(
        current_label="Current run",
        baseline_label="Baseline run",
        current_metrics={
            "lc_nm": "12.0",
            "lc_method": "fit",
            "Tm_peak_C": "221.0",
            "extra": "ignored",
        },
        baseline_metrics={
            "lc_nm": "10.0",
            "lc_method": "fit",
            "Tm_peak_C": "",
        },
        technique="saxs",
    )

    assert summary == (
        "Current: Current run | Baseline: Baseline run | Key changes: "
        "lc_nm: 10.0 -> 12.0; Tm_peak_C: - -> 221.0"
    )


def test_result_comparison_summary_uses_strain_keys_when_active():
    summary = result_comparison_summary(
        current_label="Current run",
        baseline_label="Baseline run",
        current_metrics={"Q_star_rel_mean": "1.20", "lc_nm": "12.0"},
        baseline_metrics={"Q_star_rel_mean": "1.00", "lc_nm": "10.0"},
        technique="saxs",
        strain_active=True,
    )

    assert "invariant_Q_rel_mean: 1.00 -> 1.20" in summary
    assert "lc_nm" not in summary


def test_result_review_metric_summary_uses_default_and_strain_keys():
    assert result_review_metric_summary(
        {
            "r_squared": "0.98",
            "L_nm": "12.3",
            "Xc_pct": "41.5",
            "quality_score": "0.88",
            "extra": "ignored",
        },
        technique="dsc",
    ) == "r_squared=0.98, L_nm=12.3, Xc_pct=41.5, quality_score=0.88"

    assert result_review_metric_summary(
        {
            "Q_star_rel_mean": "1.03",
            "phi_void_mean": "0.02",
            "f_Herman_mean": "0.66",
            "porod_slope_mean": "-3.8",
            "void_detected_frames": "4",
            "lc_nm": "ignored",
        },
        technique="saxs",
        strain_active=True,
    ) == "invariant_Q_rel_mean=1.03, phi_void_mean=0.02, f_Herman_mean=0.66, porod_slope_mean=-3.8"
    assert result_review_metric_summary({}, technique="waxs") == ""


def test_result_source_summary_text_builds_waxs_core_trend_support_and_validation():
    text = result_source_summary_text(
        {"results_summary": {"validation_summary": "review needed"}},
        current_metrics={"n_peaks": "3", "Xc_pct": "41.5", "D_Scherrer_nm": "8.2"},
        evidence={
            "peak_support_score": 0.8,
            "background_stability_score": 0.7,
            "waxs_support_score": 0.75,
        },
        origin_label="AI tuned",
        technique="waxs",
        trend_evidence={"D_trend_support_score": 0.9, "D_trend_monotonicity": "stable", "instrument_broadening_present": True},
        empty_text="N/A",
        format_score_value_fn=lambda value: f"{float(value):.2f}",
        display_text_fn=lambda value: str(value) if value not in (None, "") else "N/A",
        constraint_text="constraints ok",
    )

    assert text == (
        "AI tuned | core=n_peaks=3, Xc_pct=41.5, D_Scherrer_nm=8.2 | "
        "trend=score=0.9, mode=stable, instrument_broadening=True | "
        "support=peak=0.80 | background=0.70 | D_trend=0.90 | waxs_support_score=0.75 | "
        "validation=review needed | constraints ok"
    )


def test_result_source_summary_text_builds_generic_core_and_uses_empty_fallback():
    assert result_source_summary_text(
        {"technique": "saxs"},
        current_metrics={"r_squared": "0.98", "quality_score": "0.77", "L_nm": "12.0", "extra": "ignored"},
        evidence={},
        origin_label="Manual",
        technique="saxs",
        empty_text="N/A",
        constraint_text="N/A",
    ) == "Manual | core=r_squared=0.98, quality_score=0.77, L_nm=12.0"

    assert result_source_summary_text({}, current_metrics={}, evidence={}, empty_text="N/A") == "N/A"


def test_work_memory_summary_text_uses_first_slices_and_deduplicates_extra_lines():
    text = work_memory_summary_text(
        [
            {"label": "Current", "detail": "run-a"},
            {"label": "History", "detail": "run-b"},
            {"label": "Sample", "detail": "PA6"},
            {"label": "Export", "detail": "bundle"},
        ],
        extra_lines=["Benchmark: +0.018", "Current: run-a", "Benchmark: +0.018"],
    )

    assert text == "Current: run-a | History: run-b | Sample: PA6 | Benchmark: +0.018"


def test_work_memory_summary_text_handles_label_or_detail_only():
    assert work_memory_summary_text(
        [{"label": "Current", "detail": ""}, {"label": "", "detail": "detail only"}],
        extra_lines=[],
    ) == "Current | detail only"


def test_workspace_context_summary_text_combines_current_joint_and_work_memory_lines():
    text = workspace_context_summary_text(
        {
            "confirmed": True,
            "results_summary": {
                "project_label": "Project A",
                "ai_tuned": True,
            },
        },
        confirm_state_text="confirmed by user",
        origin_label="AI tuned",
        current_note="risk ok",
        joint_report={
            "rows": [{"sample": "PA6"}, {"sample": "PET"}],
            "validations": [{"check": "a"}],
        },
        joint_context={"summary": "Joint summary"},
        joint_label="Joint",
        joint_count_text_fn=lambda rows, validations: f"{rows} rows, {validations} validations",
        work_memory={"slices": [{"label": "Sample", "detail": "PA6"}, {"label": "Batch", "detail": "B1"}]},
        empty_text="No context",
    )

    assert text == "\n".join(
        [
            "Current result: Project A | confirmed by user | confirmed=True | ai_tuned=True | AI tuned | risk ok",
            "Joint: Joint summary",
            "2 rows, 1 validations",
            "Sample: PA6",
            "Batch: B1",
        ]
    )


def test_workspace_context_summary_text_uses_joint_report_summary_and_limits_lines():
    text = workspace_context_summary_text(
        {"results_summary": {}},
        confirm_state_text="pending",
        origin_label="",
        current_note="",
        joint_report={"summary": "Report summary"},
        joint_context={"summary": "Context summary"},
        joint_label="Joint",
        joint_count_text_fn=lambda rows, validations: "unused",
        work_memory={
            "slices": [
                {"label": "One", "detail": "1"},
                {"label": "Two", "detail": "2"},
                {"label": "Three", "detail": "3"},
                {"label": "Four", "detail": "4"},
            ]
        },
        empty_text="No context",
    )

    assert text.splitlines() == [
        "Current result: pending | confirmed=False | ai_tuned=False",
        "Joint: Report summary",
        "One: 1",
        "Two: 2",
        "Three: 3",
    ]


def test_workspace_context_summary_text_returns_empty_text_without_context():
    assert workspace_context_summary_text(
        {},
        confirm_state_text="",
        origin_label="",
        current_note="",
        joint_report=None,
        joint_context={},
        joint_label="Joint",
        joint_count_text_fn=lambda rows, validations: "unused",
        work_memory={},
        empty_text="No context",
    ) == "No context"


def test_quality_flag_summary_text_maps_known_flags_and_limits_output():
    result = {
        "quality_flag": (
            "WARN:low_snr; WARN:sasmodels_low_r2; ERROR:sasmodels_failed; "
            "WARN:qstar_series_jump; ERROR:L_not_computed"
        )
    }

    assert quality_flag_summary_text(result, language="en") == (
        "low peak SNR; weak sasmodels fit; sasmodels fit failed; adjacent-frame Q* jump"
    )
    assert quality_flag_summary_text(result, language="zh") == (
        "主峰信噪比偏低；sasmodels 拟合偏弱；sasmodels 拟合失败；相邻帧 Q* 跳变较大"
    )


def test_quality_flag_summary_text_handles_unknown_empty_and_object_values():
    class Result:
        quality_flag = "ERROR:custom_flag"

    assert quality_flag_summary_text(Result(), language="en") == "custom flag"
    assert quality_flag_summary_text({"quality_flag": "OK"}, language="en") == ""
    assert quality_flag_summary_text({"quality_flag": ""}, language="zh") == ""
    assert quality_flag_summary_text(None, language="en") == ""


def test_gui_display_text_helpers_use_empty_fallback_and_json_for_structures():
    assert gui_display_text_value(None, empty_text="N/A") == "N/A"
    assert gui_display_text_value("  value  ", empty_text="N/A") == "value"
    assert gui_display_text_value("", empty_text="N/A") == "N/A"
    assert gui_display_text({"a": 1}, empty_text="N/A") == '{"a": 1}'
    assert gui_display_text(["x", 2], empty_text="N/A") == '["x", 2]'
    assert gui_display_text(None, empty_text="N/A") == "N/A"


def test_analysis_history_service_reuses_risk_helper_module_functions():
    service = importlib.import_module("polynexus.gui.analysis_history_service")

    assert service.gui_display_text_value is helper_gui_display_text_value
    assert service.gui_display_text is helper_gui_display_text
    assert service.gui_format_score_value is helper_gui_format_score_value
    assert service.gui_coerce_summary_float is helper_gui_coerce_summary_float
    assert service.results_has_critical_risk is helper_results_has_critical_risk
    assert service.has_condition_axis_risk is helper_has_condition_axis_risk
    assert service.has_fallback_conflict_risk is helper_has_fallback_conflict_risk
    assert service.results_next_step_translation_key is helper_results_next_step_translation_key
    assert service.result_mask_summary_text is helper_result_mask_summary_text
    assert service.ordered_results_columns is helper_ordered_results_columns
    assert service.measured_result_metric_parts is helper_measured_result_metric_parts


def test_gui_format_score_value_and_coerce_summary_float():
    assert gui_format_score_value(0.12345, empty_text="N/A") == "0.123"
    assert gui_format_score_value(0.12345, empty_text="N/A", signed=True) == "+0.123"
    assert gui_format_score_value(-0.5, empty_text="N/A", signed=True) == "-0.500"
    assert gui_format_score_value("bad", empty_text="N/A") == "N/A"

    assert gui_coerce_summary_float("0.72") == 0.72
    assert gui_coerce_summary_float("nan") is None
    assert gui_coerce_summary_float(None) is None


def test_results_has_critical_risk_uses_precomputed_saxs_risk_flags():
    assert results_has_critical_risk(
        {},
        technique="saxs",
        condition_axis_risk=True,
        fallback_conflict_risk=False,
    ) is True
    assert results_has_critical_risk(
        {},
        technique="saxs",
        condition_axis_risk=False,
        fallback_conflict_risk=True,
    ) is True


def test_has_condition_axis_risk_uses_symptoms_evidence_and_batch_params():
    assert has_condition_axis_risk({}, symptom_names=["condition_axis_missing"]) is True
    assert has_condition_axis_risk(
        {},
        analysis_evidence={
            "condition_evidence": {
                "condition_missing_frames": 1,
                "condition_continuity_score": 0.99,
                "condition_confidence": 0.99,
            }
        },
    ) is True
    assert has_condition_axis_risk(
        {},
        analysis_evidence={
            "condition_evidence": {
                "condition_missing_frames": 0,
                "condition_continuity_score": 0.84,
                "condition_confidence": 0.99,
            }
        },
    ) is True
    assert has_condition_axis_risk(
        {"batch_frames": 2, "condition_missing_frames": 0, "condition_continuity_score": 0.9, "condition_confidence": 0.74}
    ) is True
    assert has_condition_axis_risk({"batch_frames": 1, "condition_confidence": 0.1}) is False


def test_has_fallback_conflict_risk_requires_fallback_and_conflict_symptoms():
    assert has_fallback_conflict_risk(
        [
            "temperature_calibration_fallback_active",
            "batch_summary_conflicts_with_frame_evidence",
        ]
    ) is True
    assert has_fallback_conflict_risk(
        [
            "temperature_calibration_fallback_active",
            "thickness_chain_unreliable",
        ]
    ) is True
    assert has_fallback_conflict_risk(["temperature_calibration_fallback_active"]) is False


def test_results_has_critical_risk_detects_waxs_and_dsc_evidence_limits():
    assert results_has_critical_risk(
        {},
        technique="waxs",
        waxs_structure={"physical_support_pass": False},
        waxs_support={"waxs_support_score": 0.9},
    ) is True
    assert results_has_critical_risk(
        {},
        technique="waxs",
        waxs_structure={"physical_support_pass": True},
        waxs_support={"waxs_support_score": 0.5},
    ) is True
    assert results_has_critical_risk(
        {},
        technique="dsc",
        analysis_evidence={
            "feature_evidence": {
                "structure_evidence": {"paper_conclusion_ready": False},
                "event_support_evidence": {
                    "event_support_score": "0.70",
                    "baseline_stability_score": "0.90",
                    "thermodynamic_consistency_score": "bad",
                },
            }
        },
    ) is True


def test_results_has_critical_risk_detects_validation_and_mask_risks():
    class Result:
        validation_summary = "Needs review"
        mask_truncated = False
        beam_stop_contaminated = False

    assert results_has_critical_risk({}, technique="saxs", result=Result()) is True
    assert results_has_critical_risk({"validation_summary": "Needs review"}, technique="ir") is True
    assert results_has_critical_risk({"validation_summary": "All checks passed"}, technique="ir") is False


def test_results_next_step_translation_key_prefers_input_mode_and_multi_sample():
    assert results_next_step_translation_key({}, mode="sequence", technique="saxs") == "RESULTS_SUMMARY_NEXT_SEQUENCE"
    assert results_next_step_translation_key({}, mode="directory", technique="saxs") == "RESULTS_SUMMARY_NEXT_DIRECTORY"
    assert results_next_step_translation_key(
        {"sample-a": {}, "sample-b": {}},
        mode="single",
        technique="ir",
    ) == "RESULTS_SUMMARY_NEXT_MULTI_SAMPLE"


def test_results_next_step_translation_key_handles_batch_risk_single_and_empty():
    assert results_next_step_translation_key(
        {"batch_frames": "2"},
        mode="single",
        technique="saxs",
    ) == "RESULTS_SUMMARY_NEXT_BATCH"
    assert results_next_step_translation_key(
        {},
        mode="single",
        technique="waxs",
        has_risk=True,
    ) == "RESULTS_SUMMARY_NEXT_WAXS_RISK"
    assert results_next_step_translation_key(
        {},
        mode="single",
        technique="dsc",
        has_risk=True,
    ) == "RESULTS_SUMMARY_NEXT_DSC_RISK"
    assert results_next_step_translation_key(
        {},
        mode="single",
        technique="saxs",
        has_risk=True,
    ) == "RESULTS_SUMMARY_NEXT_SAXS_RISK"
    assert results_next_step_translation_key({}, mode="single", technique="ir", has_result=True) == "RESULTS_SUMMARY_NEXT_SINGLE"
    assert results_next_step_translation_key({}, mode="single", technique="ir") == ""


def test_ordered_results_columns_prefers_known_columns_dedupes_and_keeps_unknown_order():
    assert ordered_results_columns(
        ["foo", "L_nm", "sample", "Foo", "bar", "temperature_C", "file", "foo"]
    ) == ["file", "sample", "temperature_C", "L_nm", "foo", "bar"]
    assert ordered_results_columns(["Xc_pct", "unknown", "D_Scherrer_nm"]) == [
        "Xc_pct",
        "D_Scherrer_nm",
        "unknown",
    ]


def test_measured_result_metric_parts_handles_dsc_and_default_keys():
    assert measured_result_metric_parts(
        {"Tg_C": "70", "Tm_peak_C": "220", "DHm_Jg": "45", "Xc_pct": "32", "extra": "ignored"},
        technique="dsc",
        params={},
        strain_snapshot={},
    ) == ["Tg_C=70", "Tm_peak_C=220", "DHm_Jg=45", "Xc_pct=32"]
    assert measured_result_metric_parts(
        {"r_squared": "0.98", "L_nm": "12", "quality_score": "0.8"},
        technique="ir",
        params={},
        strain_snapshot={},
    ) == ["r_squared=0.98", "L_nm=12", "quality_score=0.8"]


def test_measured_result_metric_parts_handles_saxs_strain_and_static_modes():
    strain_parts = measured_result_metric_parts(
        {
            "Q_star_rel_mean": "1.2",
            "phi_void_mean": "0.04",
            "f_Herman_mean": "0.7",
            "void_detected_frames": "3",
        },
        technique="saxs",
        params={},
        strain_snapshot={
            "active": True,
            "strain_reliability_status": "usable",
            "dominant_phase": "void",
            "paper_figure_candidate": True,
            "paper_conclusion_candidate": False,
        },
    )
    assert strain_parts[:4] == [
        "strain_reliability_status=usable",
        "dominant_phase=void",
        "paper_figure_candidate=true",
        "paper_conclusion_candidate=false",
    ]
    assert "invariant_Q_rel_mean=1.2" in strain_parts

    static_parts = measured_result_metric_parts(
        {"lc_nm": "13.5", "lc_reliability_status": "review"},
        technique="saxs",
        params={"lc_method": "peak", "calibrated_fallback_active": True},
        strain_snapshot={"active": False},
    )
    assert static_parts == [
        "lc_method=peak",
        "calibrated_fallback_active=True",
        "lc_nm=13.5",
        "lc_reliability_status=review",
    ]


def test_context_suggestion_spec_handles_data_slot_without_and_with_file():
    assert context_suggestion_spec("data", has_file=False) == {
        "title_key": "CONTEXT_HINT_DATA_TITLE",
        "detail_key": "CONTEXT_HINT_DATA_NEED_INPUT",
        "detail_args": (),
        "items": [
            {"text_key": "CONTEXT_HINT_ACTION_BROWSE_FILE", "action_key": "browse_file", "callback_key": "browse_file"},
            {"text_key": "CONTEXT_HINT_ACTION_BROWSE_FOLDER", "action_key": "browse_folder", "callback_key": "browse_folder"},
        ],
    }

    assert context_suggestion_spec("data", has_file=True, source_name="sample.csv", has_results=True) == {
        "title_key": "CONTEXT_HINT_DATA_TITLE",
        "detail_key": "CONTEXT_HINT_DATA_READY",
        "detail_args": ("sample.csv",),
        "items": [
            {"text_key": "CONTEXT_HINT_ACTION_OPEN_CONFIG", "action_key": "open_config", "callback_key": "open_config"},
            {"text_key": "CONTEXT_HINT_ACTION_OPEN_RESULTS", "action_key": "open_results", "callback_key": "open_results"},
        ],
    }


def test_context_suggestion_spec_handles_config_slot_branches():
    assert context_suggestion_spec("config", has_file=False)["items"] == [
        {"text_key": "CONTEXT_HINT_ACTION_BACK_TO_DATA", "action_key": "back_to_data", "callback_key": "back_to_data"},
        {"text_key": "CONTEXT_HINT_ACTION_OPEN_HISTORY", "action_key": "open_history", "callback_key": "open_history"},
    ]

    ai_tuned = context_suggestion_spec(
        "config",
        has_file=True,
        current_origin="controlled_optimization_rerun",
    )
    assert ai_tuned["detail_key"] == "CONTEXT_HINT_CONFIG_AI_TUNED"
    assert ai_tuned["items"] == [
        {"text_key": "CONTEXT_HINT_ACTION_REVIEW_AI_RESULT", "action_key": "review_ai_result", "callback_key": "review_ai_result"},
        {
            "text_key": "CONTEXT_HINT_ACTION_RUN_CONTROLLED_OPTIMIZATION",
            "action_key": "run_controlled_optimization",
            "callback_key": "run_controlled_optimization",
        },
    ]

    calibration = context_suggestion_spec(
        "config",
        has_file=True,
        technique="saxs",
        has_config=True,
        has_recent_calibration=True,
        calibration_scope_label="SAXS static",
        has_results=False,
    )
    assert calibration["detail_args"] == ("SAXS static",)
    assert calibration["items"] == [
        {
            "text_key": "CONTEXT_HINT_ACTION_APPLY_RECENT_CALIBRATION",
            "action_key": "recent_calibration",
            "callback_key": "apply_recent_calibration",
        },
        {"text_key": "CONTEXT_HINT_ACTION_OPEN_HISTORY", "action_key": "open_history", "callback_key": "open_history"},
    ]

    generic = context_suggestion_spec("config", has_file=True, technique="ir", has_results=True)
    assert generic["detail_key"] == "CONTEXT_HINT_CONFIG_GENERIC"
    assert generic["items"][1]["action_key"] == "open_results"
    assert context_suggestion_spec("unknown") is None


def test_workflow_task_context_spec_selects_title_detail_and_source():
    assert workflow_task_context_spec(
        tech="joint",
        input_mode="single",
        filepath="",
        is_dir=False,
        is_native_directory_context=False,
        ai_tuning_active=False,
        running=False,
        source_name="",
        mode_text="",
        no_data_text="No data",
    ) == {
        "title_key": "WORKFLOW_TASK_JOINT_TITLE",
        "detail_key": "WORKFLOW_TASK_JOINT_DETAIL",
        "status_key": "WORKFLOW_TASK_STATUS_JOINT",
        "source": "No data",
    }

    assert workflow_task_context_spec(
        tech="saxs",
        input_mode="sequence",
        filepath="D:/data",
        is_dir=True,
        is_native_directory_context=True,
        ai_tuning_active=False,
        running=False,
        source_name="data",
        mode_text="Sequence",
        no_data_text="No data",
    )["title_key"] == "WORKFLOW_TASK_SEQUENCE_TITLE"


def test_workflow_task_context_spec_status_priority_and_idle_single_modes():
    ai_spec = workflow_task_context_spec(
        tech="saxs",
        input_mode="single",
        filepath="D:/a.csv",
        is_dir=False,
        is_native_directory_context=False,
        ai_tuning_active=True,
        running=True,
        source_name="a.csv",
        mode_text="",
        no_data_text="No data",
    )
    assert ai_spec["title_key"] == "WORKFLOW_TASK_AI_TUNING_TITLE"
    assert ai_spec["status_key"] == "WORKFLOW_TASK_STATUS_RUNNING"
    assert ai_spec["source"] == "a.csv"

    single = workflow_task_context_spec(
        tech="ir",
        input_mode="single",
        filepath="D:/a.csv",
        is_dir=False,
        is_native_directory_context=False,
        ai_tuning_active=False,
        running=False,
        source_name="a.csv",
        mode_text="",
        no_data_text="No data",
    )
    assert single["title_key"] == "WORKFLOW_TASK_SINGLE_TITLE"
    assert single["status_key"] == "WORKFLOW_TASK_STATUS_SINGLE"

    idle = workflow_task_context_spec(
        tech="ir",
        input_mode="single",
        filepath="",
        is_dir=False,
        is_native_directory_context=False,
        ai_tuning_active=False,
        running=False,
        source_name="",
        mode_text="",
        no_data_text="No data",
    )
    assert idle["title_key"] == "WORKFLOW_TASK_IDLE_TITLE"
    assert idle["status_key"] == "WORKFLOW_TASK_STATUS_IDLE"


def test_workflow_task_tech_label_uses_special_labels_map_and_empty_text():
    assert workflow_task_tech_label("samples", technique_labels={}, no_tech_text="No tech") == "Samples"
    assert workflow_task_tech_label("joint", technique_labels={}, no_tech_text="No tech") == "Joint"
    assert workflow_task_tech_label("saxs", technique_labels={"saxs": "SAXS"}, no_tech_text="No tech") == "SAXS"
    assert workflow_task_tech_label("custom", technique_labels={}, no_tech_text="No tech") == "CUSTOM"
    assert workflow_task_tech_label("", technique_labels={}, no_tech_text="No tech") == "No tech"


def test_ai_tuning_change_summary_text_formats_first_three_and_remaining():
    assert ai_tuning_change_summary_text(
        {"a": 1, "b": {"x": 2}, "c": "", "d": 4},
        empty_text="N/A",
        display_text_fn=lambda value: f"<{value}>",
        more_text_fn=lambda remaining: f"+{remaining} more",
    ) == "a -> <1>; b -> <{'x': 2}>; c -> <>; +1 more"
    assert ai_tuning_change_summary_text({}, empty_text="N/A", display_text_fn=str, more_text_fn=str) == "N/A"


def test_ai_tuning_remaining_risks_text_dedupes_rejected_history():
    history = [
        {"accepted": True, "rollback_detail": "ignored"},
        {"accepted": False, "rollback_detail": "guard"},
        {"accepted": False, "rollback_detail": "guard", "llm_advice": {"rollback_reason": "axis"}},
        {"accepted": False, "llm_advice": {"rollback_reason": "support"}},
        {"accepted": False, "llm_advice": {"rollback_reason": "extra"}},
    ]

    assert ai_tuning_remaining_risks_text(history, empty_text="N/A") == "guard; axis; support"
    assert ai_tuning_remaining_risks_text([], empty_text="N/A") == "N/A"


def test_ai_tuning_stability_and_constraint_summary_parts_normalize_evidence():
    stability = ai_tuning_stability_summary_parts(
        {
            "stability_evidence": {
                "stability_score": 0.9,
                "parameter_stability_score": 0.8,
                "method_agreement_score": 0.7,
                "batch_continuity_score": 0.6,
                "stability_flags": [" drift ", "", "noise"],
            }
        },
        empty_text="N/A",
        format_score_fn=lambda value: f"{float(value):.1f}",
    )
    assert stability == ("0.9", "0.8", "0.7", "0.6", "drift, noise")
    assert ai_tuning_stability_summary_parts({}, empty_text="N/A", format_score_fn=str) is None

    constraint = ai_tuning_constraint_summary_parts(
        {
            "constraint_summary": {
                "status": "soft_warn",
                "triggered_counts": {"hard_fail": 1, "soft_warn": 2},
                "triggered_names": {"hard_fail": ["a"], "soft_warn": ["b", "a"], "evidence_only": ["c"]},
            }
        },
        empty_text="N/A",
        display_text_fn=lambda value: str(value).upper(),
    )
    assert constraint == ("SOFT_WARN", 1, 2, 0, "a, b, c")
    assert ai_tuning_constraint_summary_parts({}, empty_text="N/A", display_text_fn=str) is None


def test_batch_fallback_summary_parts_extracts_translation_parts():
    parts = batch_fallback_summary_parts(
        {
            "batch_evidence": {
                "batch_calibration_summary": {
                    "fallback_ratio": 0.25,
                    "raw_snapshot_rows": "7",
                    "calibrated_fallback_reason": "low support",
                    "calibration_skipped_reason": "missing axis",
                }
            }
        },
        symptom_names=[
            "temperature_calibration_fallback_active",
            "batch_summary_conflicts_with_frame_evidence",
            "thickness_chain_unreliable",
        ],
    )

    assert [(part.translation_key, part.args) for part in parts] == [
        ("RESULTS_REVIEW_FALLBACK_ACTIVE", ("25",)),
        ("RESULTS_REVIEW_FALLBACK_RAW", (7,)),
        ("RESULTS_REVIEW_FALLBACK_CONFLICT", ()),
        ("RESULTS_REVIEW_FALLBACK_THICKNESS", ()),
        ("RESULTS_REVIEW_FALLBACK_REASON", ("low support",)),
        ("RESULTS_REVIEW_FALLBACK_REASON", ("missing axis",)),
    ]


def test_batch_fallback_summary_parts_returns_empty_without_summary_or_fallback_symptom():
    assert batch_fallback_summary_parts({}, symptom_names=[]) == []
    assert batch_fallback_summary_parts({"batch_evidence": {"batch_calibration_summary": {}}}, symptom_names=[]) == []


def test_saxs_lc_status_summary_parts_prefers_batch_then_structure_then_params():
    assert saxs_lc_status_summary_parts(
        {},
        {
            "batch_evidence": {
                "batch_structure_summary": {
                    "dominant_lc_reliability_status": "review",
                    "dominant_lc_reliability_reason": "mixed",
                    "diagnostic_only_rows": "2",
                    "within_window_rows": "3",
                }
            }
        },
    ) == ("review", 2, 3, "mixed")

    assert saxs_lc_status_summary_parts(
        {},
        {
            "structure_evidence": {
                "lc_reliability_status": "diagnostic_only",
                "lc_reliability_reason": "weak peak",
                "melting_window_status": "within_window",
            }
        },
    ) == ("diagnostic_only", 1, 1, "weak peak")

    assert saxs_lc_status_summary_parts(
        {
            "batch_structure_summary": {"diagnostic_only_rows": 0, "within_window_rows": 2},
            "lc_reliability_status": "usable",
            "lc_reliability_reason": "stable",
        },
        {},
    ) == ("usable", 0, 2, "stable")


def test_saxs_lc_status_summary_parts_returns_none_without_status_or_counts():
    assert saxs_lc_status_summary_parts({}, {}) is None
    assert saxs_lc_status_summary_parts({"batch_structure_summary": {}}, {}) is None


def test_saxs_reason_text_maps_known_tokens_dedupes_and_falls_back():
    assert saxs_reason_text(
        "stable_structure_support|low_lc_confidence|low_lc_confidence|custom_reason",
        language="en",
    ) == "stable structure support, low lc confidence, custom reason"
    assert saxs_reason_text("stable_structure_support|within_melting_window", language="zh") == "结构支撑稳定, 位于熔融窗口内"
    assert saxs_reason_text("", language="en") == ""


def test_saxs_lc_status_text_maps_known_statuses_and_unknowns():
    assert saxs_lc_status_text("usable", language="en") == "usable"
    assert saxs_lc_status_text("low_confidence", language="en") == "low-confidence"
    assert saxs_lc_status_text("diagnostic_only", language="zh") == "仅作诊断"
    assert saxs_lc_status_text("custom_status", language="en") == "custom-status"
    assert saxs_lc_status_text("", language="zh") == ""


def test_saxs_structure_status_snapshot_prefers_batch_summary_and_counts_rows():
    snapshot = saxs_structure_status_snapshot(
        {"batch_frames": 9},
        {
            "batch_evidence": {
                "batch_structure_summary": {
                    "batch_rows": 4,
                    "dominant_lc_reliability_status": "usable",
                    "dominant_lc_reliability_reason": "stable",
                    "dominant_melting_window_status": "within_window",
                    "dominant_melting_window_reason": "ok",
                    "diagnostic_only_rows": 1,
                    "low_confidence_rows": 2,
                    "usable_rows": 3,
                    "within_window_rows": 4,
                }
            }
        },
        symptom_names=["a", "b"],
    )

    assert snapshot["batch_rows"] == 4
    assert snapshot["lc_reliability_status"] == "usable"
    assert snapshot["melting_window_status"] == "within_window"
    assert snapshot["diagnostic_only_rows"] == 1
    assert snapshot["symptoms"] == ["a", "b"]


def test_saxs_structure_status_snapshot_falls_back_to_structure_params_and_infers_rows():
    structure_snapshot = saxs_structure_status_snapshot(
        {},
        {
            "structure_evidence": {
                "lc_reliability_status": "diagnostic_only",
                "lc_reliability_reason": "weak",
                "melting_window_status": "near_onset",
                "melting_window_reason": "near",
            }
        },
        symptom_names=[],
    )
    assert structure_snapshot["batch_rows"] == 1
    assert structure_snapshot["lc_reliability_status"] == "diagnostic_only"
    assert structure_snapshot["melting_window_reason"] == "near"

    params_snapshot = saxs_structure_status_snapshot(
        {
            "batch_structure_summary": {"low_confidence_rows": 2, "near_onset_rows": 3},
            "lc_reliability_status": "low_confidence",
            "melting_window_status": "near_onset",
        },
        {},
        symptom_names=[],
    )
    assert params_snapshot["batch_rows"] == 5
    assert params_snapshot["low_confidence_rows"] == 2
    assert params_snapshot["near_onset_rows"] == 3


def test_saxs_strain_evidence_snapshot_prefers_feature_evidence_and_sorts_symptoms():
    snapshot = saxs_strain_evidence_snapshot(
        {"condition_label": "ignored"},
        {
            "feature_evidence": {
                "condition_evidence": {
                    "condition_label": "Strain",
                    "strain_axis_confidence": "0.88",
                    "strain_monotonic": True,
                    "strain_missing_count": 1,
                    "strain_duplicate_count": 2,
                    "strain_min_pct": "0.5",
                    "strain_max_pct": "3.5",
                },
                "strain_structure_evidence": {
                    "Q_star_rel_mean": "0.1234",
                    "Q_star_rel_span": "0.0100",
                    "phi_void_mean": 0.2,
                    "phi_void_span": 0.03,
                    "void_detected_frames": 4,
                    "f_Herman_mean": 0.6,
                    "f_Herman_span": 0.2,
                    "porod_slope_mean": 1.5,
                    "porod_slope_span": 0.4,
                    "dominant_phase": "Lamellar",
                    "strain_reliability_status": "Low_Confidence",
                    "strain_reliability_reason": "weak",
                    "paper_figure_candidate": 1,
                    "paper_conclusion_candidate": 0,
                    "phase_support_mean": "0.9",
                    "phase_support_span": "0.1",
                },
            }
        },
        symptom_names=["orientation_shift_breaks_lamellar_comparison", "low_q_void_dominant", "low_q_void_dominant", "  "],
    )

    assert snapshot["active"] is True
    assert snapshot["condition_label"] == "strain"
    assert snapshot["strain_axis_confidence"] == 0.88
    assert snapshot["invariant_Q_rel_mean"] == 0.1234
    assert snapshot["strain_reliability_status"] == "low_confidence"
    assert snapshot["paper_figure_candidate"] is True
    assert snapshot["paper_conclusion_candidate"] is False
    assert snapshot["symptoms"] == ["low_q_void_dominant", "orientation_shift_breaks_lamellar_comparison"]


def test_saxs_strain_evidence_snapshot_uses_params_fallback_and_active_detection():
    snapshot = saxs_strain_evidence_snapshot(
        {
            "condition_label": "Stretch",
            "strain_structure_evidence": {
                "Q_star_rel_mean": 0.2,
                "void_detected_frames": 2,
            },
        },
        {},
        symptom_names=[],
    )

    assert snapshot["active"] is True
    assert snapshot["condition_label"] == "stretch"
    assert snapshot["invariant_Q_rel_mean"] == 0.2
    assert snapshot["void_detected_frames"] == 2


def test_saxs_strain_summary_text_and_followup_helpers_format_active_snapshots():
    params = {
        "condition_label": "strain",
        "strain_structure_evidence": {
            "Q_star_rel_mean": 0.1234,
            "Q_star_rel_span": 0.01,
            "phi_void_mean": 0.2,
            "phi_void_span": 0.03,
            "void_detected_frames": 4,
            "f_Herman_mean": 0.6,
            "f_Herman_span": 0.2,
            "porod_slope_mean": 1.5,
            "porod_slope_span": 0.4,
            "strain_reliability_status": "low_confidence",
        },
    }
    evidence = {
        "feature_evidence": {
            "condition_evidence": {
                "condition_label": "strain",
                "strain_axis_confidence": 0.88,
                "strain_monotonic": True,
                "strain_missing_count": 1,
                "strain_duplicate_count": 2,
                "strain_min_pct": 0.5,
                "strain_max_pct": 3.5,
            },
        }
    }
    symptoms = ["low_q_void_dominant", "orientation_shift_breaks_lamellar_comparison"]

    summary_text = saxs_strain_summary_text(params, evidence, symptom_names=symptoms, language="en")
    risk_text = saxs_strain_risk_summary_text(params, evidence, symptom_names=symptoms, language="en")
    next_step_text = saxs_strain_next_step_text(params, evidence, symptom_names=symptoms, language="en")

    assert "strain axis=" in summary_text
    assert "structure=" in summary_text
    assert "main issues=" in summary_text
    assert "low-q / void dominant" in summary_text
    assert risk_text == "Risk note | tensile SAXS status=low_confidence, so keep the result in diagnostic framing until the chain stabilizes"
    assert next_step_text == "Next step | align the strain axis, low-q coverage, void evidence, and long-period anchor before deciding whether to tune again"


def test_result_mask_summary_text_handles_saxs_mask_and_beamstop_flags():
    result = SimpleNamespace(mask_truncated=True, beam_stop_contaminated=True, effective_q_min="0.1234")

    assert result_mask_summary_text(result, current_technique="saxs", language="en") == tr(
        "RESULTS_SUMMARY_MASK_TRUNCATED_AND_BEAMSTOP",
        "0.123",
    )
    assert result_mask_summary_text(result, current_technique="waxs", language="en") == ""


def test_history_context_snapshot_normalizes_summaries_and_context_fields():
    tuning_context = {
        "benchmark_summary": {"average_objective_delta": 0.018},
        "benchmark_text": " Benchmark ",
        "tuning_goal": "risk",
        "tuning_goal_label": " Risk focused ",
        "stop_reason": " converged ",
        "remaining_risks": " edge cases ",
        "next_goal": " review ",
    }
    joint_context = {"summary": " Joint summary ", "issue_count": 2}

    snapshot = history_context_snapshot(
        review_summary=" Review ",
        work_memory_summary=" Memory ",
        comparison_summary=" Compare ",
        validation_summary=" Valid ",
        responsibility_boundary=" Boundary ",
        tuning_context=tuning_context,
        joint_context=joint_context,
    )

    assert snapshot == {
        "review_summary": "Review",
        "work_memory_summary": "Memory",
        "comparison_summary": "Compare",
        "validation_summary": "Valid",
        "responsibility_boundary": "Boundary",
        "benchmark_summary": {"average_objective_delta": 0.018},
        "benchmark_text": "Benchmark",
        "tuning_goal": "risk",
        "tuning_goal_label": "Risk focused",
        "stop_reason": "converged",
        "remaining_risks": "edge cases",
        "next_goal": "review",
        "tuning_context": tuning_context,
        "joint_ai_context": joint_context,
        "joint_summary": "Joint summary",
    }


def test_history_context_snapshot_uses_empty_dicts_for_invalid_contexts():
    snapshot = history_context_snapshot(
        review_summary=None,
        work_memory_summary="",
        comparison_summary="",
        validation_summary="",
        responsibility_boundary="",
        tuning_context=["bad"],
        joint_context=None,
    )

    assert snapshot["tuning_context"] == {}
    assert snapshot["joint_ai_context"] == {}
    assert snapshot["benchmark_summary"] == {}
    assert snapshot["joint_summary"] == ""


def test_build_history_context_snapshot_from_window_uses_window_state():
    class _FakeHistoryWindow:
        _last_ai_tuning_context = {
            "benchmark_summary": {"average_objective_delta": 0.018},
            "benchmark_text": " Benchmark ",
            "tuning_goal": "risk",
            "tuning_goal_label": " Risk focused ",
            "stop_reason": " converged ",
            "remaining_risks": " edge cases ",
            "next_goal": " review ",
        }

        def _current_results_record(self):
            return {"results_summary": {"validation_summary": "Validation note"}}

        def _joint_ai_context(self):
            return {"summary": "Joint summary"}

        def _result_review_summary(self):
            return "Review summary"

        def _work_memory_summary(self):
            return "Memory summary"

        def _result_comparison_summary(self):
            return "Comparison summary"

        def _history_validation_summary(self, current):
            return "Validation note"

        def _responsibility_boundary_summary(self):
            return "Boundary summary"

    snapshot = build_history_context_snapshot_from_window(_FakeHistoryWindow())

    assert snapshot == {
        "review_summary": "Review summary",
        "work_memory_summary": "Memory summary",
        "comparison_summary": "Comparison summary",
        "validation_summary": "Validation note",
        "responsibility_boundary": "Boundary summary",
        "benchmark_summary": {"average_objective_delta": 0.018},
        "benchmark_text": "Benchmark",
        "tuning_goal": "risk",
        "tuning_goal_label": "Risk focused",
        "stop_reason": "converged",
        "remaining_risks": "edge cases",
        "next_goal": "review",
        "tuning_context": _FakeHistoryWindow._last_ai_tuning_context,
        "joint_ai_context": {"summary": "Joint summary"},
        "joint_summary": "Joint summary",
    }


def test_joint_ai_context_prefers_existing_contexts_in_priority_order():
    report_context = {"summary": "report context"}
    tuning_context = {"joint_ai_context": {"summary": "tuning context"}}
    history_context = {"joint_ai_context": {"summary": "history context"}}

    assert joint_ai_context(
        {"ai_context": report_context, "rows": [{"sample": "ignored"}]},
        tuning_context=tuning_context,
        history_context=history_context,
    ) is report_context
    assert joint_ai_context(
        {"rows": [{"sample": "ignored"}]},
        tuning_context=tuning_context,
        history_context=history_context,
    ) == {"summary": "tuning context"}
    assert joint_ai_context(
        {"rows": [{"sample": "ignored"}]},
        tuning_context={},
        history_context=history_context,
    ) == {"summary": "history context"}


def test_joint_ai_context_returns_empty_without_report_content():
    assert joint_ai_context(None, tuning_context={}, history_context={}) == {}
    assert joint_ai_context({"rows": "bad", "validations": "bad"}) == {}


def test_joint_ai_context_builds_no_issue_summary_with_translated_labels():
    context = joint_ai_context(
        {
            "rows": [{"sample": "PA6", "batch": "b1"}, {"sample": "PET", "batch": "b2"}],
            "validations": [{"severity": "INFO", "check": "ok"}],
        },
        no_issue_summary="No joint issues",
        joint_scope_label="Joint analysis",
    )

    assert context == {
        "summary": "No joint issues",
        "scope": "Joint analysis",
        "sample_count": 2,
        "batch_count": 2,
        "issue_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "issue_families": [],
        "highlights": [],
        "samples": [],
        "batches": [],
        "row_count": 2,
        "ai_boundary": {
            "mode": "off",
            "provider_status": "not_configured",
            "fallback": "rule_based_report",
            "failure_policy": "preserve_source_evidence_and_diagnostic_status",
        },
    }


def test_joint_ai_context_summarizes_issue_families_highlights_and_counts():
    context = joint_ai_context(
        {
            "rows": [
                {"sample": "PA6", "batch": "batch-a"},
                {"sample": "PA6", "batch": "batch-b"},
                {"sample": "PET", "batch": "batch-c"},
                {"sample": "PBT", "batch": "batch-d"},
            ],
            "validations": [
                {
                    "severity": "ERROR",
                    "sample": "PA6",
                    "batch": "batch-a",
                    "check": "saxs/phi_c_delta",
                    "message": "phi mismatch",
                },
                {
                    "severity": "WARN",
                    "sample": "PET",
                    "batch": "batch-c",
                    "check": "dsc/tm_gt_tc",
                    "message": "gap large",
                },
                {
                    "severity": "WARN",
                    "sample": "PBT",
                    "batch": "batch-d",
                    "check": "waxs/l_consistency",
                    "message": "unstable",
                },
                {
                    "severity": "INFO",
                    "sample": "ignored",
                    "check": "ignored",
                    "message": "ok",
                },
            ],
        }
    )

    assert context["scope"] == "PA6 / PET"
    assert context["sample_count"] == 3
    assert context["batch_count"] == 4
    assert context["issue_count"] == 3
    assert context["warning_count"] == 2
    assert context["error_count"] == 1
    assert context["issue_families"] == [
        "phi_c inconsistency",
        "Tm bidirectional gap",
        "L consistency unstable",
    ]
    assert context["samples"] == ["PA6", "PET", "PBT"]
    assert context["batches"] == ["batch-a", "batch-b", "batch-c"]
    assert context["row_count"] == 4
    assert context["ai_boundary"] == {
        "mode": "off",
        "provider_status": "not_configured",
        "fallback": "rule_based_report",
        "failure_policy": "preserve_source_evidence_and_diagnostic_status",
    }
    assert context["highlights"] == [
        "ERROR · PA6 / batch-a · phi_c_delta · phi mismatch",
        "WARN · PET / batch-c · tm_gt_tc · gap large",
        "WARN · PBT / batch-d · l_consistency · unstable",
    ]
    assert context["summary"].startswith("Cross-tech consistency for PA6 / PET: 1 errors, 2 warnings")
    assert "focus on phi_c inconsistency, Tm bidirectional gap, L consistency unstable" in context["summary"]
    assert "example ERROR · PA6 / batch-a · phi_c_delta · phi mismatch" in context["summary"]


def test_joint_ai_reminder_parts_focuses_unique_family_labels():
    parts = joint_ai_reminder_parts(
        {
            "issue_count": "4",
            "issue_families": ["phi_c inconsistency", "phi_c inconsistency", "Tm bidirectional gap"],
        },
        family_label_fn=lambda family: {
            "phi_c inconsistency": "Phi",
            "Tm bidirectional gap": "Tm",
        }.get(family, ""),
        separator="、",
    )

    assert parts.translation_key == "JOINT_REMINDER_FOCUS"
    assert parts.args == ("Phi、Tm",)


def test_joint_ai_reminder_parts_uses_generic_for_issues_without_family_labels():
    assert joint_ai_reminder_parts(
        {"issue_count": 1, "issue_families": ["unknown"]},
        family_label_fn=lambda family: "",
    ).translation_key == "JOINT_REMINDER_GENERIC"
    assert joint_ai_reminder_parts({"issue_count": 0}, family_label_fn=lambda family: "") is None
    assert joint_ai_reminder_parts(None, family_label_fn=lambda family: "") is None


def test_joint_compare_hint_parts_uses_family_or_generic_prompt():
    family_parts = joint_compare_hint_parts(
        {"issue_count": 2, "issue_families": ["phi_c inconsistency", "cross-tech issue"]},
        family_label_fn=lambda family: family.upper(),
        separator=", ",
    )

    assert family_parts.translation_key == "JOINT_COMPARE_HINT_FAMILIES"
    assert family_parts.args == ("PHI_C INCONSISTENCY, CROSS-TECH ISSUE",)
    assert joint_compare_hint_parts(
        {"issue_count": 2, "issue_families": []},
        family_label_fn=lambda family: "",
    ).translation_key == "JOINT_COMPARE_HINT_GENERIC"
    assert joint_compare_hint_parts({"issue_count": "bad"}, family_label_fn=lambda family: "") is None


def test_history_context_line_parts_prefer_snapshot_order_and_marks_review_chain():
    tuning_context = {"history": [{"round_num": 1, "accepted": True}]}
    record = {
        "results_summary": {
            "history_context": {
                "review_summary": "Review",
                "comparison_summary": "Compare",
                "validation_summary": "Valid",
                "benchmark_text": "Benchmark",
                "work_memory_summary": "Memory",
                "joint_summary": "Joint",
                "responsibility_boundary": "Boundary",
                "tuning_context": tuning_context,
            }
        }
    }

    parts = history_context_line_parts(
        record,
        validation_summary="fallback valid",
        origin_label="manual",
        boundary_text="fallback boundary",
        chain_summary_fn=lambda context: "Chain" if context is tuning_context else "",
    )

    assert [(part.kind, part.text) for part in parts] == [
        ("plain", "Review"),
        ("plain", "Compare"),
        ("plain", "Valid"),
        ("plain", "Benchmark"),
        ("plain", "Memory"),
        ("plain", "Joint"),
        ("plain", "Boundary"),
        ("review_chain", "Chain"),
    ]


def test_history_context_line_parts_falls_back_for_ai_tuned_records_and_dedupes_boundary():
    parts = history_context_line_parts(
        {"results_summary": {"ai_tuned": True, "history_context": {}}},
        validation_summary="Valid",
        origin_label="AI rerun",
        boundary_text="Valid",
        chain_summary_fn=lambda context: "",
    )

    assert [(part.kind, part.text) for part in parts] == [
        ("plain", "Valid"),
        ("plain", "AI rerun"),
        ("review_chain", "AI rerun"),
    ]


def test_history_summary_lines_combines_fields_and_dedupes_context_entries():
    record = {
        "technique": "saxs",
        "created_at": "2026-07-09 10:11:12",
    }

    lines = history_summary_lines(
        record,
        technique_text_fn=lambda technique: technique.upper(),
        context_text_fn=lambda item: "Batch A",
        timestamp_text_fn=lambda value: "2026-07-09 10:11",
        metrics_text_fn=lambda item: "L_nm=12.0",
        context_lines_fn=lambda item: ["Batch A", "review summary", "L_nm=12.0"],
    )

    assert lines == [
        "SAXS",
        "Batch A",
        "2026-07-09 10:11",
        "review summary",
        "L_nm=12.0",
    ]


def test_history_has_available_source_uses_data_file_when_present(tmp_path):
    data_file = tmp_path / "sample.csv"
    record = {"results_summary": {"data_file": str(data_file)}}

    assert history_has_available_source(record) is False

    data_file.write_text("x,y\n1,2\n", encoding="utf-8")

    assert history_has_available_source(record) is True
    assert history_has_available_source({"results_summary": {}}) is True
    assert history_has_available_source(None) is False


def test_history_export_rows_appends_persistence_metadata():
    headers = ["Time", "Technique"]
    matrix = [["2026-07-06 10:00", "SAXS"], ["2026-07-06 11:00", "WAXS"]]
    cache = [
        {
            "results_summary": {
                "ai_tuned": True,
                "data_file": "D:/data/a.csv",
                "result_origin": "controlled_optimization_rerun",
            },
            "output_dir": "D:/out/a",
        },
        {
            "results_summary": {},
            "output_dir": "D:/out/b",
        },
    ]

    export_headers, rows = history_export_rows(
        headers,
        matrix,
        cache,
        origin_label_fn=lambda record: "AI rerun" if record["results_summary"].get("result_origin") else "",
    )

    assert export_headers == [
        "Time",
        "Technique",
        "Result origin",
        "AI tuned",
        "Source data",
        "Output dir",
    ]
    assert rows == [
        ["2026-07-06 10:00", "SAXS", "AI rerun", "Yes", "D:/data/a.csv", "D:/out/a"],
        ["2026-07-06 11:00", "WAXS", "", "No", "", "D:/out/b"],
    ]


def test_history_export_rows_returns_empty_without_table_data():
    assert history_export_rows([], [["value"]], [], origin_label_fn=lambda record: "") == ([], [])
    assert history_export_rows(["Header"], [], [], origin_label_fn=lambda record: "") == ([], [])
