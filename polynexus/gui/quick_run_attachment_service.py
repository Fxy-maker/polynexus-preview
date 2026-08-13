"""GUI-facing adapter for attaching an already-persisted run to a project."""

from __future__ import annotations

from pathlib import Path

from ..core.project_workflow.service import ProjectWorkflowService
from .workspace_context import WorkspaceContext, WorkspaceResultStatus


def attach_current_run_to_project(
    context: WorkspaceContext,
    project_root: str | Path,
):
    """Attach the active completed run by reference without rerunning or copying data."""
    if not isinstance(context, WorkspaceContext):
        raise ValueError("completed run context is required")
    if (
        context.result_status is not WorkspaceResultStatus.COMPLETE
        or not context.run_id
        or not context.technique
        or not context.source_path
    ):
        raise ValueError("completed run context is required")
    return ProjectWorkflowService.open(project_root).attach_quick_run(
        quick_run_id=context.run_id,
        technique=context.technique,
        source_file=context.source_path,
        output_dir=context.output_dir,
    )


__all__ = ["attach_current_run_to_project"]
