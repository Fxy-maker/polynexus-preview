import json

from polynexus.gui.i18n import get_language, set_language, tr
from polynexus.gui.export_context_service import (
    create_export_bundle_dirs,
    build_export_context_payload,
    copy_export_bundle_sections,
    export_manifest_payload,
    export_primary_report,
    export_readme_text,
    export_relative_report_path,
    export_recommended_reading_order,
    export_review_priority,
    write_export_manifest,
    write_export_readme,
    task_type_label,
    compose_joint_export_detail,
)


class _FakeWindow:
    def __init__(self):
        self._current_technique = "ir"
        self._current_submodule_id = "ir.temperature_2d"
        self._current_input_mode = "single"
        self._current_filepath = r"D:\data\sample.csv"
        self._current_result_confirmed_flag = True

    def _current_results_record(self):
        return {"results_summary": {"validation_summary": "Validation summary"}}

    def _current_result_tuning_context(self, current=None):
        return {"benchmark_text": "Benchmark: objective delta +0.018"}

    def _joint_ai_context(self):
        return {"summary": "Cross-tech consistency for PA6"}

    def _history_context_snapshot(self, tuning_context=None, joint_context=None):
        return {
            "benchmark_text": "Benchmark: objective delta +0.018",
            "joint_summary": "Cross-tech consistency for PA6",
            "tuning_context": tuning_context if isinstance(tuning_context, dict) else {},
            "joint_ai_context": joint_context if isinstance(joint_context, dict) else {},
        }

    def _current_result_origin(self):
        return "controlled_optimization_rerun"

    def _result_origin_label(self, origin):
        return "Recommended-parameter rerun"

    def _history_technique_text(self, technique):
        return "IR"

    def _history_submodule_text(self, submodule):
        return "Temperature 2D"

    def _result_comparison_summary(self):
        return "Current: run-a"

    def _history_validation_summary(self, record):
        return "Validation summary"

    def _ai_tuning_chain_snapshot(self, tuning_context=None):
        return "Run trace | accepted 1 rounds"

    def _current_analysis_evidence(self):
        return {"feature_evidence": {"sequence_evidence": {}}}

    def _result_review_summary(self):
        return "Review summary"

    def _work_memory_summary(self):
        return "Work memory summary"

    def _responsibility_boundary_summary(self):
        return "Boundary summary"


def test_task_type_label_maps_known_input_modes():
    assert task_type_label("single") == "Single-file analysis"
    assert task_type_label("batch") == "Batch analysis"
    assert task_type_label("directory") == "Directory analysis"
    assert task_type_label("multi_sample") == "Multi-sample analysis"
    assert task_type_label("joint") == "Joint analysis"
    assert task_type_label("unknown") == "Analysis run"


def test_create_export_bundle_dirs_creates_standard_directories(tmp_path):
    dirs = create_export_bundle_dirs(tmp_path / "PolyNexus_Export")

    assert dirs == {
        "figures": tmp_path / "PolyNexus_Export" / "figures",
        "data": tmp_path / "PolyNexus_Export" / "data",
        "report": tmp_path / "PolyNexus_Export" / "report",
        "metadata": tmp_path / "PolyNexus_Export" / "metadata",
    }
    assert all(path.is_dir() for path in dirs.values())


def test_export_primary_report_is_relative_to_report_directory():
    assert export_primary_report("D:/out/report/polynexus_report.html") == "report/polynexus_report.html"
    assert export_primary_report("") == ""


def test_export_relative_report_path_prefers_path_relative_to_bundle_root(tmp_path):
    bundle = tmp_path / "PolyNexus_Export"
    report = bundle / "report" / "polynexus_report.html"

    assert export_relative_report_path(str(report), str(bundle)) == "report\\polynexus_report.html"
    assert export_relative_report_path("", str(bundle)) == ""


def test_export_review_priority_depends_on_result_origin():
    assert export_review_priority("controlled_optimization_rerun") == [
        "report/",
        "metadata/export_manifest.json",
        "data/",
    ]
    assert export_review_priority("manual_run") == [
        "report/",
        "data/",
        "metadata/export_manifest.json",
    ]


