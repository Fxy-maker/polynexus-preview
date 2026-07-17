import json
from pathlib import Path

from polynexus.core.figure_edit_persistence import (
    save_edit_bundle,
    try_save_edit_bundle,
)


def test_save_bundle_writes_asset_document_and_compatibility_state(tmp_path):
    target = tmp_path / "edited.png"

    result = save_edit_bundle(
        target,
        {"version": 1, "objects": []},
        b"new-image",
        {"font": "Small"},
        [],
    )

    assert result.ok is True
    assert result.target_path == target
    assert target.read_bytes() == b"new-image"
    assert result.document_path.exists()
    assert json.loads(result.document_path.read_text(encoding="utf-8"))["objects"] == []
    assert result.compatibility_path is not None
    assert result.compatibility_path.exists()


def test_save_failure_keeps_previous_target(tmp_path, monkeypatch):
    target = tmp_path / "edited.png"
    target.write_bytes(b"old-image")

    def fail_replace(self, _target):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", fail_replace)

    result = try_save_edit_bundle(target, {"version": 1, "objects": []}, b"new-image")

    assert result.ok is False
    assert result.error_code == "save_failed"
    assert target.read_bytes() == b"old-image"


def test_save_bundle_normalizes_document_before_writing(tmp_path):
    target = tmp_path / "edited.png"

    result = save_edit_bundle(
        target,
        {"version": "v1", "objects": None, "data_sources": None},
        b"image",
    )

    assert result.ok is True
    document = json.loads(result.document_path.read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert document["objects"] == []
    assert document["data_sources"] == []
