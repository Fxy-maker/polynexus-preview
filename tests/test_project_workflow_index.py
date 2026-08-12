from __future__ import annotations

import json
from pathlib import Path

from polynexus.core.project_workflow.index import ProjectIndexer
from polynexus.core.project_workflow.workspace import ProjectWorkspace


def test_index_preserves_raw_condition_when_filename_disagrees(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "WAXS_180C.raw"
    source.parent.mkdir()
    source.write_text("method_temperature_C=185\n", encoding="utf-8")

    index = ProjectIndexer(ProjectWorkspace.open(tmp_path)).inspect([source])

    artifact = index.artifacts[0]
    assert artifact.facts["condition.setpoint_C"].value == 185.0
    assert artifact.facts["condition.setpoint_C"].status == "verified_from_raw"
    assert "filename_value_disagrees" in artifact.discrepancies


def test_index_writes_raw_inventory_and_repeated_inspection_is_stable(tmp_path: Path) -> None:
    source = tmp_path / "raw" / "PA6_185C.raw"
    source.parent.mkdir()
    source.write_text("method_temperature_C=185\n", encoding="utf-8")
    workspace = ProjectWorkspace.open(tmp_path)
    indexer = ProjectIndexer(workspace)

    first = indexer.inspect([source])
    second = indexer.inspect([source])
    persisted = json.loads((workspace.inventory_dir / "index.json").read_text(encoding="utf-8"))

    assert first.graph_hash == second.graph_hash
    assert first.artifacts[0].sha256
    assert persisted["graph_hash"] == first.graph_hash


def test_index_orders_paths_deterministically(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    first = raw / "z-last.raw"
    second = raw / "a-first.raw"
    first.write_text("method_temperature_C=185\n", encoding="utf-8")
    second.write_text("method_temperature_C=184\n", encoding="utf-8")
    indexer = ProjectIndexer(ProjectWorkspace.open(tmp_path))

    index = indexer.inspect([first, second])

    assert [artifact.relative_path for artifact in index.artifacts] == [
        "raw/a-first.raw",
        "raw/z-last.raw",
    ]
