from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace

import pytest

from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.package import ProjectEvidencePackager
from polynexus.core.project_workflow.service import ProjectWorkflowService
from polynexus.core.project_workflow.workspace import ProjectWorkspace
from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.agent_workflow.models import AnalysisRecipe, AnalysisRun, EvidenceRecord, InputArtifact, RecipeStep, WorkflowStepResult
from polynexus.core.project_workflow.evidence import evidence_items_from_run
from polynexus.core.project_workflow.ir_group_figures import FigureCandidate, FigureCandidateSet


def _write_mettler_fixture(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = ["Sample Weight: 5.95 mg"]
    index = 0
    for setpoint, duration in ((255.0, 70), (180.0, 80), (255.0, 70), (181.0, 85)):
        for second in range(duration + 1):
            sample_temperature = setpoint + 0.05 if setpoint < 200 else setpoint + 0.02
            heat_flow = 1.0 + (20.0 / (second + 5) if setpoint < 200 else 0.0)
            rows.append(f"{index} {index} {sample_temperature:.3f} {setpoint:.3f} {heat_flow:.6f}")
            index += 1
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def _run_dsc_request(tmp_path: Path):
    source = _write_mettler_fixture(tmp_path / "raw" / "PA6-DWJJ.txt")
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question="Compare PA6 kinetics",
        requested_outputs=("avrami_parameter_table",),
        data_scope=(str(source.relative_to(tmp_path)),),
    )
    return service.run(request)


def test_package_contains_ars_entrypoint_and_provenance(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    package = ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))

    assert (package.path / "writing-input.md").exists()
    payload = json.loads((package.path / "evidence.json").read_text(encoding="utf-8"))
    assert payload["items"]
    assert payload["items"][0]["source_runs"]
    assert payload["items"][0]["supported_interpretations"]
    assert payload["items"][0]["disallowed_conclusions"]
    manifest = json.loads((package.path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "review_required"
    assert manifest["run_manifests"]
    assert manifest["evidence_item_hashes"]
    assert manifest["relations_hash"]
    assert (package.path / "figures").is_dir()
    assert (package.path / "tables").is_dir()
    relations = json.loads((package.path / "relations.json").read_text(encoding="utf-8"))
    assert relations["relations"] == [{
        "type": "run_part_of_request",
        "run_id": run.run_id,
        "request_hash": run.request_hash,
        "evidence_scope": "explicit_project_request",
    }]


def test_package_writing_evidence_groups_claim_boundaries_by_technique(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    package = ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))

    payload = json.loads((package.path / "writing-evidence.json").read_text(encoding="utf-8"))
    assert set(payload["techniques"]) == {"dsc"}
    item = payload["techniques"]["dsc"]["evidence"][0]
    assert item["source_runs"] == [run.run_id]
    assert item["supported_interpretations"]
    assert item["disallowed_conclusions"]
    assert isinstance(item["observed_metrics"], dict)
    writing = (package.path / "writing-input.md").read_text(encoding="utf-8")
    assert "## Writing evidence by technique" in writing
    assert "### DSC" in writing


def test_package_writes_citation_metrics_with_writing_evidence_links(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    package = ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))

    metrics = json.loads((package.path / "citation-metrics.json").read_text(encoding="utf-8"))
    writing = json.loads((package.path / "writing-evidence.json").read_text(encoding="utf-8"))
    manifest = json.loads((package.path / "manifest.json").read_text(encoding="utf-8"))

    assert metrics["version"] == 1
    assert metrics["records"]
    assert metrics["records"][0]["evidence_id"]
    assert metrics["records"][0]["raw_source_hashes"]
    assert manifest["citation_metrics"] == "citation-metrics.json"
    assert manifest["ars_writing_input"] == "ars-writing-input.json"
    assert manifest["questions"] == ["Compare PA6 kinetics"]
    ars = json.loads((package.path / "ars-writing-input.json").read_text(encoding="utf-8"))
    assert ars["citation_metrics"] == "citation-metrics.json"
    assert ars["techniques"]["dsc"]["evidence"][0]["results_metric_ids"]
    item = writing["techniques"]["dsc"]["evidence"][0]
    assert item["citation_metric_ids"]
    assert "results_candidate" in item["citation_metric_counts"]
    assert "Citation metrics: citation-metrics.json" in (package.path / "writing-input.md").read_text(encoding="utf-8")


