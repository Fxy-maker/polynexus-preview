"""Registry for narrow, manifest-driven agent workflow adapters."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from .models import RecipeProposal


class WorkflowAdapter(Protocol):
    workflow_id: str

    def propose_recipe(self, manifest: Mapping[str, object] | Path | str) -> RecipeProposal:
        """Return a deterministic recipe proposal or structured blocking reason."""


class WorkflowRegistry:
    """Explicit workflow registration keeps agent capabilities discoverable."""

    def __init__(self) -> None:
        self._adapters: dict[str, WorkflowAdapter] = {}

    def register(self, adapter: WorkflowAdapter) -> None:
        self._adapters[adapter.workflow_id] = adapter

    def get(self, workflow_id: str) -> WorkflowAdapter | None:
        return self._adapters.get(str(workflow_id))
