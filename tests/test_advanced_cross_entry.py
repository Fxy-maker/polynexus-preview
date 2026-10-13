from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from polynexus.cli.run_single_service import run_single
from polynexus.core.agent_workflow import (
    AgentWorkflowService,
    AnalysisRecipe,
    InputArtifact,
    RecipeStep,
)
from polynexus.core.agent_workflow.registry import WorkflowRegistry
from polynexus.core.compute import ComputeRunService
from polynexus.core.compute.models import RawArtifact
from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.service import ProjectWorkflowService


class _RecipeAdapter:
    workflow_id = "test.advanced-replay.v1"

    @staticmethod
    def is_valid_recipe(recipe: AnalysisRecipe) -> bool:
        return recipe.workflow_id == _RecipeAdapter.workflow_id


def _run_and_replay(
    tmp_path: Path,
    technique: str,
    content: str,
    option_name: str,
    option: dict,
):
    source = tmp_path / f"{technique}.csv"
    source.write_text(content, encoding="utf-8")
    direct = ComputeRunService().run_direct(
        technique=technique,
        path=source,
        output_dir=tmp_path / "direct",
        pipeline_options={option_name: option},
    )
    assert direct.status == "completed"
    assert direct.canonical_template is not None
    artifact = InputArtifact.ready(
        path=str(source),
        technique=technique,
        sha256=RawArtifact.from_path(source, technique=technique).sha256,
    )
    recipe = AnalysisRecipe.create(
        workflow_id=_RecipeAdapter.workflow_id,
        artifacts=(artifact,),
        steps=(
            RecipeStep(
                step_id=f"{technique}-advanced",
                technique=technique,
                parameters={
                    "canonical_converter": direct.canonical_template.conversion_record.conversion_id,
                    "canonical_template": direct.canonical_template.to_dict(),
                },
            ),
        ),
    )
    registry = WorkflowRegistry()
    registry.register(_RecipeAdapter())
    agent_output = tmp_path.parent / f"{tmp_path.name}-{technique}-agent"
    replayed = AgentWorkflowService(registry=registry).run_recipe(recipe, agent_output)
    assert replayed.status in {"completed", "review_required"}
    assert replayed.steps[0].compute_run is not None
    compute_run = replayed.steps[0].to_dict()["compute_run"]
    assert compute_run["canonical_template"]["content_hash"] == direct.canonical_template.content_hash
    direct_manifest = {
        row["path"]: row
        for row in direct.result.metric_manifest(source=str(source))
    }
    replay_manifest = {
        row["path"]: row for row in compute_run["result"]["metric_manifest"]
    }
    assert json.dumps(replay_manifest, sort_keys=True) == json.dumps(
        direct_manifest, sort_keys=True
    )
    return direct, replayed


@pytest.mark.parametrize(
    ("technique", "content", "option_name", "option"),
    (
        (
            "tga",
            "Temperature (C),Mass (%)\n25,100\n100,98\n200,90\n300,50\n400,20\n",
            "tga_kinetics",
            {"heating_rates": [10.0, 20.0]},
        ),
        (
            "dma",
            "Frequency (Hz),Storage Modulus (Pa)\n1,10\n10,20\n100,30\n",
            "dma_tts",
            {
                "reference_temperature": 25.0,
                "temperatures": [25.0],
                "shift_factors": [1.0],
                "curve_measurement_ids": [
                        "sheet-0-table-0"
                ],
            },
        ),
        (
            "rheology",
            "Time (s),Viscosity (Pa*s)\n0,10\n1,8\n2,6\n",
            "rheology_advanced",
            {
                    "thixotropy_measurement_id": "sheet-0-table-0"
            },
        ),
        (
            "mechanics",
            "Cycle,Force (N)\n1,10\n2,8\n3,7\n",
            "mechanics_advanced",
                {"cycle_measurement_id": "sheet-0-table-0"},
        ),
    ),
)
def test_advanced_specs_replay_identically_through_agent(
    tmp_path: Path,
    technique: str,
    content: str,
    option_name: str,
    option: dict,
) -> None:
    _run_and_replay(tmp_path, technique, content, option_name, option)


