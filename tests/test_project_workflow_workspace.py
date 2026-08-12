from __future__ import annotations

import json
from pathlib import Path

import pytest

from polynexus.core.project_workflow.workspace import ProjectWorkspace


def test_workspace_creates_only_polynexus_children(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.open(tmp_path)

    assert workspace.root == tmp_path.resolve()
    assert workspace.inventory_dir.parent == tmp_path / ".polynexus"
    assert not (tmp_path / "raw").exists()
    assert {path.name for path in workspace.derived_root.iterdir()} == {
        "inventory",
        "requests",
        "canonical",
        "runs",
        "figures",
        "evidence",
    }


@pytest.mark.parametrize("relative", ("../escape.json", "raw/result.json", "notes/result.json", "manuscript/result.json"))
def test_workspace_rejects_non_derived_output_paths(tmp_path: Path, relative: str) -> None:
    workspace = ProjectWorkspace.open(tmp_path)

    with pytest.raises(ValueError, match="project root|derived"):
        workspace.require_derived_path(tmp_path / relative)


def test_workspace_writes_json_atomically_under_derived_root(tmp_path: Path) -> None:
    workspace = ProjectWorkspace.open(tmp_path)
    destination = workspace.inventory_dir / "index.json"

    workspace.write_json(destination, {"schema": 1, "items": ["PA6"]})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"schema": 1, "items": ["PA6"]}
    assert not list(destination.parent.glob("*.tmp"))
