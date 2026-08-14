from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow.grouping import CandidateExperimentGroup
from polynexus.core.project_workflow.ir_group_figures import render_ftir_group_candidates
from polynexus.core.project_workflow.selection import (
    FigureSelectionRequest,
    resolve_figure_selection,
)
from polynexus.core.project_workflow.service import ProjectWorkflowService
from polynexus.cli.parser import build_parser
from polynexus.cli.run_project_workflow_service import run_project_workflow
import json


def _group(
    group_id: str,
    *,
    technique: str = "ir",
    condition_kind: str = "temperature_C",
) -> CandidateExperimentGroup:
    return CandidateExperimentGroup(
        group_id=group_id,
        label=group_id,
        technique=technique,
        condition_kind=condition_kind,
        condition_values=(30.0, 40.0),
        artifact_paths=("raw/a.csv", "raw/b.csv"),
    )


def test_figure_selection_requires_unique_known_groups() -> None:
    request = FigureSelectionRequest.create(
        question="Compare PA6 series",
        selected_groups=("ir:pa6-jw:temperature_C", "ir:pa6-jw:temperature_C"),
        figure_intent="compare_groups",
    )

    assert request.reason_codes == ("selected_groups_duplicate",)
    resolved = resolve_figure_selection(request, (_group("ir:pa6-jw:temperature_C"),))
    assert resolved.status == "blocked"
    assert resolved.reason_codes == ("selected_groups_duplicate",)


def test_figure_selection_blocks_mixed_condition_kinds() -> None:
    request = FigureSelectionRequest.create(
        question="Compare PA6 sequences",
        selected_groups=("ir:pa6-jw:temperature_C", "ir:pa6-250:time_min"),
        figure_intent="compare_groups",
    )

    resolved = resolve_figure_selection(
        request,
        (
            _group("ir:pa6-jw:temperature_C"),
            _group("ir:pa6-250:time_min", condition_kind="time_min"),
        ),
    )

    assert resolved.status == "blocked"
    assert resolved.reason_codes == ("selected_groups_condition_kind_mismatch",)


def test_compare_groups_renders_overlay_for_two_usable_groups(tmp_path: Path) -> None:
    first = _group("ir:pa6-jw:temperature_C")
    second = _group("ir:pa6-sw:temperature_C")
    (tmp_path / "raw").mkdir()
    for path in ("a.csv", "b.csv"):
        (tmp_path / "raw" / path).write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    first = CandidateExperimentGroup(**{**first.to_dict(), "artifact_paths": ("raw/a.csv", "raw/b.csv")})
    second = CandidateExperimentGroup(**{**second.to_dict(), "artifact_paths": ("raw/a.csv", "raw/b.csv")})
    request = FigureSelectionRequest.create(
        question="Compare PA6 JW and SW",
        selected_groups=(first.group_id, second.group_id),
        figure_intent="compare_groups",
    )
    selection = resolve_figure_selection(request, (first, second))

    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
    )

    assert [candidate.kind for candidate in result.main_candidates] == [
        "group_comparison_overlay",
        "group_difference",
    ]
    assert set(result.main_candidates[0].group_ids) == {first.group_id, second.group_id}


def test_compare_groups_keeps_overlay_when_conditions_do_not_match(tmp_path: Path) -> None:
    first = _group("ir:pa6-jw:temperature_C")
    second = CandidateExperimentGroup(
        group_id="ir:pa6-sw:temperature_C",
        label="ir pa6 sw",
        technique="ir",
        condition_kind="temperature_C",
        condition_values=(50.0, 60.0),
        artifact_paths=("raw/c.csv", "raw/d.csv"),
    )
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    for path in ("a.csv", "b.csv", "c.csv", "d.csv"):
        (source_dir / path).write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    selection = resolve_figure_selection(
        FigureSelectionRequest.create(
            question="Compare PA6 JW and SW",
            selected_groups=(first.group_id, second.group_id),
            figure_intent="compare_groups",
        ),
        (first, second),
    )
    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
    )
    assert result.main_candidates
    assert result.main_candidates[0].kind == "group_comparison_overlay"
    assert "comparison_conditions_unmatched" in result.omission_reasons


