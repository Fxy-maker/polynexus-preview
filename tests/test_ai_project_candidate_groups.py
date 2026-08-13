from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow import ProjectWorkflowService
from polynexus.core.project_workflow.grouping import candidate_groups
from polynexus.cli.parser import build_parser
from polynexus.cli.run_project_workflow_service import run_project_workflow
import json


def _ftir(root: Path, name: str) -> Path:
    path = root / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("XLabel,Wavenumber\nYLabel,Absorbance\n1000,1\n900,2\n", encoding="utf-8")
    return path


def _service(root: Path) -> ProjectWorkflowService:
    service = ProjectWorkflowService.open(root)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(technique=step.technique, validation_passed=True)
    )
    return service


def test_candidate_groups_extract_filename_only_jw_sw_and_time_series(tmp_path: Path) -> None:
    paths = [
        _ftir(tmp_path, "PA6-JW-30.csv"),
        _ftir(tmp_path, "PA6-JW-40.csv"),
        _ftir(tmp_path, "PA6-SW-30.csv"),
        _ftir(tmp_path, "PA6-250-for 1min.csv"),
        _ftir(tmp_path, "PA6-250-for 2min.csv"),
    ]
    graph = _service(tmp_path).inspect(paths)

    groups = candidate_groups(graph.artifacts)

    assert [(group.label, group.condition_kind, group.condition_values) for group in groups] == [
        ("PA6 JW temperature series", "temperature_C", (30.0, 40.0)),
        ("PA6 SW temperature series", "temperature_C", (30.0,)),
        ("PA6 250 C time series", "time_min", (1.0, 2.0)),
    ]
    assert all(group.status == "inferred_from_filename" for group in groups)


def test_candidate_groups_distinguish_colliding_material_prefixes(tmp_path: Path) -> None:
    paths = [
        _ftir(tmp_path, "PA6-JW-30.csv"),
        _ftir(tmp_path, "PEEK-JW-30.csv"),
    ]
    graph = _service(tmp_path).inspect(paths)

    groups = candidate_groups(graph.artifacts)

    assert [(group.group_id, group.label) for group in groups] == [
        ("ir:pa6-jw:temperature_C", "PA6 JW temperature series"),
        ("ir:peek-jw:temperature_C", "PEEK JW temperature series"),
    ]


def test_question_selects_matching_candidate_group_before_run(tmp_path: Path) -> None:
    for name in ("PA6-JW-30.csv", "PA6-JW-40.csv", "PA6-SW-30.csv", "PA6-SW-40.csv"):
        _ftir(tmp_path, name)
    summary = _service(tmp_path).analyze_project(question="Compare the JW FTIR temperature series")

    payload = summary.to_dict()
    assert payload["computation"] == "passed"
    assert payload["selected_group"]["label"] == "PA6 JW temperature series"
    assert payload["evidence_count"] == 2


def test_question_condition_unit_does_not_match_unrelated_time_group(tmp_path: Path) -> None:
    for name in (
        "PA6-JW-30.csv",
        "PA6-JW-40.csv",
        "PA6-250-for 1min.csv",
        "PA6-250-for 2min.csv",
    ):
        _ftir(tmp_path, name)

    summary = _service(tmp_path).analyze_project(
        question="Compare the JW FTIR measurements at 30 C"
    )

    payload = summary.to_dict()
    assert payload["computation"] == "passed"
    assert payload["selected_group"]["label"] == "PA6 JW temperature series"


def test_question_time_series_does_not_select_a_temperature_group(tmp_path: Path) -> None:
    for name in ("PA6-JW-30.csv", "PA6-250-for 1min.csv"):
        _ftir(tmp_path, name)

    summary = _service(tmp_path).analyze_project(question="Compare the JW time series")

    payload = summary.to_dict()
    assert payload["computation"] == "blocked"
    assert payload["reason_codes"] == ["candidate_group_selection_required"]


def test_single_candidate_is_recorded_as_the_selected_scope(tmp_path: Path) -> None:
    for name in ("PA6-JW-30.csv", "PA6-JW-40.csv"):
        _ftir(tmp_path, name)

    summary = _service(tmp_path).analyze_project(question="Analyze PA6 FTIR data")

    payload = summary.to_dict()
    assert payload["computation"] == "passed"
    assert payload["selected_group"]["label"] == "PA6 JW temperature series"


def test_explicit_scope_keeps_same_stem_companion_files(tmp_path: Path) -> None:
    csv_path = _ftir(tmp_path, "PA6-JW-30.csv")
    spa_path = _ftir(tmp_path, "PA6-JW-30.spa")

    discovered, _ = _service(tmp_path)._discover_project_files(
        (str(csv_path), str(spa_path))
    )

    assert discovered == (csv_path, spa_path)


def test_ambiguous_project_returns_candidates_without_starting_provider(tmp_path: Path) -> None:
    for name in ("PA6-JW-30.csv", "PA6-SW-30.csv", "PA6-250-for 1min.csv"):
        _ftir(tmp_path, name)
    summary = _service(tmp_path).analyze_project(question="Analyze PA6 FTIR data")

    payload = summary.to_dict()
    assert payload["computation"] == "blocked"
    assert payload["reason_codes"] == ["candidate_group_selection_required"]
    assert [group["label"] for group in payload["candidate_groups"]] == [
        "PA6 JW temperature series", "PA6 SW temperature series", "PA6 250 C time series",
    ]
    assert payload["runs"] == []


def test_cli_returns_candidate_groups_before_ambiguous_full_directory_run(capsys, tmp_path: Path) -> None:
    for name in ("PA6-JW-30.csv", "PA6-SW-30.csv"):
        _ftir(tmp_path, name)
    args = build_parser().parse_args([
        "project-workflow", "analyze-project", "--project-root", str(tmp_path),
        "--question", "Analyze PA6 FTIR data",
    ])

    code = run_project_workflow(args, service=_service(tmp_path))

    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["analysis"]["reason_codes"] == ["candidate_group_selection_required"]
    assert len(payload["analysis"]["candidate_groups"]) == 2
