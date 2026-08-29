from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.engine import AnalysisResult
from polynexus.core.project_workflow.adapters import (
    IRTemperatureSeriesAdapter,
    MixedTechniqueAdapter,
    SingleInputTechniqueAdapter,
    TechniqueSeriesAdapter,
)
from polynexus.core.project_workflow.models import AnalysisRequest
from polynexus.core.project_workflow.service import ProjectWorkflowService


def _source(tmp_path: Path, technique: str, name: str = "sample.csv") -> Path:
    path = tmp_path / "raw" / technique.upper() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("q,I\n0.1,1\n0.2,2\n", encoding="utf-8")
    return path


def test_single_input_adapter_proposes_registered_static_recipe(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    proposal = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": "project.technique.single.v1",
        "technique": "waxs",
        "path": str(source),
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.workflow_id == "project.technique.single.v1"
    assert proposal.recipe.steps[0].step_id == "waxs_profile"
    assert proposal.recipe.steps[0].parameters["submodule_id"] == "waxs.static"
    assert proposal.recipe.steps[0].parameters["canonical_converter"] == "generic.one-dimensional.v1"
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == "scattering_1d.v1"


def test_single_input_adapter_binds_waxs_detector_image_template(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "WAXS" / "frame.tif"
    source.parent.mkdir(parents=True)
    Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4)).save(source)

    proposal = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": SingleInputTechniqueAdapter.workflow_id,
        "technique": "waxs",
        "path": str(source),
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == "waxs.detector_image.v1"
    assert SingleInputTechniqueAdapter.is_valid_recipe(proposal.recipe)


def test_technique_series_adapter_binds_detector_image_templates_per_frame(tmp_path: Path) -> None:
    paths = []
    for index in range(2):
        source = tmp_path / "raw" / "SAXS" / f"frame-{index}.tif"
        source.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4) + index).save(source)
        paths.append(str(source))

    proposal = TechniqueSeriesAdapter().propose_recipe({
        "workflow_id": TechniqueSeriesAdapter.workflow_id,
        "technique": "saxs",
        "paths": paths,
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert [
        step.parameters["canonical_template"]["template_id"]
        for step in proposal.recipe.steps
    ] == ["saxs.detector_image.v1", "saxs.detector_image.v1"]
    assert TechniqueSeriesAdapter.is_valid_recipe(proposal.recipe)


def test_single_input_adapter_requires_explicit_nmr_submodule_and_binds_it(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "NMR" / "spectrum.csv"
    source.parent.mkdir(parents=True)
    source.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")

    blocked = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": SingleInputTechniqueAdapter.workflow_id,
        "technique": "nmr",
        "path": str(source),
    })
    assert blocked.status == "blocked"
    assert blocked.reason_codes == ("nmr_submodule_required",)

    proposal = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": SingleInputTechniqueAdapter.workflow_id,
        "technique": "nmr",
        "submodule_id": "nmr.liquid_h",
        "path": str(source),
    })
    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert proposal.recipe.steps[0].parameters["submodule_id"] == "nmr.liquid_h"
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == "nmr.spectrum.v1"
    assert SingleInputTechniqueAdapter.is_valid_recipe(proposal.recipe)


def test_single_input_adapter_accepts_all_four_nmr_modes(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "NMR" / "spectrum.csv"
    source.parent.mkdir(parents=True)
    source.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")
    adapter = SingleInputTechniqueAdapter()

    for submodule in ("nmr.liquid_h", "nmr.liquid_c", "nmr.solid_h", "nmr.solid_c"):
        proposal = adapter.propose_recipe({
            "workflow_id": adapter.workflow_id,
            "technique": "nmr",
            "submodule_id": submodule,
            "path": str(source),
        })
        assert proposal.status == "ready"
        assert proposal.recipe is not None
        assert proposal.recipe.steps[0].parameters["submodule_id"] == submodule
    assert proposal.recipe.steps[0].parameters["canonical_template"]["source_artifact_id"] == proposal.recipe.artifacts[0].artifact_id


def test_single_input_adapter_blocks_unsupported_and_multiple_inputs(tmp_path: Path) -> None:
    adapter = SingleInputTechniqueAdapter()
    unsupported = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "nmr",
        "path": str(_source(tmp_path, "nmr", "sample.dat")),
    })
    multiple = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "saxs",
        "paths": [str(_source(tmp_path, "saxs", "a.dat")), str(_source(tmp_path, "saxs", "b.dat"))],
    })

    assert unsupported.status == "blocked"
    assert unsupported.reason_codes == ("nmr_submodule_required",)
    assert multiple.status == "blocked"
    assert multiple.reason_codes == ("multiple_artifacts",)