def test_step_evidence_does_not_inherit_run_wide_disallowed_conclusions() -> None:
    artifact = InputArtifact.ready(path="source.csv", technique="ir", sha256="source-sha256")
    recipe = AnalysisRecipe.create(
        workflow_id="test.workflow.v1",
        artifacts=(artifact,),
        steps=(RecipeStep(step_id="ir_spectrum", technique="ir"),),
    )
    run = AnalysisRun(
        recipe=recipe,
        status="review_required",
        steps=(WorkflowStepResult(
            step_id="ir_spectrum",
            technique="ir",
            status="review_required",
            reason_codes=("ir_xc_uncalibrated",),
        ),),
        evidence=EvidenceRecord(
            disallowed_conclusions=(
                "unique_hydrogen_bond_species",
                "absolute_scattering_quantity_without_background",
            ),
        ),
    )

    item = evidence_items_from_run(
        run,
        run_id="run-ir",
        raw_sources=("source-sha256",),
    )[0]

    assert item.limitations == ("ir_xc_uncalibrated",)
    assert item.disallowed_conclusions == ("human_review_required",)


def test_package_keeps_run_wide_limitations_outside_technique_items(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    package = ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))

    package_limits = json.loads((package.path / "limitations.json").read_text(encoding="utf-8"))["limitations"]
    item = json.loads((package.path / "writing-evidence.json").read_text(encoding="utf-8"))["techniques"]["dsc"]["evidence"][0]

    assert "unique_hydrogen_bond_species" in package_limits
    assert "unique_hydrogen_bond_species" not in item["limitations"]


def test_new_package_version_does_not_replace_previous_snapshot(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    workspace = ProjectWorkspace.open(tmp_path)
    first = ProjectEvidencePackager(workspace).create((run,))
    first_manifest = (first.path / "manifest.json").read_bytes()
    second = ProjectEvidencePackager(workspace).create((run,))

    assert first.path != second.path
    assert first.path.exists()
    assert (first.path / "manifest.json").read_bytes() == first_manifest
    assert second.version == 2


def test_package_rejects_blocked_run(tmp_path: Path) -> None:
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(question="Analyze WAXS", data_scope=("raw/missing",))
    run = service.run(request)

    with pytest.raises(ValueError, match="blocked"):
        ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))


def test_package_rejects_tampered_run_manifest(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    manifest_path = Path(run.manifest_path or "")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["run_id"] = "tampered"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="run manifest"):
        ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))


def test_package_rejects_changed_raw_input(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    source = tmp_path / "raw" / "PA6-DWJJ.txt"
    source.write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="source hash"):
        ProjectEvidencePackager(ProjectWorkspace.open(tmp_path)).create((run,))