def test_export_recommended_reading_order_starts_with_primary_report_or_default():
    assert export_recommended_reading_order("report/polynexus_report.html") == [
        "report/polynexus_report.html",
        "metadata/export_manifest.json",
        "data/",
    ]
    assert export_recommended_reading_order("") == [
        "report/ (no HTML report generated)",
        "metadata/export_manifest.json",
        "data/",
    ]


def test_compose_joint_export_detail_joins_nonempty_parts():
    assert compose_joint_export_detail(
        joint_summary="Cross-tech consistency for PA6",
        joint_reminder="Review phi_c inconsistency",
        joint_compare_hint="Compare SAXS and WAXS first",
    ) == "Cross-tech consistency for PA6 | Review phi_c inconsistency | Compare SAXS and WAXS first"
    assert compose_joint_export_detail(joint_summary="", joint_reminder="", joint_compare_hint="") == ""


def test_export_readme_text_renders_review_and_order_sections():
    text = export_readme_text(
        project_name="PA6",
        generated_at="2026-07-06 12:00:00",
        techniques="SAXS",
        source_data_path="D:/data/sample.dat",
        primary_report="report/polynexus_report.html",
        export_context={
            "task_type": "Single-file analysis",
            "technique_label": "SAXS",
            "submodule_label": "Static SAXS",
            "input_mode": "single",
            "confirmed_result": True,
            "result_origin_label": "Recommended-parameter rerun",
            "decision_owner_label": "User",
            "used_controlled_optimization": True,
            "comparison_summary": "Current: run-a",
            "review_summary": "Measured: L=12",
            "validation_chain": "chain text",
            "responsibility_boundary": "Boundary",
            "work_memory_summary": "Current result: run-a",
            "review_priority": ["report/", "metadata/export_manifest.json", "data/"],
            "recommended_reading_order": ["report/polynexus_report.html", "metadata/export_manifest.json", "data/"],
        },
        joint_detail="Cross-tech consistency for PA6",
        confirmed_review_label="Confirmed reference",
    )

    assert "PolyNexus Export Package" in text
    assert "Project: PA6" in text
    assert "Result origin: Recommended-parameter rerun" in text
    assert "Review summary: Confirmed reference | Measured: L=12" in text
    assert "Joint summary: Cross-tech consistency for PA6" in text
    assert "Review priority:" in text
    assert "1. report/polynexus_report.html" in text


def test_export_readme_text_uses_defaults_for_missing_optional_values():
    text = export_readme_text(
        project_name="",
        generated_at="2026-07-06 12:00:00",
        techniques="",
        source_data_path="",
        primary_report="",
        export_context={},
        joint_detail="",
        confirmed_review_label="Confirmed reference",
    )

    assert "Project: Unnamed" in text
    assert "Techniques: None" in text
    assert "Source data: -" in text
    assert "Validation chain: -" in text
    assert "Joint summary: -" in text
    assert "Open first: report/ (no HTML report generated)" in text


def test_export_manifest_payload_builds_stable_metadata_shape():
    payload = export_manifest_payload(
        project_name="PA6",
        exported_at="2026-07-06T12:00:00",
        bundle_root="D:/bundle",
        source_output_dir="D:/out",
        source_data_path="D:/data/sample.dat",
        current_technique="saxs",
        current_submodule="saxs.static",
        input_mode="single",
        included_techniques=["waxs", "saxs"],
        copied_sections=["figures", "data"],
        primary_report="report/polynexus_report.html",
        task_context={"task_type": "Single-file analysis"},
    )

    assert payload == {
        "project_name": "PA6",
        "exported_at": "2026-07-06T12:00:00",
        "bundle_root": "D:/bundle",
        "source_output_dir": "D:/out",
        "source_data_path": "D:/data/sample.dat",
        "current_technique": "saxs",
        "current_submodule": "saxs.static",
        "input_mode": "single",
        "included_techniques": ["saxs", "waxs"],
        "copied_sections": ["figures", "data"],
        "directories": {
            "figures": "figures",
            "data": "data",
            "report": "report",
            "metadata": "metadata",
            "figure_runs": "metadata/runs",
            "active_figure_run": "metadata/active_run.json",
        },
        "primary_report": "report/polynexus_report.html",
        "task_context": {"task_type": "Single-file analysis"},
    }


