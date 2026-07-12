"""Canonical top-level workspace modes for the main GUI."""

from __future__ import annotations

from enum import Enum
from typing import Any


class WorkspaceMode(str, Enum):
    """User-facing workspaces that own navigation and action context."""

    ANALYSIS = "analysis"
    JOINT = "joint"
    SAMPLES = "samples"


def normalize_workspace_mode(value: Any) -> WorkspaceMode:
    """Normalize canonical values and legacy pseudo-workspace aliases."""

    if isinstance(value, WorkspaceMode):
        return value

    text = str(value or "").strip().lower()
    if not text:
        raise ValueError("Workspace mode is required")
    if text == WorkspaceMode.ANALYSIS.value:
        return WorkspaceMode.ANALYSIS
    if text == WorkspaceMode.SAMPLES.value:
        return WorkspaceMode.SAMPLES
    if text == WorkspaceMode.JOINT.value or text.startswith("joint."):
        return WorkspaceMode.JOINT
    raise ValueError(f"Unknown workspace mode: {value!r}")