def test_package_copies_derived_assets_without_copying_raw_data(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    figure = tmp_path / ".polynexus" / "runs" / run.run_id / "kinetics.png"
    figure.parent.mkdir(parents=True, exist_ok=True)
    figure.write_bytes(b"derived figure")
    enriched = replace(run, outputs=(*run.outputs, str(figure)))

    package = ProjectWorkflowService.open(tmp_path).package(enriched)

    assert (package.path / "figures" / "kinetics.png").read_bytes() == b"derived figure"
    assert not list(package.path.rglob("PA6-DWJJ.txt"))


def test_package_indexes_svg_once_when_derived_figure_has_png_sibling(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    figure_dir = tmp_path / ".polynexus" / "runs" / run.run_id
    png = figure_dir / "kinetics.png"
    svg = figure_dir / "kinetics.svg"
    preview = figure_dir / "preview.png"
    figure_dir.mkdir(parents=True, exist_ok=True)
    png.write_bytes(b"derived preview")
    svg.write_text("<svg>derived figure</svg>", encoding="utf-8")
    preview.write_bytes(b"editor preview")

    package = ProjectWorkflowService.open(tmp_path).package(
        replace(run, outputs=(*run.outputs, str(png), str(svg), str(preview)))
    )

    index = json.loads((package.path / "figure-index.json").read_text(encoding="utf-8"))
    assert index["version"] == 1
    assert len(index["figures"]) == 1
    entry = index["figures"][0]
    assert entry["svg"] == "figures/kinetics.svg"
    assert entry["role"] == "diagnostic"
    assert entry["technique"] == "DSC"
    assert entry["document"] is None
    assert entry["data"] is None
    assert (package.path / entry["metadata"]).is_file()
    assert not (package.path / "figures" / "kinetics.png").exists()
    assert not (package.path / "figures" / "preview.png").exists()


def test_package_index_preserves_ars_selected_figure_role_and_technique(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    dsc_figure = tmp_path / ".polynexus" / "runs" / run.run_id / "dsc-output.svg"
    dsc_figure.parent.mkdir(parents=True, exist_ok=True)
    dsc_figure.write_text("<svg>unselected DSC output</svg>", encoding="utf-8")
    figure_dir = tmp_path / ".polynexus" / "figures" / "selection"
    figure_dir.mkdir(parents=True)
    svg = figure_dir / "ftir_group_overlay.svg"
    png = figure_dir / "ftir_group_overlay.png"
    svg.write_text("<svg>selected FTIR group figure</svg>", encoding="utf-8")
    png.write_bytes(b"selected FTIR group preview")
    candidates = FigureCandidateSet(
        selection_id="selection",
        main_candidates=(FigureCandidate(
            candidate_id="selection:group_overlay",
            kind="group_overlay",
            role="main_candidate",
            group_ids=("ir:pa6-jw:temperature_C",),
            technique="ir",
            condition_kind="temperature_C",
            source_artifacts=("raw/PA6-JW-100.csv", "raw/PA6-JW-110.csv"),
            paths=(str(png), str(svg)),
        ),),
    )

    package = ProjectWorkflowService.open(tmp_path).package(
        replace(run, outputs=(*run.outputs, str(dsc_figure))), figure_candidates=candidates
    )

    index = json.loads((package.path / "figure-index.json").read_text(encoding="utf-8"))
    assert index["figures"] == [
        {
            "id": "dsc-output",
            "role": "diagnostic",
            "technique": "DSC",
            "group": None,
            "writing_eligibility": "review_only",
            "svg": "figures/dsc-output.svg",
            "document": None,
            "data": None,
            "metadata": "figures/dsc-output.metadata.json",
        },
        {
            "id": "ftir_group_overlay",
            "role": "manuscript_candidate",
            "technique": "IR",
            "group": "ir:pa6-jw:temperature_C",
            "writing_eligibility": "review_only",
            "svg": "figures/ftir_group_overlay.svg",
            "document": None,
            "data": None,
            "metadata": "figures/ftir_group_overlay.metadata.json",
        }
    ]


def test_package_rejects_conflicting_candidate_roles_for_same_figure(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    figure = tmp_path / ".polynexus" / "figures" / "selection" / "figure.svg"
    figure.parent.mkdir(parents=True)
    figure.write_text("<svg>candidate</svg>", encoding="utf-8")
    candidate = FigureCandidate(
        candidate_id="selection:figure",
        kind="group_overlay",
        role="main_candidate",
        group_ids=("ir:pa6-jw:temperature_C",),
        technique="ir",
        condition_kind="temperature_C",
        source_artifacts=("raw/PA6-JW-100.csv",),
        paths=(str(figure),),
    )

    with pytest.raises(ValueError, match="conflicting figure candidate role"):
        ProjectWorkflowService.open(tmp_path).package(
            run,
            figure_candidates=FigureCandidateSet(
                selection_id="selection",
                main_candidates=(candidate,),
                supporting_candidates=(candidate,),
            ),
        )


def test_package_rejects_conflicting_candidate_roles_for_figure_siblings(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    figure_dir = tmp_path / ".polynexus" / "figures" / "selection"
    figure_dir.mkdir(parents=True)
    svg = figure_dir / "figure.svg"
    png = figure_dir / "figure.png"
    svg.write_text("<svg>candidate</svg>", encoding="utf-8")
    png.write_bytes(b"candidate preview")
    common = {
        "kind": "group_overlay",
        "group_ids": ("ir:pa6-jw:temperature_C",),
        "technique": "ir",
        "condition_kind": "temperature_C",
        "source_artifacts": ("raw/PA6-JW-100.csv",),
    }

    with pytest.raises(ValueError, match="conflicting figure candidate role"):
        ProjectWorkflowService.open(tmp_path).package(
            run,
            figure_candidates=FigureCandidateSet(
                selection_id="selection",
                main_candidates=(FigureCandidate(
                    candidate_id="selection:main", role="main_candidate", paths=(str(svg),), **common
                ),),
                supporting_candidates=(FigureCandidate(
                    candidate_id="selection:support", role="supporting_candidate", paths=(str(png), str(svg)), **common
                ),),
            ),
        )


def test_package_indexes_distinct_selected_figures_from_one_output_directory(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    figure_dir = tmp_path / ".polynexus" / "figures" / "selection" / "main"
    figure_dir.mkdir(parents=True)
    overlay = figure_dir / "ftir_group_overlay.svg"
    trend = figure_dir / "ftir_metric_trend.svg"
    overlay.write_text("<svg>overlay</svg>", encoding="utf-8")
    trend.write_text("<svg>trend</svg>", encoding="utf-8")
    common = {
        "role": "main_candidate",
        "group_ids": ("ir:pa6-jw:temperature_C",),
        "technique": "ir",
        "condition_kind": "temperature_C",
        "source_artifacts": ("raw/PA6-JW-100.csv", "raw/PA6-JW-110.csv"),
    }
    candidates = FigureCandidateSet(
        selection_id="selection",
        main_candidates=(
            FigureCandidate(candidate_id="selection:overlay", kind="group_overlay", paths=(str(overlay),), **common),
            FigureCandidate(candidate_id="selection:trend", kind="metric_trend", paths=(str(trend),), **common),
        ),
    )

    package = ProjectWorkflowService.open(tmp_path).package(run, figure_candidates=candidates)

    index = json.loads((package.path / "figure-index.json").read_text(encoding="utf-8"))
    assert {(entry["svg"], entry["role"]) for entry in index["figures"]} == {
        ("figures/ftir_group_overlay.svg", "manuscript_candidate"),
        ("figures/ftir_metric_trend.svg", "manuscript_candidate"),
    }


def test_package_rejects_candidate_without_svg(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    png = tmp_path / ".polynexus" / "figures" / "selection" / "figure.png"
    png.parent.mkdir(parents=True)
    png.write_bytes(b"PNG-only candidate")
    candidate = FigureCandidate(
        candidate_id="selection:figure",
        kind="group_overlay",
        role="main_candidate",
        group_ids=("ir:pa6-jw:temperature_C",),
        technique="ir",
        condition_kind="temperature_C",
        source_artifacts=("raw/PA6-JW-100.csv",),
        paths=(str(png),),
    )

    with pytest.raises(ValueError, match="figure candidate svg is missing"):
        ProjectWorkflowService.open(tmp_path).package(
            run,
            figure_candidates=FigureCandidateSet(
                selection_id="selection", main_candidates=(candidate,)
            ),
        )


def test_package_deduplicates_same_role_candidate_siblings_with_different_ids(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    figure_dir = tmp_path / ".polynexus" / "figures" / "selection"
    figure_dir.mkdir(parents=True)
    svg = figure_dir / "figure.svg"
    png = figure_dir / "figure.png"
    svg.write_text("<svg>candidate</svg>", encoding="utf-8")
    png.write_bytes(b"candidate preview")
    common = {
        "role": "main_candidate",
        "group_ids": ("ir:pa6-jw:temperature_C",),
        "technique": "ir",
        "condition_kind": "temperature_C",
        "source_artifacts": ("raw/PA6-JW-100.csv",),
    }
    package = ProjectWorkflowService.open(tmp_path).package(
        run,
        figure_candidates=FigureCandidateSet(
            selection_id="selection",
            main_candidates=(
                FigureCandidate(candidate_id="selection:one", kind="group_overlay", paths=(str(svg),), **common),
                FigureCandidate(candidate_id="selection:two", kind="group_overlay", paths=(str(png), str(svg)), **common),
            ),
        ),
    )

    index = json.loads((package.path / "figure-index.json").read_text(encoding="utf-8"))
    assert [entry["svg"] for entry in index["figures"] if entry["id"] == "figure"] == ["figures/figure.svg"]
    assert not (package.path / "figures" / "figure.png").exists()


def test_package_rejects_conflicting_candidate_group_for_same_figure(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    svg = tmp_path / ".polynexus" / "figures" / "selection" / "figure.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg>candidate</svg>", encoding="utf-8")
    common = {
        "kind": "group_overlay",
        "role": "main_candidate",
        "technique": "ir",
        "condition_kind": "temperature_C",
        "source_artifacts": ("raw/PA6-JW-100.csv",),
        "paths": (str(svg),),
    }

    with pytest.raises(ValueError, match="conflicting figure candidate metadata"):
        ProjectWorkflowService.open(tmp_path).package(
            run,
            figure_candidates=FigureCandidateSet(
                selection_id="selection",
                main_candidates=(
                    FigureCandidate(
                        candidate_id="selection:one", group_ids=("ir:pa6-jw:temperature_C",), **common
                    ),
                    FigureCandidate(
                        candidate_id="selection:two", group_ids=("ir:pa6-sw:temperature_C",), **common
                    ),
                ),
            ),
        )


def test_package_keeps_same_named_derived_figures_from_distinct_sources(tmp_path: Path) -> None:
    run = _run_dsc_request(tmp_path)
    first = tmp_path / ".polynexus" / "runs" / run.run_id / "first" / "figure.svg"
    second = tmp_path / ".polynexus" / "runs" / run.run_id / "second" / "figure.svg"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("<svg>same</svg>", encoding="utf-8")
    second.write_text("<svg>same</svg>", encoding="utf-8")

    package = ProjectWorkflowService.open(tmp_path).package(
        replace(run, outputs=(*run.outputs, str(first), str(second)))
    )

    figures = sorted((package.path / "figures").glob("*.svg"))
    assert len(figures) == 2
    assert figures[0].name != figures[1].name


def test_package_projects_cross_technique_membership_without_sample_inference(tmp_path: Path) -> None:
    first = _run_dsc_request(tmp_path)
    second = _run_dsc_request(tmp_path)
    package = ProjectWorkflowService.open(tmp_path).package((first, second), package_id="joint-evidence")
    relations = json.loads((package.path / "relations.json").read_text(encoding="utf-8"))["relations"]
    relation = next(item for item in relations if item["type"] in {"cross_technique_evidence_set", "technique_series_evidence_set"})
    assert relation["run_ids"] == [first.run_id, second.run_id]
    assert "sample_id" not in relation


def test_package_validates_ir_directory_source_without_copying_raw(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "series"
    source.mkdir(parents=True)
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,1\n", encoding="utf-8")
    agent = AgentWorkflowService(provider_runner=lambda step, artifact, output: AnalysisResult(
        technique=step.technique, validation_passed=True,
    ))
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = agent
    service.inspect((source,))
    run = service.run(AnalysisRequest.create(
        question="Analyze IR series",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))
    package = service.package(run, package_id="ir-series")
    assert package.status == "review_required"
    assert not any(path.name == "20C.csv" for path in package.path.rglob("*"))