def test_write_export_manifest_writes_manifest_json_to_metadata_directory(tmp_path):
    manifest_path = write_export_manifest(
        tmp_path / "PolyNexus_Export",
        project_name="PA6",
        exported_at="2026-07-06T12:00:00",
        bundle_root="D:/bundle",
        source_output_dir="D:/out",
        source_data_path="D:/data/sample.dat",
        current_technique="saxs",
        current_submodule="saxs.static",
        input_mode="single",
        included_techniques=["waxs", "saxs"],
        copied_sections=["figures", "data"],
        primary_report="report/polynexus_report.html",
        task_context={"task_type": "Single-file analysis"},
    )

    assert manifest_path == tmp_path / "PolyNexus_Export" / "metadata" / "export_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["project_name"] == "PA6"
    assert payload["task_context"] == {"task_type": "Single-file analysis"}


def test_write_export_readme_writes_readme_txt_to_bundle_root(tmp_path):
    readme_path = write_export_readme(
        tmp_path / "PolyNexus_Export",
        project_name="PA6",
        generated_at="2026-07-06 12:00:00",
        techniques="SAXS",
        source_data_path="D:/data/sample.dat",
        primary_report="report/polynexus_report.html",
        export_context={
            "task_type": "Single-file analysis",
            "technique_label": "SAXS",
            "submodule_label": "Static SAXS",
            "input_mode": "single",
            "confirmed_result": True,
            "result_origin_label": "Recommended-parameter rerun",
            "decision_owner_label": "User",
            "used_controlled_optimization": True,
            "comparison_summary": "Current: run-a",
            "review_summary": "Measured: L=12",
            "validation_chain": "chain text",
            "responsibility_boundary": "Boundary",
            "work_memory_summary": "Current result: run-a",
            "review_priority": ["report/", "metadata/export_manifest.json", "data/"],
            "recommended_reading_order": ["report/polynexus_report.html", "metadata/export_manifest.json", "data/"],
        },
        joint_detail="Cross-tech consistency for PA6",
        confirmed_review_label="Confirmed reference",
    )

    assert readme_path == tmp_path / "PolyNexus_Export" / "README.txt"
    text = readme_path.read_text(encoding="utf-8")
    assert "PolyNexus Export Package" in text
    assert "Project: PA6" in text
    assert "Joint summary: Cross-tech consistency for PA6" in text


def test_build_export_context_payload_packages_current_export_state():
    previous = get_language()
    set_language("en")
    try:
        window = _FakeWindow()
        payload = build_export_context_payload(
            window,
            report_path=r"D:\bundle\report\polynexus_report.html",
            ir_summary_fn=lambda evidence: ["IR summary", "2D temperature evidence"],
        )

        assert payload["task_type"] == "Single-file analysis"
        assert payload["technique_id"] == "ir"
        assert payload["technique_label"] == "IR"
        assert payload["submodule_label"] == "Temperature 2D"
        assert payload["result_origin"] == "controlled_optimization_rerun"
        assert payload["result_origin_label"] == "Recommended-parameter rerun"
        assert payload["used_controlled_optimization"] is True
        assert payload["decision_owner_label"] == tr("EXPORT_DECISION_OWNER_USER")
        assert payload["review_priority"] == [
            "report/",
            "metadata/export_manifest.json",
            "data/",
        ]
        assert payload["recommended_reading_order"] == [
            "report/polynexus_report.html",
            "metadata/export_manifest.json",
            "data/",
        ]
        assert payload["comparison_summary"] == "Current: run-a"
        assert payload["review_summary"].startswith("IR summary | 2D temperature evidence | Review summary")
        assert payload["validation_summary"] == "Validation summary"
        assert payload["validation_chain"] == "Benchmark: objective delta +0.018 | Run trace | accepted 1 rounds"
        assert payload["benchmark_text"] == "Benchmark: objective delta +0.018"
        assert payload["joint_summary"] == "Cross-tech consistency for PA6"
        assert payload["history_context"]["joint_summary"] == "Cross-tech consistency for PA6"
        assert payload["work_memory_summary"] == "Work memory summary"
        assert payload["responsibility_boundary"] == "Boundary summary"
        assert payload["paper_figure_status"] == "IR summary | 2D temperature evidence"
        assert payload["scientific_review"]["status"] == "not_applicable"
        assert "not_applicable" in payload["scientific_review_text"]
    finally:
        set_language(previous)


