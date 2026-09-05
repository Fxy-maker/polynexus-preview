from __future__ import annotations

import json
from pathlib import Path

from scripts.validation_pack import load_manifest, validate_manifest


MANIFEST = Path(__file__).parents[1] / "docs" / "validation" / "public-validation-pack.json"


def test_public_validation_manifest_is_valid_without_local_data() -> None:
    payload = load_manifest(MANIFEST)
    assert validate_manifest(payload) == []
    assert len(payload["entries"]) >= 10


def test_manifest_requires_license_and_checksum() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["entries"][0]["license_verified"] = False
    payload["entries"][0]["source_checksum"] = {}
    errors = validate_manifest(payload)
    assert any("license_verified" in error for error in errors)
    assert any("source_checksum" in error for error in errors)


def test_manifest_rejects_path_escape() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["entries"][0]["local_relative_path"] = "../outside.zip"
    assert any("local_relative_path" in error for error in validate_manifest(payload))


def test_require_local_detects_missing_archive(tmp_path: Path) -> None:
    payload = load_manifest(MANIFEST)
    errors = validate_manifest(payload, data_root=tmp_path, require_local=True)
    assert len(errors) == len(payload["entries"])
    assert all("local file is missing" in error for error in errors)


def test_require_local_rejects_present_but_corrupted_archive(tmp_path: Path) -> None:
    payload = load_manifest(MANIFEST)
    entry = payload["entries"][0]
    target = tmp_path / Path(*entry["local_relative_path"].split("/"))
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupted")
    errors = validate_manifest(payload, data_root=tmp_path, require_local=True)
    assert any("source MD5 does not match" in error for error in errors)
