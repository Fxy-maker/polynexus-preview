"""Project-local planning facade for Codex and ARS requests.

This module deliberately stops at provider/template selection.  Scientific
execution belongs to the existing agent-workflow providers and is implemented
by a later task.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from polynexus.core.agent_workflow import AgentWorkflowService
from polynexus.core.agent_workflow.models import AnalysisRecipe

from .evidence import ProjectWorkflowRun, evidence_items_from_run, stable_run_id
from .adapters import SingleInputTechniqueAdapter
from .index import ProjectIndexer
from .models import AnalysisRequest, ProjectPlan, ResearchGraph
from .package import ProjectEvidencePackager, ResearchEvidencePackage
from .workspace import ProjectWorkspace


_DSC_WORKFLOW = "tpae.characterization.v1"
_DSC_TEMPLATE = "dsc.isothermal.v1"
_SINGLE_WORKFLOW = SingleInputTechniqueAdapter.workflow_id


class ProjectWorkflowService:
    """Persisted project inventory and deterministic analysis-request planner."""

    def __init__(
        self,
        workspace: ProjectWorkspace,
        *,
        agent_service: AgentWorkflowService | None = None,
    ) -> None:
        self.workspace = workspace
        self.indexer = ProjectIndexer(workspace)
        self.agent_service = agent_service or AgentWorkflowService()
        self.single_input_adapter = SingleInputTechniqueAdapter()
        if self.agent_service.registry.get(_SINGLE_WORKFLOW) is None:
            self.agent_service.registry.register(self.single_input_adapter)

    @classmethod
    def open(cls, root: str | Path) -> "ProjectWorkflowService":
        return cls(ProjectWorkspace.open(root))

    def inspect(self, paths: Iterable[str | Path]) -> ResearchGraph:
        resolved = tuple(
            (self.workspace.root / path if not Path(path).is_absolute() else Path(path))
            for path in paths
        )
        return self.indexer.inspect(resolved)

    def plan(self, request: AnalysisRequest) -> ProjectPlan:
        """Resolve a request against inventory and select registered routes only."""
        scope_boundary_error = self._scope_boundary_error(request.data_scope)
        if scope_boundary_error:
            return self._persist_blocked_plan(request, scope_boundary_error)
        try:
            graph = self._load_or_discover(request.data_scope)
        except (ValueError, KeyError, TypeError, OSError, UnicodeError):
            return self._persist_blocked_plan(request, "inventory_invalid")
        scope_error = self._scope_error(graph, request.data_scope)
        if scope_error:
            return self._persist_blocked_plan(request, scope_error)
        artifacts = self._resolve_scope(graph, request.data_scope)
        techniques = sorted({artifact.technique for artifact in artifacts})
        if not techniques:
            techniques = self._techniques_from_scope(request.data_scope)
        if not techniques and self._request_mentions_dsc(request):
            techniques = ["dsc"]

        reason_codes: list[str] = []
        steps: list[dict[str, object]] = []
        if len(techniques) > 1:
            reason_codes.append("mixed_technique_inputs")
        for technique in techniques:
            selected = tuple(
                artifact for artifact in artifacts
                if artifact.technique == technique and artifact.inspection_status != "blocked"
            )
            blocked_count = sum(
                1 for artifact in artifacts
                if artifact.technique == technique and artifact.inspection_status == "blocked"
            )
            if blocked_count:
                reason_codes.append("artifact_blocked")
                if not selected:
                    steps.append({
                        "step_id": f"{technique}.blocked",
                        "technique": technique,
                        "status": "blocked",
                        "provider_id": None,
                        "template_id": None,
                        "artifact_paths": [
                            artifact.relative_path
                            for artifact in artifacts
                            if artifact.technique == technique
                        ],
                        "requested_outputs": list(request.requested_outputs),
                    })
                    continue
            if technique != "dsc":
                proposal = self.single_input_adapter.propose_recipe({
                    "workflow_id": _SINGLE_WORKFLOW,
                    "technique": technique,
                    "paths": [
                        str((self.workspace.root / artifact.relative_path).absolute())
                        for artifact in selected
                    ],
                })
                if proposal.recipe is None:
                    reason_codes.extend(proposal.reason_codes or ("adapter_blocked",))
                    step_id = f"{technique}.blocked"
                    step_status = "blocked"
                    provider_id = None
                    template_id = None
                else:
                    recipe_step = proposal.recipe.steps[0]
                    step_id = recipe_step.step_id
                    step_status = "review_required" if proposal.status == "review_required" else "ready"
                    provider_id = _SINGLE_WORKFLOW
                    template_id = str(recipe_step.parameters.get("submodule_id", ""))
                steps.append({
                    "step_id": step_id,
                    "technique": technique,
                    "status": step_status,
                    "provider_id": provider_id,
                    "template_id": template_id,
                    "artifact_paths": [artifact.relative_path for artifact in selected],
                    "requested_outputs": list(request.requested_outputs),
                })
                continue
            status = "review_required" if any(a.inspection_status == "review_required" for a in selected) else "ready"
            steps.append({
                "step_id": "dsc.isothermal",
                "technique": "dsc",
                "status": status,
                "provider_id": _DSC_WORKFLOW,
                "template_id": _DSC_TEMPLATE,
                "artifact_paths": [artifact.relative_path for artifact in selected],
                "requested_outputs": list(request.requested_outputs),
            })

        status = "blocked" if reason_codes else (
            "review_required" if any(step["status"] == "review_required" for step in steps) else "ready"
        )
        plan = ProjectPlan.create(
            request_hash=request.request_hash,
            steps=steps,
            status=status,
            reason_codes=tuple(sorted(set(reason_codes))),
            required_context=(),
        )
        self.workspace.write_json(self.workspace.requests_dir / f"{request.request_hash}.request.json", request.to_dict())
        self.workspace.write_json(self.workspace.requests_dir / f"{request.request_hash}.plan.json", plan.to_dict())
        return plan

    def run(self, request_or_plan: AnalysisRequest | ProjectPlan) -> ProjectWorkflowRun:
        """Execute a planned project request through existing agent providers."""
        if self.agent_service.registry.get(_SINGLE_WORKFLOW) is None:
            self.agent_service.registry.register(self.single_input_adapter)
        if isinstance(request_or_plan, AnalysisRequest):
            request = request_or_plan
            plan = self.plan(request)
        elif isinstance(request_or_plan, ProjectPlan):
            plan = request_or_plan
            request = self._load_request(plan.request_hash)
            if request is None:
                return self._blocked_project_run(plan, "request_manifest_missing")
            try:
                persisted_payload = self.workspace.read_json(
                    self.workspace.requests_dir / f"{plan.request_hash}.plan.json"
                )
                if persisted_payload is None:
                    return self._blocked_project_run(plan, "plan_manifest_missing")
                persisted_plan = ProjectPlan.from_dict(persisted_payload)
            except (ValueError, KeyError, TypeError, OSError, UnicodeError):
                persisted_plan = None
            if persisted_plan is None or (
                persisted_plan.plan_hash != plan.plan_hash
                or persisted_plan.to_dict() != plan.to_dict()
            ):
                return self._blocked_project_run(plan, "plan_manifest_mismatch")
        else:
            raise TypeError("run expects AnalysisRequest or ProjectPlan")

        if plan.status == "blocked":
            return self._blocked_project_run(plan, *plan.reason_codes)
        dsc_steps = tuple(step for step in plan.steps if step.get("technique") == "dsc")
        non_dsc_steps = tuple(step for step in plan.steps if step.get("technique") != "dsc")
        if non_dsc_steps:
            return self._run_single_technique(request, plan, non_dsc_steps)
        if not dsc_steps:
            return self._blocked_project_run(plan, "dsc_step_missing")
        source_paths = tuple(
            str((self.workspace.root / str(path)).absolute())
            for step in dsc_steps
            for path in step.get("artifact_paths", ())
        )
        if len(source_paths) != 1:
            return self._blocked_project_run(plan, "dsc_source_count_invalid")
        source = Path(source_paths[0])
        try:
            graph = self._load_or_discover(request.data_scope)
        except (ValueError, KeyError, TypeError, OSError, UnicodeError):
            return self._blocked_project_run(plan, "inventory_invalid")
        artifacts = {artifact.relative_path: artifact for artifact in graph.artifacts}
        relative_source = source.relative_to(self.workspace.root).as_posix()
        artifact = artifacts.get(relative_source)
        if artifact is None:
            return self._blocked_project_run(plan, "dsc_source_not_indexed")

        manifest = {
            "workflow_id": _DSC_WORKFLOW,
            "artifacts": {
                "dsc_isothermal": {
                    "path": str(source),
                    "technique": "dsc",
                }
            },
        }
        proposal = self.agent_service.propose_recipe(_DSC_WORKFLOW, manifest)
        if proposal.recipe is None:
            return self._blocked_project_run(plan, *proposal.reason_codes)
        recipe = proposal.recipe
        source_hashes = tuple(
            str(item.sha256) for item in recipe.artifacts if item.sha256
        )
        run_id = stable_run_id(request.request_hash, recipe.recipe_hash, source_hashes)
        output_dir = self.workspace.runs_dir / run_id
        raw_analysis_run = self.agent_service.run_recipe(recipe, output_dir)
        analysis_run = self.agent_service.validate_run(raw_analysis_run)
        limitations = tuple(
            dict.fromkeys(
                [
                    *analysis_run.reason_codes,
                    *(
                        analysis_run.evidence.disallowed_conclusions
                        if analysis_run.evidence
                        else ()
                    ),
                ]
            )
        )
        evidence_items = evidence_items_from_run(
            analysis_run,
            run_id=run_id,
            raw_sources=source_hashes,
            limitations=limitations,
        )
        outputs = self._derived_outputs(output_dir, analysis_run)
        manifest_payload = self._run_manifest(
            request=request,
            plan=plan,
            recipe=recipe,
            run=analysis_run,
            run_id=run_id,
            source_hashes=source_hashes,
            evidence_items=evidence_items,
            outputs=outputs,
        )
        manifest_path = self.workspace.write_json(
            self.workspace.runs_dir / f"{run_id}.json", manifest_payload
        )
        return ProjectWorkflowRun(
            run_id=run_id,
            request_hash=request.request_hash,
            plan_hash=plan.plan_hash,
            recipe_hash=recipe.recipe_hash,
            status=analysis_run.status,
            outputs=tuple(str(path) for path in outputs) + (str(manifest_path),),
            evidence_items=evidence_items,
            manifest_path=str(manifest_path),
            analysis_run=analysis_run,
            reason_codes=analysis_run.reason_codes,
        )

    def _run_single_technique(
        self,
        request: AnalysisRequest,
        plan: ProjectPlan,
        steps: tuple[Mapping[str, object], ...],
    ) -> ProjectWorkflowRun:
        """Execute exactly one registered IR/WAXS/SAXS input through the provider."""
        if len(steps) != 1:
            return self._blocked_project_run(plan, "mixed_technique_inputs")
        plan_step = steps[0]
        technique = str(plan_step.get("technique", "")).lower()
        paths = tuple(str(path) for path in plan_step.get("artifact_paths", ()))
        if len(paths) != 1:
            return self._blocked_project_run(plan, f"{technique}_source_count_invalid")
        source = (self.workspace.root / paths[0]).absolute()
        try:
            graph = self._load_or_discover(request.data_scope)
        except (ValueError, KeyError, TypeError, OSError, UnicodeError):
            return self._blocked_project_run(plan, "inventory_invalid")
        artifacts = {artifact.relative_path: artifact for artifact in graph.artifacts}
        relative_source = source.relative_to(self.workspace.root).as_posix()
        artifact = artifacts.get(relative_source)
        if artifact is None:
            return self._blocked_project_run(plan, "source_not_indexed")
        proposal = self.single_input_adapter.propose_recipe({
            "workflow_id": _SINGLE_WORKFLOW,
            "technique": technique,
            "paths": (str(source),),
        })
        if proposal.recipe is None:
            return self._blocked_project_run(plan, *proposal.reason_codes)
        recipe = proposal.recipe
        recipe_step = recipe.steps[0]
        if recipe_step.step_id != str(plan_step.get("step_id")):
            return self._blocked_project_run(plan, "recipe_step_mismatch")
        source_hashes = tuple(str(item.sha256) for item in recipe.artifacts if item.sha256)
        run_id = stable_run_id(request.request_hash, recipe.recipe_hash, source_hashes)
        output_dir = self.workspace.runs_dir / run_id
        analysis_run = self.agent_service.validate_run(
            self.agent_service.run_recipe(recipe, output_dir)
        )
        limitations = tuple(dict.fromkeys([
            *analysis_run.reason_codes,
            *(analysis_run.evidence.disallowed_conclusions if analysis_run.evidence else ()),
        ]))
        evidence_items = evidence_items_from_run(
            analysis_run,
            run_id=run_id,
            raw_sources=source_hashes,
            limitations=limitations,
        )
        outputs = self._derived_outputs(output_dir, analysis_run)
        manifest_payload = self._run_manifest(
            request=request,
            plan=plan,
            recipe=recipe,
            run=analysis_run,
            run_id=run_id,
            source_hashes=source_hashes,
            evidence_items=evidence_items,
            outputs=outputs,
        )
        manifest_path = self.workspace.write_json(
            self.workspace.runs_dir / f"{run_id}.json", manifest_payload
        )
        return ProjectWorkflowRun(
            run_id=run_id,
            request_hash=request.request_hash,
            plan_hash=plan.plan_hash,
            recipe_hash=recipe.recipe_hash,
            status=analysis_run.status,
            outputs=tuple(str(path) for path in outputs) + (str(manifest_path),),
            evidence_items=evidence_items,
            manifest_path=str(manifest_path),
            analysis_run=analysis_run,
            reason_codes=analysis_run.reason_codes,
        )

    def package(
        self,
        runs: Iterable[ProjectWorkflowRun] | ProjectWorkflowRun,
        *,
        relations: Iterable[Mapping[str, Any]] = (),
        package_id: str = "pa6-crystallization",
    ) -> ResearchEvidencePackage:
        """Materialize validated runs as an immutable ARS evidence snapshot."""
        values = (runs,) if isinstance(runs, ProjectWorkflowRun) else tuple(runs)
        return ProjectEvidencePackager(self.workspace).create(
            values,
            relations=relations,
            package_id=package_id,
        )

    def _persist_blocked_plan(self, request: AnalysisRequest, reason: str) -> ProjectPlan:
        plan = ProjectPlan.create(
            request_hash=request.request_hash,
            status="blocked",
            reason_codes=(reason,),
        )
        self.workspace.write_json(self.workspace.requests_dir / f"{request.request_hash}.request.json", request.to_dict())
        self.workspace.write_json(self.workspace.requests_dir / f"{request.request_hash}.plan.json", plan.to_dict())
        return plan

    def _load_request(self, request_hash: str) -> AnalysisRequest | None:
        payload = self.workspace.read_json(
            self.workspace.requests_dir / f"{request_hash}.request.json"
        )
        if payload is None:
            return None
        try:
            return AnalysisRequest.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return None

    def _blocked_project_run(self, plan: ProjectPlan, *reason_codes: str) -> ProjectWorkflowRun:
        codes = tuple(dict.fromkeys(str(code) for code in reason_codes if code))
        run_id = f"blocked-{plan.plan_hash[:24]}"
        payload = {
            "run_id": run_id,
            "request_hash": plan.request_hash,
            "plan_hash": plan.plan_hash,
            "recipe_hash": None,
            "source_hashes": [],
            "canonical_template_hashes": [],
            "conversion_hashes": [],
            "provider_version": (
                _DSC_WORKFLOW
                if all(str(step.get("technique")) == "dsc" for step in plan.steps)
                else _SINGLE_WORKFLOW
            ),
            "status": "blocked",
            "reason_codes": list(codes),
            "figures": [],
            "tables": [],
            "limitations": list(codes),
            "evidence_items": [],
        }
        path = self.workspace.write_json(self.workspace.runs_dir / f"{run_id}.json", payload)
        return ProjectWorkflowRun(
            run_id=run_id,
            request_hash=plan.request_hash,
            plan_hash=plan.plan_hash,
            recipe_hash=None,
            status="blocked",
            outputs=(str(path),),
            manifest_path=str(path),
            reason_codes=codes,
        )

    @staticmethod
    def _derived_outputs(output_dir: Path, run: Any) -> tuple[Path, ...]:
        outputs: list[Path] = []
        if output_dir.exists():
            outputs.extend(path for path in output_dir.rglob("*") if path.is_file())
        return tuple(sorted(set(outputs), key=lambda path: path.as_posix()))

    @staticmethod
    def _run_manifest(
        *,
        request: AnalysisRequest,
        plan: ProjectPlan,
        recipe: AnalysisRecipe,
        run: Any,
        run_id: str,
        source_hashes: tuple[str, ...],
        evidence_items: tuple[Any, ...],
        outputs: tuple[Path, ...],
    ) -> dict[str, Any]:
        canonical_hashes: list[str] = []
        conversion_hashes: list[str] = []
        figures: list[str] = []
        tables: list[str] = []
        for step in run.steps:
            summary = step.result_summary
            if summary.get("canonical_template_hash"):
                canonical_hashes.append(str(summary["canonical_template_hash"]))
            conversion = summary.get("canonical_conversion")
            if isinstance(conversion, Mapping) and conversion.get("conversion_hash"):
                conversion_hashes.append(str(conversion["conversion_hash"]))
            figures.extend(str(value) for value in step.figure_references.values() if isinstance(value, str))
        return {
            "run_id": run_id,
            "request_hash": request.request_hash,
            "plan_hash": plan.plan_hash,
            "recipe_hash": recipe.recipe_hash,
            "source_hashes": list(source_hashes),
            "canonical_template_hashes": list(dict.fromkeys(canonical_hashes)),
            "conversion_hashes": list(dict.fromkeys(conversion_hashes)),
            "provider_version": recipe.workflow_id,
            "status": run.status,
            "reason_codes": list(run.reason_codes),
            "figures": list(dict.fromkeys(figures)),
            "tables": tables,
            "limitations": list(dict.fromkeys(
                [*run.reason_codes, *[limit for item in evidence_items for limit in item.limitations]]
            )),
            "outputs": [str(path) for path in outputs],
            "evidence_items": [item.to_dict() for item in evidence_items],
            "analysis_run": run.to_dict(),
        }

    def _load_or_discover(self, scope: tuple[str, ...]) -> ResearchGraph:
        payload = self.workspace.read_json(self.workspace.inventory_dir / "index.json")
        if payload is not None:
            return ResearchGraph.from_dict(payload)
        paths: list[Path] = []
        candidates = scope or ("raw",)
        for item in candidates:
            candidate = (self.workspace.root / item).resolve()
            if candidate.is_dir():
                paths.extend(sorted(candidate.rglob("*"), key=lambda path: path.as_posix()))
            elif candidate.exists():
                paths.append(candidate)
        if paths:
            return self.inspect(paths)
        return ResearchGraph.create(study_id=f"project-{self.workspace.root.name or 'root'}")

    def _scope_error(self, graph: ResearchGraph, scope: tuple[str, ...]) -> str | None:
        if not scope:
            return None
        for item in scope:
            candidate = Path(item).expanduser()
            if ".." in candidate.parts:
                return "scope_outside_project"
            resolved = (candidate if candidate.is_absolute() else self.workspace.root / candidate).absolute()
            try:
                resolved.relative_to(self.workspace.root)
            except ValueError:
                return "scope_outside_project"
        if self.workspace.read_json(self.workspace.inventory_dir / "index.json") is None:
            return None
        if not graph.artifacts:
            return "scope_not_indexed"
        if not self._resolve_scope(graph, scope):
            return "scope_not_indexed"
        return None

    def _scope_boundary_error(self, scope: tuple[str, ...]) -> str | None:
        for item in scope:
            candidate = Path(item).expanduser()
            if ".." in candidate.parts:
                return "scope_outside_project"
            resolved = (candidate if candidate.is_absolute() else self.workspace.root / candidate).absolute()
            try:
                resolved.relative_to(self.workspace.root)
            except ValueError:
                return "scope_outside_project"
        return None

    @staticmethod
    def _resolve_scope(graph: ResearchGraph, scope: tuple[str, ...]):
        if not scope:
            return graph.artifacts
        normalized = tuple(Path(item).as_posix().rstrip("/") for item in scope)
        return tuple(
            artifact for artifact in graph.artifacts
            if any(artifact.relative_path == item or artifact.relative_path.startswith(item + "/") for item in normalized)
        )

    @staticmethod
    def _techniques_from_scope(scope: tuple[str, ...]) -> list[str]:
        text = " ".join(scope).lower()
        aliases = (("waxs", "waxs"), ("saxs", "saxs"), ("ftir", "ir"), ("ir", "ir"), ("dsc", "dsc"))
        return sorted({technique for marker, technique in aliases if marker in text})

    @staticmethod
    def _request_mentions_dsc(request: AnalysisRequest) -> bool:
        text = " ".join(
            (request.question, request.purpose, *request.requested_outputs, *request.data_scope)
        ).lower()
        return "dsc" in text or "avrami" in text or "crystall" in text or "结晶" in text


__all__ = ["ProjectWorkflowService"]
