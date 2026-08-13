"""Project-local planning facade for Codex and ARS requests.

This module deliberately stops at provider/template selection.  Scientific
execution belongs to the existing agent-workflow providers and is implemented
by a later task.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from polynexus.core.agent_workflow import AgentWorkflowService, inspect_artifact
from polynexus.core.agent_workflow.models import AnalysisRecipe

from .evidence import ProjectAnalysisSummary, ProjectWorkflowRun, evidence_items_from_run, stable_run_id
from .adapters import SingleInputTechniqueAdapter, TechniqueSeriesAdapter
from .index import ProjectIndexer
from .grouping import CandidateExperimentGroup, candidate_groups
from .models import AnalysisRequest, ProjectPlan, ResearchGraph
from .package import ProjectEvidencePackager, ResearchEvidencePackage
from .workspace import ProjectWorkspace


_DSC_WORKFLOW = "tpae.characterization.v1"
_DSC_TEMPLATE = "dsc.isothermal.v1"
_SINGLE_WORKFLOW = SingleInputTechniqueAdapter.workflow_id
_SERIES_WORKFLOW = TechniqueSeriesAdapter.workflow_id


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
        self.series_adapter = TechniqueSeriesAdapter()
        if self.agent_service.registry.get(_SINGLE_WORKFLOW) is None:
            self.agent_service.registry.register(self.single_input_adapter)
        if self.agent_service.registry.get(_SERIES_WORKFLOW) is None:
            self.agent_service.registry.register(self.series_adapter)

    @classmethod
    def open(cls, root: str | Path) -> "ProjectWorkflowService":
        return cls(ProjectWorkspace.open(root))

    def inspect(self, paths: Iterable[str | Path]) -> ResearchGraph:
        resolved = tuple(
            (self.workspace.root / path if not Path(path).is_absolute() else Path(path))
            for path in paths
        )
        return self.indexer.inspect(resolved)

    def analyze_project(
        self,
        *,
        question: str,
        data_scope: Iterable[str | Path] = (),
        requested_outputs: Iterable[str] = ("figures", "tables", "writing_input"),
        package_id: str = "research-evidence",
    ) -> ProjectAnalysisSummary:
        """Run the ordinary project workflow through one AI/ARS-facing call."""
        scope = tuple(str(value) for value in data_scope)
        discovered, discovery_reasons = self._discover_project_files(scope)
        if not discovered:
            return self._analysis_summary((), (*discovery_reasons, "raw_data_missing"))
        try:
            graph = self.inspect(discovered)
        except (OSError, TypeError, ValueError, UnicodeError):
            return self._analysis_summary((), (*discovery_reasons, "inspection_invalid"))
        candidates = candidate_groups(graph.artifacts)
        selected_group = None
        if not scope:
            selected_group = candidates[0] if len(candidates) == 1 else self._select_candidate_group(candidates, question)
        if not scope and len(candidates) > 1 and selected_group is None:
            return ProjectAnalysisSummary(
                computation="blocked",
                data_quality="warning",
                publication="blocked",
                reason_codes=("candidate_group_selection_required",),
                messages=("Select one candidate experiment group before analysis; filenames are only inferred grouping hints.",),
                candidate_groups=tuple(group.to_dict() for group in candidates),
            )
        if selected_group is not None:
            graph_artifact_paths = set(selected_group.artifact_paths)
            graph = ResearchGraph.create(study_id=graph.study_id, artifacts=tuple(artifact for artifact in graph.artifacts if artifact.relative_path in graph_artifact_paths))
        grouped: dict[str, list[str]] = {}
        reasons: list[str] = list(discovery_reasons)
        for artifact in graph.artifacts:
            if artifact.technique in {"dsc", "ir", "waxs", "saxs"}:
                grouped.setdefault(artifact.technique, []).append(artifact.relative_path)
            else:
                reasons.extend(artifact.reason_codes or ("technique_unrecognized",))
        runs: list[ProjectWorkflowRun] = []
        for technique in sorted(grouped):
            request = AnalysisRequest.create(
                question=question,
                requested_outputs=tuple(requested_outputs),
                data_scope=tuple(sorted(grouped[technique])),
                parameters={"requested_by": "ai_native_project_entrypoint"},
            )
            result = self.run(request)
            if result.status in {"completed", "review_required"}:
                runs.append(result)
            else:
                reasons.extend(result.reason_codes)
        package: ResearchEvidencePackage | None = None
        if runs:
            try:
                package = self.package(tuple(runs), package_id=package_id)
            except (OSError, TypeError, ValueError, UnicodeError):
                reasons.append("evidence_package_failed")
        return self._analysis_summary(
            tuple(runs),
            tuple(reasons),
            package=package,
            candidate_groups=tuple(group.to_dict() for group in candidates),
            selected_group=selected_group.to_dict() if selected_group else None,
        )

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
                        "artifact_sha256": None,
                        "requested_outputs": list(request.requested_outputs),
                    })
                    continue
            if technique != "dsc":
                if len(selected) > 1:
                    proposal = self.series_adapter.propose_recipe({
                        "workflow_id": _SERIES_WORKFLOW,
                        "technique": technique,
                        "paths": [str((self.workspace.root / artifact.relative_path).absolute()) for artifact in selected],
                    })
                    if proposal.recipe is None:
                        reason_codes.extend(proposal.reason_codes or ("adapter_blocked",))
                        steps.append({"step_id": f"{technique}.series.blocked", "technique": technique, "status": "blocked", "provider_id": None, "template_id": None, "artifact_paths": [artifact.relative_path for artifact in selected], "artifact_sha256": [artifact.sha256 for artifact in selected]})
                    else:
                        steps.append({"step_id": "series", "technique": technique, "status": "review_required" if proposal.status == "review_required" else "ready", "provider_id": _SERIES_WORKFLOW, "template_id": str(proposal.recipe.steps[0].parameters.get("submodule_id", "")), "artifact_paths": [artifact.relative_path for artifact in selected], "artifact_sha256": [artifact.sha256 for artifact in selected], "source_order": list(range(len(proposal.recipe.artifacts)))})
                    continue
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
                    "artifact_sha256": selected[0].sha256 if len(selected) == 1 else None,
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
                "artifact_sha256": selected[0].sha256 if len(selected) == 1 else None,
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

    def _discover_project_files(self, scope: tuple[str, ...]) -> tuple[tuple[Path, ...], tuple[str, ...]]:
        candidates = scope or ("raw",)
        paths: list[Path] = []
        for item in candidates:
            source = (self.workspace.root / item if not Path(item).is_absolute() else Path(item)).absolute()
            try:
                source.relative_to(self.workspace.root)
            except ValueError:
                continue
            if source.is_file():
                paths.append(source)
            elif source.is_dir():
                paths.extend(path for path in source.rglob("*") if path.is_file())
        ordered = tuple(sorted(set(paths), key=lambda path: path.as_posix().lower()))
        if scope:
            return ordered, ()
        selected: list[Path] = []
        skipped_companions = 0
        seen_stems: set[str] = set()
        for path in ordered:
            stem_key = str(path.with_suffix("")).lower()
            if path.suffix.lower() in {".spc", ".spa"} and stem_key in seen_stems:
                skipped_companions += 1
                continue
            selected.append(path)
            seen_stems.add(stem_key)
        reasons = ("duplicate_format_skipped",) if skipped_companions else ()
        return tuple(selected), reasons

    @staticmethod
    def _analysis_summary(
        runs: tuple[ProjectWorkflowRun, ...],
        reason_codes: Iterable[str],
        *,
        package: ResearchEvidencePackage | None = None,
        candidate_groups: tuple[Mapping[str, Any], ...] = (),
        selected_group: Mapping[str, Any] | None = None,
    ) -> ProjectAnalysisSummary:
        reasons = tuple(dict.fromkeys(str(value) for value in reason_codes if value))
        if not runs:
            return ProjectAnalysisSummary(
                computation="blocked",
                data_quality="failed",
                publication="blocked",
                reason_codes=reasons or ("analysis_route_unavailable",),
                messages=("No usable analysis route was found. Check the raw files or ask for the missing condition.",),
                candidate_groups=candidate_groups,
                selected_group=selected_group,
            )
        review_bound = any(run.status == "review_required" for run in runs) or bool(reasons)
        publication = "review_required" if review_bound or package is None else "ready"
        messages = (
            "Analysis completed; figures, tables, and evidence package are ready for AI/ARS.",
            "Review-bound evidence has explicit limits; do not promote it to a manuscript conclusion automatically.",
        ) if review_bound else ("Analysis and evidence package are ready for AI/ARS.",)
        return ProjectAnalysisSummary(
            computation="passed",
            data_quality="warning" if review_bound else "passed",
            publication=publication,
            runs=runs,
            package=package.to_dict() if package else None,
            reason_codes=reasons,
            messages=messages,
            candidate_groups=candidate_groups,
            selected_group=selected_group,
        )

    @staticmethod
    def _select_candidate_group(
        candidates: tuple[CandidateExperimentGroup, ...],
        question: str,
    ) -> CandidateExperimentGroup | None:
        question_words = set(re.findall(r"[a-z0-9]+", question.lower()))
        requested_kind = (
            "time_min" if "time" in question_words else
            "temperature_C" if "temperature" in question_words else
            None
        )
        matches = [
            group for group in candidates
            if (requested_kind is None or group.condition_kind == requested_kind) and any(
                token in question_words and token not in {"c", "temperature", "time", "series"}
                for token in re.findall(r"[a-z0-9]+", group.label.lower())
            )
        ]
        return matches[0] if len(matches) == 1 else None

    def run(self, request_or_plan: AnalysisRequest | ProjectPlan) -> ProjectWorkflowRun:
        """Execute a planned project request through existing agent providers."""
        if self.agent_service.registry.get(_SINGLE_WORKFLOW) is None:
            self.agent_service.registry.register(self.single_input_adapter)
        if self.agent_service.registry.get(_SERIES_WORKFLOW) is None:
            self.agent_service.registry.register(self.series_adapter)
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
            if any(str(step.get("provider_id")) == _SERIES_WORKFLOW for step in non_dsc_steps):
                return self._run_series_technique(request, plan, non_dsc_steps)
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
        expected_hash = dsc_steps[0].get("artifact_sha256")
        if expected_hash and artifact.sha256 != expected_hash:
            return self._blocked_project_run(plan, "stale_plan_source_hash")
        current = inspect_artifact(source, technique="dsc")
        if current.sha256 != artifact.sha256:
            return self._blocked_project_run(plan, "source_hash_changed")

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

    def resume(self, run_id: str) -> ProjectWorkflowRun:
        """Replay a persisted request after validating its recorded sources."""
        payload = self.workspace.read_json(self.workspace.runs_dir / f"{str(run_id)}.json")
        if not isinstance(payload, Mapping) or payload.get("run_id") != str(run_id):
            return self._blocked_project_run(ProjectPlan.create(request_hash="resume-missing"), "run_manifest_missing")
        try:
            request = self._load_request(str(payload["request_hash"]))
            plan_payload = self.workspace.read_json(self.workspace.requests_dir / f"{payload['request_hash']}.plan.json")
            plan = ProjectPlan.from_dict(plan_payload) if isinstance(plan_payload, Mapping) else None
        except (KeyError, TypeError, ValueError, OSError, UnicodeError):
            request, plan = None, None
        if request is None or plan is None or plan.plan_hash != payload.get("plan_hash"):
            return self._blocked_project_run(plan or ProjectPlan.create(request_hash=str(payload.get("request_hash", "resume-invalid"))), "run_manifest_mismatch")
        for step in plan.steps:
            paths = tuple(str(path) for path in step.get("artifact_paths", ()))
            expected_values = step.get("artifact_sha256", ())
            if isinstance(expected_values, str):
                expected_values = (expected_values,)
            for path, expected in zip(paths, expected_values, strict=False):
                current = inspect_artifact(self.workspace.root / path, technique=str(step.get("technique", "unknown")))
                if expected and current.sha256 != str(expected):
                    return self._blocked_project_run(plan, "source_hash_changed")
        return self.run(plan)

    def approve_context_correction(
        self,
        request: AnalysisRequest,
        corrections: Mapping[str, Any],
        *,
        approved: bool = False,
        approver: str = "",
    ) -> AnalysisRequest:
        """Create a new request with explicit, auditable user-approved context."""
        if approved is not True or not isinstance(corrections, Mapping) or not corrections:
            raise ValueError("context correction requires explicit approval and non-empty mapping")
        if not str(approver).strip():
            raise ValueError("context correction approver is required")
        parameters = dict(request.parameters)
        parameters.update({"approved_context_corrections": dict(corrections), "approved_context_corrections_status": "approved", "approved_context_approver": str(approver)})
        return AnalysisRequest.create(question=request.question, purpose=request.purpose, requested_outputs=request.requested_outputs, data_scope=request.data_scope, context_sources=request.context_sources, parameters=parameters)

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
        expected_hash = plan_step.get("artifact_sha256")
        if expected_hash and artifact.sha256 != expected_hash:
            return self._blocked_project_run(plan, "stale_plan_source_hash")
        current = inspect_artifact(source, technique=technique)
        if current.sha256 != artifact.sha256:
            return self._blocked_project_run(plan, "source_hash_changed")
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

    def _run_series_technique(self, request: AnalysisRequest, plan: ProjectPlan, steps: tuple[Mapping[str, object], ...]) -> ProjectWorkflowRun:
        if len(steps) != 1:
            return self._blocked_project_run(plan, "mixed_technique_inputs")
        plan_step = steps[0]
        technique = str(plan_step.get("technique", "")).lower()
        paths = tuple(str(path) for path in plan_step.get("artifact_paths", ()))
        if len(paths) < 2:
            return self._blocked_project_run(plan, "series_source_count_invalid")
        source_paths = tuple((self.workspace.root / path).absolute() for path in paths)
        try:
            graph = self._load_or_discover(request.data_scope)
        except (ValueError, KeyError, TypeError, OSError, UnicodeError):
            return self._blocked_project_run(plan, "inventory_invalid")
        by_path = {artifact.relative_path: artifact for artifact in graph.artifacts}
        for path, expected in zip(paths, plan_step.get("artifact_sha256", ()), strict=False):
            artifact = by_path.get(path)
            if artifact is None or (expected and artifact.sha256 != expected):
                return self._blocked_project_run(plan, "stale_plan_source_hash")
            current = inspect_artifact(self.workspace.root / path, technique=technique)
            if current.sha256 != artifact.sha256:
                return self._blocked_project_run(plan, "source_hash_changed")
        proposal = self.series_adapter.propose_recipe({"workflow_id": _SERIES_WORKFLOW, "technique": technique, "paths": [str(path) for path in source_paths]})
        if proposal.recipe is None:
            return self._blocked_project_run(plan, *proposal.reason_codes)
        recipe = proposal.recipe
        run_id = stable_run_id(request.request_hash, recipe.recipe_hash, [artifact.sha256 for artifact in recipe.artifacts if artifact.sha256])
        output_dir = self.workspace.runs_dir / run_id
        analysis_run = self.agent_service.validate_run(self.agent_service.run_recipe(recipe, output_dir))
        limitations = tuple(dict.fromkeys([*analysis_run.reason_codes, *(analysis_run.evidence.disallowed_conclusions if analysis_run.evidence else ())]))
        evidence_items = evidence_items_from_run(analysis_run, run_id=run_id, raw_sources=[artifact.sha256 for artifact in recipe.artifacts if artifact.sha256], limitations=limitations)
        outputs = self._derived_outputs(output_dir, analysis_run)
        manifest_path = self.workspace.write_json(self.workspace.runs_dir / f"{run_id}.json", self._run_manifest(request=request, plan=plan, recipe=recipe, run=analysis_run, run_id=run_id, source_hashes=[artifact.sha256 for artifact in recipe.artifacts if artifact.sha256], evidence_items=evidence_items, outputs=outputs))
        return ProjectWorkflowRun(run_id=run_id, request_hash=request.request_hash, plan_hash=plan.plan_hash, recipe_hash=recipe.recipe_hash, status=analysis_run.status, outputs=tuple(str(path) for path in outputs) + (str(manifest_path),), evidence_items=evidence_items, manifest_path=str(manifest_path), analysis_run=analysis_run, reason_codes=analysis_run.reason_codes)

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
            "request_parameters": request.to_dict().get("parameters", {}),
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
