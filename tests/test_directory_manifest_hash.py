from pathlib import Path

from polynexus.core.canonical_experiments.registry import default_converter_registry
from polynexus.core.compute.models import RawArtifact


def test_converter_directory_hash_matches_raw_artifact(tmp_path: Path) -> None:
    source = tmp_path / "series"
    source.mkdir()
    (source / "a.dat").write_bytes(b"1,2\n")

    artifact = RawArtifact.from_path(source, technique="saxs")
    outcome = default_converter_registry().convert_path(
        source,
        technique="saxs",
        source_artifact_id=artifact.artifact_id,
    )

    assert outcome.template is not None
    assert outcome.template.payload["source_sha256"] == artifact.sha256