def test_single_recipe_without_canonical_template_is_invalid(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    proposal = SingleInputTechniqueAdapter().propose_recipe({
        "workflow_id": "project.technique.single.v1",
        "technique": "waxs",
        "path": str(source),
    })

    assert proposal.recipe is not None
    step = proposal.recipe.steps[0]
    invalid = replace(
        proposal.recipe,
        steps=(replace(step, parameters={"submodule_id": "waxs.static"}),),
    )

    run = AgentWorkflowService().run_recipe(invalid, tmp_path / "derived")

    assert run.status == "blocked"
    assert run.reason_codes == ("recipe_invalid",)


def test_project_plan_uses_single_input_adapter_for_waxs(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect((source,))
    plan = service.plan(AnalysisRequest.create(
        question="Analyze WAXS profile",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert plan.status == "ready", (plan.status, plan.reason_codes, plan.steps)
    assert plan.reason_codes == ()
    assert plan.steps[0]["provider_id"] == "project.technique.single.v1"
    assert plan.steps[0]["template_id"] == "waxs.static"


def test_project_run_delegates_single_waxs_input_to_existing_service(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")
    calls: list[str] = []

    def provider(step, artifact, output_dir):
        calls.append(step.technique)
        return AnalysisResult(technique=step.technique, validation_passed=True)

    agent = AgentWorkflowService(provider_runner=provider)
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = agent
    service.inspect((source,))
    result = service.run(AnalysisRequest.create(
        question="Analyze WAXS profile",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert result.status == "review_required", (result.status, result.reason_codes)
    assert calls == ["waxs"]
    assert result.evidence_items[0].technique == "waxs"
    assert result.analysis_run is not None
    assert result.analysis_run.recipe.steps[0].parameters["submodule_id"] == "waxs.static"


def test_project_run_step_exposes_shared_compute_run_projection(tmp_path: Path) -> None:
    source = _source(tmp_path, "waxs")

    def provider(step, artifact, output_dir):
        return AnalysisResult(
            technique=step.technique,
            validation_passed=True,
            parameters={"peak": 1.0},
        )

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=provider)
    service.inspect((source,))
    result = service.run(AnalysisRequest.create(
        question="Analyze WAXS profile",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert result.analysis_run is not None
    step = result.analysis_run.steps[0]
    assert step.compute_run["status"] == "completed"
    assert step.compute_run["artifact"]["sha256"]
    assert step.compute_run["canonical_template"]["template_id"] == "scattering_1d.v1"
    assert step.compute_run["capability_items"]
    assert step.compute_run["result"]["metrics"] == {"peak": 1.0}
    assert step.result_summary["compute_run"]["result"]["metric_manifest"]


def test_ir_directory_alias_is_indexed_as_ir_and_stale_source_blocks_run(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "series"
    source.mkdir(parents=True)
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,1\n", encoding="utf-8")
    service = ProjectWorkflowService.open(tmp_path)
    graph = service.inspect((source,))
    assert graph.artifacts[0].technique == "ir"
    plan = service.plan(AnalysisRequest.create(
        question="Analyze IR",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))
    (source / "20C.csv").write_text("wavenumber,intensity\n1000,2\n", encoding="utf-8")
    result = service.run(plan)
    assert result.status == "blocked"
    assert "source_hash_changed" in result.reason_codes


def test_series_adapter_orders_paths_and_binds_each_step(tmp_path: Path) -> None:
    paths = [_source(tmp_path, "waxs", name) for name in ("b.dat", "a.dat")]
    adapter = TechniqueSeriesAdapter()
    proposal = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "waxs",
        "paths": [str(path) for path in paths],
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert [step.parameters["artifact_index"] for step in proposal.recipe.steps] == [0, 1]
    assert [Path(item.path).name for item in proposal.recipe.artifacts] == ["a.dat", "b.dat"]
    assert all(step.parameters["canonical_converter"] == "generic.one-dimensional.v1" for step in proposal.recipe.steps)
    assert all(step.parameters["canonical_template"]["template_id"] == "scattering_1d.v1" for step in proposal.recipe.steps)
    assert TechniqueSeriesAdapter.is_valid_recipe(proposal.recipe)


def test_series_adapter_requires_at_least_two_same_technique_inputs(tmp_path: Path) -> None:
    adapter = TechniqueSeriesAdapter()
    one = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "saxs",
        "paths": [str(_source(tmp_path, "saxs", "a.dat"))],
    })
    mixed = adapter.propose_recipe({
        "workflow_id": adapter.workflow_id,
        "technique": "saxs",
        "paths": [str(_source(tmp_path, "saxs", "a.dat")), str(_source(tmp_path, "ir", "b.dat"))],
    })

    assert one.status == "blocked"
    assert one.reason_codes == ("series_requires_multiple_artifacts",)
    assert mixed.status == "blocked"
    assert mixed.reason_codes == ("series_technique_mismatch",)


def test_project_series_run_binds_each_file_in_stable_order(tmp_path: Path) -> None:
    paths = [_source(tmp_path, "waxs", name) for name in ("b.dat", "a.dat")]
    calls: list[str] = []

    def provider(step, artifact, output_dir):
        calls.append(Path(artifact.path).name)
        return AnalysisResult(technique=step.technique, validation_passed=True)

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=provider)
    service.inspect(paths)
    result = service.run(AnalysisRequest.create(question="Analyze WAXS series", data_scope=("raw/WAXS",)))

    assert result.status == "review_required"
    assert calls == ["a.dat", "b.dat"]
    assert result.analysis_run is not None
    assert [step.parameters["artifact_index"] for step in result.analysis_run.recipe.steps] == [0, 1]


def test_ir_temperature_series_adapter_builds_one_directory_bound_step(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "temperature"
    source.mkdir(parents=True)
    for name, value in (("PA6-100C.csv", 0.2), ("PA6-120C.csv", 0.4)):
        (source / name).write_text(
            "wavenumber,absorbance\n1000,1\n1010,2\n1020," + str(value) + "\n",
            encoding="utf-8",
        )

    proposal = IRTemperatureSeriesAdapter().propose_recipe({
        "workflow_id": IRTemperatureSeriesAdapter.workflow_id,
        "path": str(source),
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert len(proposal.recipe.artifacts) == 1
    assert proposal.recipe.artifacts[0].format == "directory"
    assert len(proposal.recipe.steps) == 1
    assert proposal.recipe.steps[0].parameters["submodule_id"] == "ir.temperature_2d"
    assert proposal.recipe.steps[0].parameters["canonical_template"]["template_id"] == "ir.temperature_series.v1"
    assert IRTemperatureSeriesAdapter.is_valid_recipe(proposal.recipe)


def test_ir_temperature_series_adapter_blocks_directory_without_two_frames(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "temperature"
    source.mkdir(parents=True)
    (source / "PA6-100C.csv").write_text(
        "wavenumber,absorbance\n1000,1\n1010,2\n1020,3\n",
        encoding="utf-8",
    )

    proposal = IRTemperatureSeriesAdapter().propose_recipe({
        "workflow_id": IRTemperatureSeriesAdapter.workflow_id,
        "path": str(source),
    })

    assert proposal.recipe is None
    assert proposal.status == "blocked"
    assert proposal.reason_codes == ("temperature_series_template_missing",)


def test_project_plan_uses_one_ir_temperature_series_directory_step(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "temperature"
    source.mkdir(parents=True)
    for name, value in (("PA6-100C.csv", 0.2), ("PA6-120C.csv", 0.4)):
        (source / name).write_text(
            "wavenumber,absorbance\n1000,1\n1010,2\n1020," + str(value) + "\n",
            encoding="utf-8",
        )
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect((source,))

    plan = service.plan(AnalysisRequest.create(
        question="Analyze IR temperature series",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert plan.status == "ready"
    assert len(plan.steps) == 1
    assert plan.steps[0]["provider_id"] == IRTemperatureSeriesAdapter.workflow_id
    assert tuple(plan.steps[0]["artifact_paths"]) == (source.relative_to(tmp_path).as_posix(),)


def test_project_plan_preserves_explicit_nmr_submodule(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "NMR" / "liquid_h.csv"
    source.parent.mkdir(parents=True)
    source.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect((source,))

    blocked = service.plan(AnalysisRequest.create(
        question="Analyze NMR",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))
    assert blocked.status == "blocked"

    plan = service.plan(AnalysisRequest.create(
        question="Analyze liquid proton NMR",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
        parameters={"submodule_id": "nmr.liquid_h"},
    ))
    assert plan.status == "ready"
    assert plan.steps[0]["template_id"] == "nmr.liquid_h"


def test_project_plan_routes_detector_image_series_through_series_adapter(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw" / "SAXS"
    source_dir.mkdir(parents=True)
    for index in range(2):
        Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4) + index).save(
            source_dir / f"frame-{index}.tif"
        )
    service = ProjectWorkflowService.open(tmp_path)
    service.inspect(tuple(source_dir.glob("*.tif")))

    plan = service.plan(AnalysisRequest.create(
        question="Analyze SAXS detector sequence",
        data_scope=tuple(path.relative_to(tmp_path).as_posix() for path in sorted(source_dir.glob("*.tif"))),
    ))

    assert plan.status == "ready"
    assert len(plan.steps) == 1
    assert plan.steps[0]["provider_id"] == TechniqueSeriesAdapter.workflow_id


def test_project_run_preserves_detector_templates_for_each_series_frame(tmp_path: Path) -> None:
    source_dir = tmp_path / "raw" / "WAXS"
    source_dir.mkdir(parents=True)
    for index in range(2):
        Image.fromarray(np.arange(12, dtype=np.uint16).reshape(3, 4) + index).save(
            source_dir / f"frame-{index}.tif"
        )
    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(
        provider_runner=lambda step, artifact, output: AnalysisResult(
            technique=step.technique, validation_passed=True,
        )
    )
    service.inspect(tuple(source_dir.glob("*.tif")))
    result = service.run(AnalysisRequest.create(
        question="Analyze WAXS detector sequence",
        data_scope=tuple(path.relative_to(tmp_path).as_posix() for path in sorted(source_dir.glob("*.tif"))),
    ))

    assert result.status == "review_required"
    assert result.analysis_run is not None
    assert [
        step.compute_run["canonical_template"]["template_id"]
        for step in result.analysis_run.steps
    ] == ["waxs.detector_image.v1", "waxs.detector_image.v1"]


def test_project_run_executes_ir_temperature_series_as_one_compute_step(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "IR" / "temperature"
    source.mkdir(parents=True)
    for name, value in (("PA6-100C.csv", 0.2), ("PA6-120C.csv", 0.4)):
        (source / name).write_text(
            "wavenumber,absorbance\n1000,1\n1010,2\n1020," + str(value) + "\n",
            encoding="utf-8",
        )
    calls: list[str] = []

    def provider(step, artifact, output_dir):
        calls.append(Path(artifact.path).name)
        return AnalysisResult(
            technique=step.technique,
            validation_passed=True,
            parameters={"n_frames": 2, "matrix_shape": [2, 3]},
        )

    service = ProjectWorkflowService.open(tmp_path)
    service.agent_service = AgentWorkflowService(provider_runner=provider)
    service.inspect((source,))
    result = service.run(AnalysisRequest.create(
        question="Analyze IR temperature series",
        data_scope=(source.relative_to(tmp_path).as_posix(),),
    ))

    assert result.status == "review_required", (result.status, result.reason_codes)
    assert calls == ["temperature"]
    assert result.analysis_run is not None
    assert len(result.analysis_run.recipe.steps) == 1
    assert result.analysis_run.recipe.steps[0].parameters["canonical_template"]["template_id"] == "ir.temperature_series.v1"
    assert result.analysis_run.steps[0].compute_run["canonical_template"]["template_id"] == "ir.temperature_series.v1"


def test_mixed_adapter_routes_ir_directory_to_temperature_series_template(tmp_path: Path) -> None:
    ir_source = tmp_path / "raw" / "IR" / "temperature"
    ir_source.mkdir(parents=True)
    for name, value in (("PA6-100C.csv", 0.2), ("PA6-120C.csv", 0.4)):
        (ir_source / name).write_text(
            "wavenumber,absorbance\n1000,1\n1010,2\n1020," + str(value) + "\n",
            encoding="utf-8",
        )
    waxs_source = _source(tmp_path, "waxs", "profile.dat")

    proposal = MixedTechniqueAdapter().propose_recipe({
        "workflow_id": MixedTechniqueAdapter.workflow_id,
        "components": {"ir": str(ir_source), "waxs": str(waxs_source)},
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert MixedTechniqueAdapter.is_valid_recipe(proposal.recipe)
    ir_steps = [step for step in proposal.recipe.steps if step.technique == "ir"]
    assert len(ir_steps) == 1
    assert ir_steps[0].parameters["submodule_id"] == "ir.temperature_2d"
    assert ir_steps[0].parameters["canonical_template"]["template_id"] == "ir.temperature_series.v1"


def test_mixed_adapter_preserves_explicit_nmr_submodule(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "NMR" / "liquid_h.csv"
    source.parent.mkdir(parents=True)
    source.write_text("ppm,intensity\n1.0,2\n1.5,3\n", encoding="utf-8")
    waxs_source = _source(tmp_path, "waxs", "profile.dat")

    proposal = MixedTechniqueAdapter().propose_recipe({
        "workflow_id": MixedTechniqueAdapter.workflow_id,
        "components": {
            "nmr": {"paths": [str(source)], "submodule_id": "nmr.liquid_h"},
            "waxs": str(waxs_source),
        },
    })

    assert proposal.status == "ready"
    assert proposal.recipe is not None
    assert MixedTechniqueAdapter.is_valid_recipe(proposal.recipe)
    nmr_steps = [step for step in proposal.recipe.steps if step.technique == "nmr"]
    assert len(nmr_steps) == 1
    assert nmr_steps[0].parameters["submodule_id"] == "nmr.liquid_h"