def test_export_context_carries_structured_scientific_review_and_readme_text():
    window = _FakeWindow()
    window._current_submodule_id = "ir.mapping"
    window._history_submodule_text = lambda submodule: "Mapping"
    window._current_analysis_evidence = lambda: {
        "feature_evidence": {
            "mapping_evidence": {
                "scientific_review": {
                    "allowed": True,
                    "reason": "review_accepted",
                    "record_id": "review-ir-map-1",
                    "scope": "ir.mapping",
                    "source_ref": "map-a.json",
                }
            }
        }
    }

    context = build_export_context_payload(window)

    assert context["scientific_review"]["status"] == "accepted"
    assert context["scientific_review"]["record_id"] == "review-ir-map-1"
    assert "review_accepted" in context["scientific_review_text"]

    text = export_readme_text(
        project_name="PA6",
        generated_at="2026-07-06 12:00:00",
        techniques="IR",
        source_data_path="D:/data/map-a.json",
        primary_report="",
        export_context=context,
        joint_detail="",
        confirmed_review_label="Confirmed reference",
    )
    assert "Scientific review:" in text
    assert "review-ir-map-1" in text


def test_export_context_carries_project_release_provenance():
    window = _FakeWindow()
    window._current_analysis_evidence = lambda: {
        "scientific_release": {
            "allowed": True,
            "reason": "review_accepted",
            "record_id": "release-1",
            "scope": "release",
            "source_ref": "joint-run",
            "policy_version": "release-v1",
        }
    }

    context = build_export_context_payload(window)

    assert context["scientific_release"]["status"] == "accepted"
    assert context["scientific_release"]["record_id"] == "release-1"
    assert "release-1" in context["scientific_release_text"]

    text = export_readme_text(
        project_name="PA6",
        generated_at="2026-07-30 12:00:00",
        techniques="Joint",
        source_data_path="D:/data/joint-run",
        primary_report="",
        export_context=context,
        joint_detail="",
        confirmed_review_label="Confirmed reference",
    )
    assert "Scientific release:" in text
    assert "release-1" in text


def test_copy_export_bundle_sections_copies_available_sections(tmp_path):
    source = tmp_path / "source"
    figures = source / "figures"
    data = source / "data"
    report = source / "report"
    metadata = source / "metadata"
    run_manifest = source / "runs" / "joint-run-1" / "figure_manifest.json"
    active_run = source / "active_run.json"
    figures.mkdir(parents=True)
    data.mkdir()
    report.mkdir()
    metadata.mkdir()
    run_manifest.parent.mkdir(parents=True)
    (figures / "Fig-1.png").write_text("figure", encoding="utf-8")
    (data / "results.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (report / "analysis_report.md").write_text("# Report\n", encoding="utf-8")
    (metadata / "manifest.json").write_text("{}", encoding="utf-8")
    run_manifest.write_text('{"run_id":"joint-run-1"}', encoding="utf-8")
    active_run.write_text('{"run_id":"joint-run-1"}', encoding="utf-8")

    bundle_dirs = create_export_bundle_dirs(tmp_path / "bundle")
    copied = copy_export_bundle_sections(source, bundle_dirs)

    assert copied == ["figures", "data", "report", "metadata", "figure_runs"]
    assert (bundle_dirs["figures"] / "Fig-1.png").exists()
    assert (bundle_dirs["data"] / "results.csv").exists()
    assert (bundle_dirs["report"] / "analysis_report.md").exists()
    assert (bundle_dirs["metadata"] / "manifest.json").exists()
    assert (
        bundle_dirs["metadata"] / "runs" / "joint-run-1" / "figure_manifest.json"
    ).exists()
    assert (bundle_dirs["metadata"] / "active_run.json").read_text(encoding="utf-8") == (
        '{"run_id":"joint-run-1"}'
    )
