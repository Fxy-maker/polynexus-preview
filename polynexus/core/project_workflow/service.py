"""Project-local planning facade for Codex and ARS requests.

This module deliberately stops at provider/template selection.  Scientific
execution belongs to the existing agent-workflow providers and is implemented
by a later task.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .index import ProjectIndexer
from .models import AnalysisRequest, ProjectPlan, ResearchGraph
from .workspace import ProjectWorkspace


_DSC_WORKFLOW = "tpae.characterization.v1"
_DSC_TEMPLATE = "dsc.isothermal.v1"


class ProjectWorkflowService:
    """Persisted project inventory and deterministic analysis-request planner."""

    def __init__(self, workspace: ProjectWorkspace) -> None:
        self.workspace = workspace
        self.indexer = ProjectIndexer(workspace)

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
        graph = self._load_or_discover(request.data_scope)
        artifacts = self._resolve_scope(graph, request.data_scope)
        techniques = sorted({artifact.technique for artifact in artifacts})
        if not techniques:
            techniques = self._techniques_from_scope(request.data_scope)

        reason_codes: list[str] = []
        steps: list[dict[str, object]] = []
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
                reason_codes.append("converter_unregistered")
                steps.append({
                    "step_id": f"{technique}.unregistered",
                    "technique": technique,
                    "status": "blocked",
                    "provider_id": None,
                    "template_id": None,
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


__all__ = ["ProjectWorkflowService"]