def test_compare_groups_retains_mixed_metric_method_limitation(tmp_path: Path) -> None:
    groups = (_group("ir:pa6-jw:temperature_C"), _group("ir:pa6-sw:temperature_C"))
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    for index in range(4):
        (source_dir / f"{chr(97 + index)}.csv").write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    groups = tuple(
        CandidateExperimentGroup(
            group_id=group.group_id,
            label=group.label,
            technique=group.technique,
            condition_kind=group.condition_kind,
            condition_values=group.condition_values if index == 0 else (50.0, 60.0),
            artifact_paths=("raw/a.csv", "raw/b.csv") if index == 0 else ("raw/c.csv", "raw/d.csv"),
        )
        for index, group in enumerate(groups)
    )
    selection = resolve_figure_selection(
        FigureSelectionRequest.create(
            question="Compare PA6 JW and SW",
            selected_groups=tuple(group.group_id for group in groups),
            figure_intent="compare_groups",
        ),
        groups,
    )
    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
        metric_values={
            "raw/a.csv": (30.0, "method_a"), "raw/b.csv": (40.0, "method_a"),
            "raw/c.csv": (20.0, "method_b"), "raw/d.csv": (35.0, "method_b"),
        },
    )
    assert any(candidate.kind == "group_comparison_overlay" for candidate in result.main_candidates)
    trend = next((candidate for candidate in result.main_candidates if candidate.kind == "group_comparison_trend"), None)
    assert trend is not None
    assert "metric_methods_differ" in trend.limitations


def test_figure_selection_is_stable_for_one_selected_group() -> None:
    request = FigureSelectionRequest.create(
        question="Describe PA6 JW evolution",
        selected_groups=("ir:pa6-jw:temperature_C",),
        figure_intent="describe_group",
    )

    resolved = resolve_figure_selection(request, (_group("ir:pa6-jw:temperature_C"),))

    assert resolved.status == "ready"
    assert resolved.selection_id.startswith("selection-")
    assert resolved.groups[0].group_id == "ir:pa6-jw:temperature_C"


def test_render_ftir_group_overlay_uses_only_selected_sources(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    first = source_dir / "PA6-JW-30.csv"
    second = source_dir / "PA6-JW-40.csv"
    ignored = source_dir / "PA6-SW-30.csv"
    for path, multiplier in ((first, 1.0), (second, 2.0), (ignored, 3.0)):
        path.write_text(
            "Wavenumber,Absorbance\n1000,{0}\n900,{1}\n800,{2}\n".format(
                multiplier, multiplier + 1.0, multiplier + 2.0
            ),
            encoding="utf-8",
        )
    group = CandidateExperimentGroup(
        group_id="ir:pa6-jw:temperature_C",
        label="PA6 JW temperature series",
        technique="ir",
        condition_kind="temperature_C",
        condition_values=(30.0, 40.0),
        artifact_paths=(
            first.relative_to(tmp_path).as_posix(),
            second.relative_to(tmp_path).as_posix(),
        ),
    )
    request = FigureSelectionRequest.create(
        question="Describe PA6 JW evolution",
        selected_groups=(group.group_id,),
    )
    selection = resolve_figure_selection(request, (group,))

    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
    )

    overlay = result.main_candidates[0]
    assert overlay.kind == "group_overlay"
    assert all(Path(path).is_file() for path in overlay.paths)
    assert overlay.source_artifacts == group.artifact_paths


def test_render_ftir_overlay_uses_stable_group_preprocessing_for_small_spectra(
    tmp_path: Path,
    caplog,
) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    paths = tuple(source_dir / f"PA6-JW-{value}.csv" for value in (30, 40))
    for path in paths:
        path.write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    group = CandidateExperimentGroup(
        group_id="ir:pa6-jw:temperature_C",
        label="PA6 JW temperature series",
        technique="ir",
        condition_kind="temperature_C",
        condition_values=(30.0, 40.0),
        artifact_paths=tuple(path.relative_to(tmp_path).as_posix() for path in paths),
    )
    selection = resolve_figure_selection(
        FigureSelectionRequest.create(question="Describe PA6 JW", selected_groups=(group.group_id,)),
        (group,),
    )

    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
    )

    assert result.main_candidates
    assert "rubberband convex-hull baseline failed" not in caplog.text


