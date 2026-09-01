from pathlib import Path
from types import SimpleNamespace

import hashlib

from polynexus.suite import handoff
from polynexus.core.project_workflow.models import canonical_json


def test_handoff_references_existing_package_files_without_copying(tmp_path: Path, monkeypatch):
    for name in (
        "manifest.json",
        "ars-writing-input.json",
        "result-tables.json",
        "writing-evidence.json",
        "evidence.json",
        "citation-metrics.json",
        "figure-index.json",
    ):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    view = SimpleNamespace(package_id="demo", version=1, status="review_required", human_review=("one",), techniques=(SimpleNamespace(key="dsc"),), run_ids=("run-1",), metrics=(1,))
    monkeypatch.setattr(handoff, "load_evidence_package_view", lambda root: view)
    result = handoff.build_suite_handoff(tmp_path)
    assert result["status"] == "ready"
    assert result["files"]["ars_writing_input"] == "ars-writing-input.json"
    assert result["files"]["evidence"] == "evidence.json"
    assert result["files"]["figure_index"] == "figure-index.json"
    assert result["human_review_required"] is True
    assert not (tmp_path / "handoff-copy.json").exists()


def test_handoff_blocks_invalid_package(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(handoff, "load_evidence_package_view", lambda root: (_ for _ in ()).throw(ValueError("bad")))
    result = handoff.build_suite_handoff(tmp_path)
    assert result["status"] == "blocked"
    assert result["reason_codes"] == ["evidence_package_invalid"]


def test_package_integrity_hashes_large_artifacts_incrementally(tmp_path: Path, monkeypatch):
    required = {
        "ars-writing-input.json": "{}",
        "result-tables.json": "{}",
        "writing-evidence.json": "{}",
        "evidence.json": "{}",
        "citation-metrics.json": "{}",
        "figure-index.json": "{}",
        "payload.bin": "x" * (2 * 1024 * 1024 + 37),
    }
    for name, content in required.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    artifact_hashes = [
        {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for path in sorted(tmp_path.iterdir())
        if path.is_file()
    ]
    unsigned = {
        "package_id": "large",
        "version": 1,
        "run_ids": [],
        "artifact_hashes": artifact_hashes,
    }
    (tmp_path / "manifest.json").write_text(
        canonical_json(
            {
                **unsigned,
                "package_hash": hashlib.sha256(
                    canonical_json(unsigned).encode("utf-8")
                ).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    view = type(
        "View",
        (),
        {
            "package_id": "large",
            "version": 1,
            "status": "completed",
            "human_review": (),
            "techniques": (),
            "run_ids": (),
            "metrics": (),
        },
    )()
    monkeypatch.setattr(handoff, "load_evidence_package_view", lambda root: view)

    original_read_bytes = Path.read_bytes

    def reject_large_read(path: Path) -> bytes:
        if path.name == "payload.bin":
            raise AssertionError("large artifact must not be read as one buffer")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", reject_large_read)
    assert handoff.build_suite_handoff(tmp_path)["status"] == "ready"
