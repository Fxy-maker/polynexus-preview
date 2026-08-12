from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from polynexus.core.agent_workflow.models import InputArtifact
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


def test_index_drops_deleted_artifacts_but_keeps_existing_partial_scope(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    deleted = raw / "deleted.raw"
    retained = raw / "retained.raw"
    deleted.write_text("method_temperature_C=184\n", encoding="utf-8")
    retained.write_text("method_temperature_C=185\n", encoding="utf-8")
    indexer = ProjectIndexer(ProjectWorkspace.open(tmp_path))
    indexer.inspect([deleted, retained])
    deleted.unlink()

    index = indexer.inspect([retained])

    assert [artifact.relative_path for artifact in index.artifacts] == ["raw/retained.raw"]


def test_index_persists_missing_requested_input_as_blocked(tmp_path: Path) -> None:
    missing = tmp_path / "raw" / "DSC_185C.txt"

    index = ProjectIndexer(ProjectWorkspace.open(tmp_path)).inspect([missing])

    artifact = index.artifacts[0]
    assert artifact.sha256 is None
    assert artifact.inspection_status == "blocked"
    assert artifact.reason_codes == ("file_missing",)


def test_index_persists_hash_for_readable_artifact_with_unreadable_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "raw" / "WAXS_185C.edf"
    source.parent.mkdir()
    source.write_bytes(b"readable raw bytes")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    def blocked_header_inspection(path: Path, *, technique: str) -> InputArtifact:
        return InputArtifact(
            artifact_id="inspection-id",
            path=str(path),
            technique=technique,
            format="edf",
            sha256=source_hash,
            inspection_status="blocked",
            reason_codes=("header_unreadable",),
        )

    monkeypatch.setattr(
        "polynexus.core.project_workflow.index.inspect_artifact", blocked_header_inspection
    )
    workspace = ProjectWorkspace.open(tmp_path)
    graph = ProjectIndexer(workspace).inspect([source])
    persisted = json.loads((workspace.inventory_dir / "index.json").read_text(encoding="utf-8"))

    assert graph.artifacts[0].sha256 == source_hash
    assert graph.artifacts[0].inspection_status == "blocked"
    assert graph.artifacts[0].reason_codes == ("header_unreadable",)
    assert persisted["artifacts"][0]["sha256"] == source_hash
    assert persisted["artifacts"][0]["inspection_status"] == "blocked"
    assert persisted["artifacts"][0]["reason_codes"] == ["header_unreadable"]


@pytest.mark.parametrize("directory", ("notes", "manuscript"))
def test_index_rejects_context_documents_as_measurement_sources(
    tmp_path: Path, directory: str
) -> None:
    source = tmp_path / directory / "context.txt"
    source.parent.mkdir()
    source.write_text("method_temperature_C=185\n", encoding="utf-8")

    with pytest.raises(ValueError, match="raw"):
        ProjectIndexer(ProjectWorkspace.open(tmp_path)).inspect([source])
