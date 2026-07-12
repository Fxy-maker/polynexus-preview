from __future__ import annotations

import pytest

from polynexus.gui.workspace_mode import WorkspaceMode, normalize_workspace_mode


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("analysis", WorkspaceMode.ANALYSIS),
        ("samples", WorkspaceMode.SAMPLES),
        (WorkspaceMode.ANALYSIS, WorkspaceMode.ANALYSIS),
        ("JOINT", WorkspaceMode.JOINT),
    ],
)
def test_normalize_workspace_mode_accepts_canonical_values(value, expected):
    assert normalize_workspace_mode(value) is expected


@pytest.mark.parametrize("value", ["joint", "joint.quick", "joint.compare"])
def test_normalize_workspace_mode_collapses_legacy_joint_aliases(value):
    assert normalize_workspace_mode(value) is WorkspaceMode.JOINT


def test_normalize_workspace_mode_rejects_unknown_values():
    with pytest.raises(ValueError, match="Unknown workspace mode"):
        normalize_workspace_mode("not-a-workspace")


def test_normalize_workspace_mode_rejects_empty_values():
    with pytest.raises(ValueError, match="Workspace mode is required"):
        normalize_workspace_mode("")