def test_render_ftir_trend_requires_common_finite_xc_metric(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    first = source_dir / "PA6-JW-30.csv"
    second = source_dir / "PA6-JW-40.csv"
    for path in (first, second):
        path.write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    group = CandidateExperimentGroup(
        group_id="ir:pa6-jw:temperature_C",
        label="PA6 JW temperature series",
        technique="ir",
        condition_kind="temperature_C",
        condition_values=(30.0, 40.0),
        artifact_paths=(
            first.relative_to(tmp_path).as_posix(),
            second.relative_to(tmp_path).as_posix(),
        ),
    )
    selection = resolve_figure_selection(
        FigureSelectionRequest.create(question="Show PA6 JW trend", selected_groups=(group.group_id,)),
        (group,),
    )

    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
        metric_values={
            group.artifact_paths[0]: (31.5, "provider_reported_band_ratio"),
            group.artifact_paths[1]: (42.0, "provider_reported_band_ratio"),
        },
    )

    assert [candidate.kind for candidate in result.main_candidates] == ["group_overlay", "metric_trend"]


def test_render_ftir_trend_is_suppressed_for_missing_metric(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    paths = tuple(source_dir / f"PA6-JW-{value}.csv" for value in (30, 40))
    for path in paths:
        path.write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    group = CandidateExperimentGroup(
        group_id="ir:pa6-jw:temperature_C",
        label="PA6 JW temperature series",
        technique="ir",
        condition_kind="temperature_C",
        condition_values=(30.0, 40.0),
        artifact_paths=tuple(path.relative_to(tmp_path).as_posix() for path in paths),
    )
    selection = resolve_figure_selection(
        FigureSelectionRequest.create(question="Show PA6 JW trend", selected_groups=(group.group_id,)),
        (group,),
    )

    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
        metric_values={group.artifact_paths[0]: (31.5, "provider_reported_band_ratio")},
    )

    assert [candidate.kind for candidate in result.main_candidates] == ["group_overlay"]
    assert result.omission_reasons == ("metric_trend_metric_unavailable",)