@pytest.mark.parametrize(
    ("technique", "content", "option_name", "option"),
    (
        (
            "tga",
            "Temperature (C),Mass (%)\n25,100\n100,98\n200,90\n",
            "tga_kinetics",
            {"heating_rates": [10.0, 20.0], "curve_measurement_ids": ["missing", "also-missing"]},
        ),
        (
            "dma",
            "Frequency (Hz),Storage Modulus (Pa)\n1,10\n10,20\n",
            "dma_tts",
            {
                "reference_temperature": 25.0,
                "temperatures": [25.0],
                "shift_factors": [1.0],
                "curve_measurement_ids": ["missing"],
            },
        ),
        (
            "rheology",
            "Time (s),Viscosity (Pa*s)\n0,10\n1,8\n2,6\n",
            "rheology_advanced",
            {"thixotropy_measurement_id": "missing"},
        ),
        (
            "mechanics",
            "Cycle,Force (N)\n1,10\n2,8\n3,7\n",
            "mechanics_advanced",
            {"cycle_measurement_id": "missing"},
        ),
    ),
)
def test_advanced_specs_reject_measurements_outside_canonical_template(
    tmp_path: Path,
    technique: str,
    content: str,
    option_name: str,
    option: dict,
) -> None:
    source = tmp_path / f"{technique}-invalid.csv"
    source.write_text(content, encoding="utf-8")
    run = ComputeRunService().run_direct(
        technique=technique,
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={option_name: option},
    )
    assert run.status == "needs_input"
    assert any(option_name in reason for reason in run.reasons)


def test_tga_kinetics_rejects_curve_count_mismatch_even_for_existing_measurements(tmp_path: Path) -> None:
    source = tmp_path / "tga-mismatch.csv"
    source.write_text(
        "Temperature (C),Mass (%)\n25,100\n100,98\n200,90\n",
        encoding="utf-8",
    )
    run = ComputeRunService().run_direct(
        technique="tga",
        path=source,
        output_dir=tmp_path / "out",
        pipeline_options={
            "tga_kinetics": {
                "heating_rates": [10.0, 20.0],
                "curve_measurement_ids": ["sheet-0-table-0"],
            }
        },
    )
    assert run.status == "needs_input"
    assert run.reasons == ("tga_kinetics_invalid",)


@pytest.mark.parametrize(
    ("technique", "content", "option_name", "option", "cli_spec"),
    (
        (
            "tga",
            "Temperature (C),Mass (%)\n25,100\n100,98\n200,90\n300,50\n400,20\n",
            "tga_kinetics",
            {"heating_rates": [10.0, 20.0]},
            {"heating_rates": [10.0, 20.0]},
        ),
        (
            "dma",
            "Frequency (Hz),Storage Modulus (Pa)\n1,10\n10,20\n100,30\n",
            "dma_tts",
            {
                "reference_temperature": 25.0,
                "temperatures": [25.0],
                "shift_factors": [1.0],
                "curve_measurement_ids": ["sheet-0-table-0"],
            },
            {
                "reference_temperature": 25.0,
                "temperatures": [25.0],
                "shift_factors": [1.0],
                "curve_measurement_ids": ["sheet-0-table-0"],
            },
        ),
        (
            "rheology",
            "Time (s),Viscosity (Pa*s)\n0,10\n1,8\n2,6\n",
            "rheology_advanced",
            {"thixotropy_measurement_id": "sheet-0-table-0"},
            {"advanced": {"thixotropy_measurement_id": "sheet-0-table-0"}},
        ),
        (
            "mechanics",
            "Cycle,Force (N)\n1,10\n2,8\n3,7\n",
            "mechanics_advanced",
            {"cycle_measurement_id": "sheet-0-table-0"},
            {"advanced": {"cycle_measurement_id": "sheet-0-table-0"}},
        ),
    ),
)
def test_advanced_specs_share_cli_compute_projection(
    tmp_path: Path,
    capsys,
    technique: str,
    content: str,
    option_name: str,
    option: dict,
    cli_spec: dict,
) -> None:
    source = tmp_path / f"{technique}.csv"
    source.write_text(content, encoding="utf-8")
    direct = ComputeRunService().run_direct(
        technique=technique,
        path=source,
        output_dir=tmp_path / "direct",
        pipeline_options={option_name: option},
    )
    capsys.readouterr()
    spec_path = tmp_path / f"{technique}-analysis.json"
    spec_path.write_text(json.dumps(cli_spec), encoding="utf-8")

    assert run_single(
        SimpleNamespace(
            cmd=technique,
            input=str(source),
            output=str(tmp_path / "cli"),
            skip_to=None,
            analysis_spec=str(spec_path),
            json=True,
        )
    ) == 0

    cli = json.loads(capsys.readouterr().out)
    assert cli["canonical_template"]["content_hash"] == direct.canonical_template.content_hash
    direct_manifest = json.loads(
        json.dumps(direct.result.metric_manifest(source=str(source)))
    )
    assert cli["result"]["metric_manifest"] == direct_manifest
    assert set(cli["result"]["figures"]) == set(direct.result.figures)


