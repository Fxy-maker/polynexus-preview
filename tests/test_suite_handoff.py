import json
from pathlib import Path
from types import SimpleNamespace

from polynexus.suite import handoff


def test_handoff_references_existing_package_files_without_copying(tmp_path: Path, monkeypatch):
    for name in ("manifest.json", "ars-writing-input.json", "result-tables.json", "writing-evidence.json", "citation-metrics.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    view = SimpleNamespace(package_id="demo", version=1, status="review_required", human_review=("one",), techniques=(SimpleNamespace(key="dsc"),), run_ids=("run-1",), metrics=(1,))
    monkeypatch.setattr(handoff, "load_evidence_package_view", lambda root: view)
    result = handoff.build_suite_handoff(tmp_path)
    assert result["status"] == "ready"
    assert result["files"]["ars_writing_input"] == "ars-writing-input.json"
    assert result["human_review_required"] is True
    assert not (tmp_path / "handoff-copy.json").exists()


def test_handoff_blocks_invalid_package(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(handoff, "load_evidence_package_view", lambda root: (_ for _ in ()).throw(ValueError("bad")))
    result = handoff.build_suite_handoff(tmp_path)
    assert result["status"] == "blocked"
    assert result["reason_codes"] == ["evidence_package_invalid"]