def test_render_ftir_trend_is_suppressed_for_mixed_metric_methods(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    paths = tuple(source_dir / f"PA6-JW-{value}.csv" for value in (30, 40))
    for path in paths:
        path.write_text("Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8")
    group = _group("ir:pa6-jw:temperature_C")
    group = CandidateExperimentGroup(
        **{**group.to_dict(), "artifact_paths": tuple(path.relative_to(tmp_path).as_posix() for path in paths)}
    )
    selection = resolve_figure_selection(
        FigureSelectionRequest.create(question="Show PA6 JW trend", selected_groups=(group.group_id,)),
        (group,),
    )
    result = render_ftir_group_candidates(
        selection=selection,
        project_root=tmp_path,
        output_dir=tmp_path / ".polynexus" / "figures" / selection.selection_id,
        metric_values={
            group.artifact_paths[0]: (31.5, "method_a"),
            group.artifact_paths[1]: (42.0, "method_b"),
        },
    )
    assert [candidate.kind for candidate in result.main_candidates] == ["group_overlay"]
    assert result.omission_reasons == ("metric_trend_metric_unavailable",)


def test_compare_selection_blocks_before_provider_execution(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    for name in ("PA6-JW-30.csv", "PA6-SW-30.csv"):
        (source_dir / name).write_text("Wavenumber,Absorbance\n1000,1\n900,2\n", encoding="utf-8")
    calls: list[str] = []
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: (
            calls.append(artifact.path)
            or AnalysisResult(technique=step.technique, validation_passed=True)
        )
    )
    request = FigureSelectionRequest.create(
        question="Compare PA6 JW and SW",
        selected_groups=("ir:pa6-jw:temperature_C", "ir:pa6-sw:temperature_C"),
        figure_intent="compare_groups",
    )
    summary = service.analyze_project(question=request.question, figure_selection=request)
    assert summary.computation in {"passed", "completed", "review_required"}
    assert len(calls) == 2


def test_analyze_project_with_ars_selection_runs_selected_group_and_limits_main_figures(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    for name, values in {
        "PA6-JW-30.csv": (1.0, 2.0, 3.0),
        "PA6-JW-40.csv": (1.5, 2.5, 3.5),
        "PA6-SW-30.csv": (3.0, 4.0, 5.0),
    }.items():
        (source_dir / name).write_text(
            "Wavenumber,Absorbance\n1000,{0}\n900,{1}\n800,{2}\n".format(*values),
            encoding="utf-8",
        )
    calls: list[str] = []

    def provider(step, artifact, output_dir):
        calls.append(Path(artifact.path).name)
        return AnalysisResult(
            technique=step.technique,
            validation_passed=True,
            parameters={
                "Xc_pct": 30.0 if "30" in artifact.path else 40.0,
                "Xc_method": "provider_reported_band_ratio",
            },
        )

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=provider)
    request = FigureSelectionRequest.create(
        question="Describe PA6 JW evolution",
        selected_groups=("ir:pa6-jw:temperature_C",),
        figure_intent="describe_group",
        main_figure_limit=2,
    )

    summary = service.analyze_project(
        question=request.question,
        figure_selection=request,
    )

    payload = summary.to_dict()
    assert calls == ["PA6-JW-30.csv", "PA6-JW-40.csv"]
    assert payload["selected_groups"] == ["ir:pa6-jw:temperature_C"]
    assert [figure["kind"] for figure in payload["figure_candidates"]["main_candidates"]] == [
        "group_overlay",
        "metric_trend",
    ]


def test_invalid_ars_selection_blocks_before_provider_execution(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    (source_dir / "PA6-JW-30.csv").write_text(
        "Wavenumber,Absorbance\n1000,1\n900,2\n", encoding="utf-8"
    )
    calls: list[str] = []
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: calls.append(artifact.path)
    )
    request = FigureSelectionRequest.create(
        question="Describe unknown group",
        selected_groups=("ir:missing:temperature_C",),
    )

    summary = service.analyze_project(question=request.question, figure_selection=request)

    assert summary.computation == "blocked"
    assert summary.reason_codes == ("selected_group_unknown",)
    assert calls == []


def test_analyze_project_cli_reads_figure_selection_json(capsys, tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    for name in ("PA6-JW-30.csv", "PA6-JW-40.csv"):
        (source_dir / name).write_text(
            "Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8"
        )
    selection_path = tmp_path / "selection.json"
    selection_path.write_text(json.dumps({
        "question": "Describe PA6 JW evolution",
        "selected_groups": ["ir:pa6-jw:temperature_C"],
        "figure_intent": "describe_group",
        "main_figure_limit": 1,
    }), encoding="utf-8")
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique, validation_passed=True
        )
    )
    args = build_parser().parse_args([
        "project-workflow", "analyze-project", "--project-root", str(tmp_path),
        "--figure-selection", str(selection_path),
    ])

    code = run_project_workflow(args, service=service)

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["analysis"]["selected_groups"] == ["ir:pa6-jw:temperature_C"]
    assert len(payload["analysis"]["figure_candidates"]["main_candidates"]) == 1


def test_evidence_package_copies_figure_candidate_manifest(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw"
    source_dir.mkdir()
    for name in ("PA6-JW-30.csv", "PA6-JW-40.csv"):
        (source_dir / name).write_text(
            "Wavenumber,Absorbance\n1000,1\n900,2\n800,3\n", encoding="utf-8"
        )
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique, validation_passed=True
        )
    )
    selection = FigureSelectionRequest.create(
        question="Describe PA6 JW evolution",
        selected_groups=("ir:pa6-jw:temperature_C",),
    )

    summary = service.analyze_project(question=selection.question, figure_selection=selection)

    package_path = Path(summary.to_dict()["package"]["path"])
    candidate_manifest = json.loads((package_path / "figure-candidates.json").read_text(encoding="utf-8"))
    assert candidate_manifest["main_candidates"][0]["role"] == "main_candidate"
    assert candidate_manifest["main_candidates"][0]["paths"] == [
        "figures/ftir_group_overlay.svg",
    ]