@pytest.mark.parametrize(
    ("technique", "content", "option_name", "option", "metric_path"),
    (
        (
            "tga",
            "Temperature (C),Mass (%)\n25,100\n100,98\n200,90\n300,50\n400,20\n",
            "tga_kinetics",
            {"heating_rates": [10.0, 20.0]},
            "kinetics",
        ),
        (
            "dma",
            "Frequency (Hz),Storage Modulus (Pa)\n1,10\n10,20\n100,30\n",
            "dma_tts",
            {
                "reference_temperature": 25.0,
                "temperatures": [25.0],
                "shift_factors": [1.0],
                "curve_measurement_ids": ["sheet-0-table-0"],
            },
            "dma_tts.reference_temperature",
        ),
        (
            "rheology",
            "Time (s),Viscosity (Pa*s)\n0,10\n1,8\n2,6\n",
            "rheology_advanced",
            {"thixotropy_measurement_id": "sheet-0-table-0"},
            "rheology_advanced.thixotropy.area",
        ),
        (
            "mechanics",
            "Cycle,Force (N)\n1,10\n2,8\n3,7\n",
            "mechanics_advanced",
            {"cycle_measurement_id": "sheet-0-table-0"},
            "mechanics_advanced.cycles.peak_response",
        ),
    ),
)
def test_project_route_reuses_advanced_canonical_and_compute_projection(
    tmp_path: Path,
    technique: str,
    content: str,
    option_name: str,
    option: dict,
    metric_path: str,
) -> None:
    source = tmp_path / "raw" / technique.upper() / "sample.csv"
    source.parent.mkdir(parents=True)
    source.write_text(content, encoding="utf-8")
    direct = ComputeRunService().run_direct(
        technique=technique,
        path=source,
        output_dir=tmp_path / "direct",
        pipeline_options={option_name: option},
    )
    service = ProjectWorkflowService.open(tmp_path)
    request = AnalysisRequest.create(
        question=f"Analyze {technique} advanced diagnostic candidates",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
        parameters={"analysis_options": {option_name: option}},
    )

    run = service.run(request)

    assert run.status in {"completed", "review_required"}, run.reason_codes
    assert run.analysis_run is not None
    compute_run = run.analysis_run.steps[0].to_dict()["compute_run"]
    assert compute_run["canonical_template"]["content_hash"] == direct.canonical_template.content_hash
    direct_manifest = json.loads(
        json.dumps(direct.result.metric_manifest(source=str(source)))
    )
    assert compute_run["result"]["metric_manifest"] == direct_manifest
    manifest = {
        row["path"]: row for row in compute_run["result"]["metric_manifest"]
    }
    assert metric_path in manifest
    assert run.evidence_items
    evidence_compute = run.evidence_items[0].to_dict()["observed_results"][
        "result_summary"
    ]["compute_run"]
    assert evidence_compute["canonical_template"]["content_hash"] == direct.canonical_template.content_hash
    assert evidence_compute["result"]["metric_manifest"] == direct_manifest
