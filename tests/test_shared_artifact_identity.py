from __future__ import annotations

from pathlib import Path

from polynexus.core.agent_workflow import inspect_artifact
from polynexus.core.compute.models import RawArtifact


def test_agent_and_compute_share_ready_artifact_identity(tmp_path: Path) -> None:
    source = tmp_path / "curve.csv"
    source.write_text("x,y\n1,2\n2,3\n", encoding="utf-8")

    inspected = inspect_artifact(source, technique="ir")
    direct = RawArtifact.from_path(source, technique="ir")

    assert inspected.artifact_id == direct.artifact_id
    assert inspected.path == direct.path
    assert inspected.sha256 == direct.sha256
