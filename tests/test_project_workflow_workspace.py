from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

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


def test_workspace_accepts_an_existing_ordinary_derived_directory(tmp_path: Path) -> None:
    derived_root = tmp_path / ".polynexus"
    derived_root.mkdir()

    workspace = ProjectWorkspace.open(tmp_path)

    assert workspace.derived_root == derived_root
    assert {path.name for path in derived_root.iterdir()} == {
        "inventory",
        "requests",
        "canonical",
        "runs",
        "figures",
        "evidence",
    }


def test_workspace_rejects_external_derived_link_before_creating_children(tmp_path: Path) -> None:
    external = tmp_path.parent / f"{tmp_path.name}-external-derived"
    external.mkdir()
    derived_link = tmp_path / ".polynexus"
    try:
        os.symlink(external, derived_link, target_is_directory=True)
    except OSError as exc:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(derived_link), str(external)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            pytest.skip(f"OS cannot create a directory link for this regression: {exc}")

    with pytest.raises(ValueError, match=r"\.polynexus.*project root"):
        ProjectWorkspace.open(tmp_path)

    assert list(external.iterdir()) == []


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
