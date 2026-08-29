import hashlib
import json
from pathlib import Path

import pytest

from polynexus.suite.contracts import SuiteComponent
from polynexus.suite.manifest import load_lock, load_manifest, write_lock


def test_manifest_loads_pinned_component_and_lock_round_trips(tmp_path: Path):
    digest = hashlib.sha256(b"fixture").hexdigest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "components": [{"id": "ars", "version": "0.1.18", "destination": "academic-research-suite",
                         "required_files": ["SKILL.md"], "source": "file:///fixture", "sha256": digest,
                         "core_range": "1.x", "handoff_schema": "v1"}],
    }), encoding="utf-8")
    manifest = load_manifest(manifest_path)
    assert manifest.components[0] == SuiteComponent(
        component_id="ars", version="0.1.18", destination="academic-research-suite",
        required_files=("SKILL.md",), source="file:///fixture", sha256=digest,
        core_range="1.x", handoff_schema="v1"
    )
    lock_path = tmp_path / "suite-lock.json"
    write_lock(lock_path, {"core_version": "1.0.0", "components": {"ars": "0.1.18"}})
    assert load_lock(lock_path)["components"]["ars"] == "0.1.18"


def test_invalid_manifest_is_rejected(tmp_path: Path):
    path = tmp_path / "manifest.json"
    path.write_text('{"schema_version":1,"components":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="component"):
        load_manifest(path)
