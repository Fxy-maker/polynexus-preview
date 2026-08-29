from polynexus.gui.suite_manager_adapter import SuiteManagerAdapter


def test_gui_adapter_returns_json_safe_projection(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"schema_version":1,"components":[{"id":"ars","version":"1","destination":"ars","required_files":["SKILL.md"],"source":"fixture","sha256":"' + '0' * 64 + '"}]}', encoding="utf-8")
    adapter = SuiteManagerAdapter(manifest_path=manifest, codex_skills_dir=tmp_path / "skills", lock_path=tmp_path / "lock.json")
    result = adapter.doctor()
    assert result["status"] in {"component_missing", "codex_not_found"}
    assert isinstance(result["components"], list)
