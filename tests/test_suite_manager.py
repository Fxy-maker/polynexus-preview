import hashlib
import json
from pathlib import Path

from polynexus.suite.manager import SuiteManager


def _dir_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted((item for item in path.rglob("*") if item.is_file()), key=lambda item: item.relative_to(path).as_posix()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(child.read_bytes())
    return digest.hexdigest()


def _manifest(path: Path, source: Path) -> Path:
    payload = {"schema_version": 1, "components": [{
        "id": "ars", "version": "0.1.18", "destination": "academic-research-suite",
        "required_files": ["SKILL.md"], "source": str(source), "sha256": _dir_hash(source),
        "core_range": "1.x", "handoff_schema": "v1",
    }]}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_install_validates_and_doctor_reports_installed(tmp_path: Path):
    source = tmp_path / "ars"
    source.mkdir()
    (source / "SKILL.md").write_text("name: fixture", encoding="utf-8")
    manifest = _manifest(tmp_path / "manifest.json", source)
    codex = tmp_path / "codex" / "skills"
    manager = SuiteManager(manifest_path=manifest, codex_skills_dir=codex, core_version="1.0.0", lock_path=tmp_path / "lock.json")
    result = manager.install("ars", confirm=True)
    assert result.status == "installed"
    assert (codex / "academic-research-suite" / "SKILL.md").is_file()
    assert manager.doctor().components[0].status == "installed"


def test_install_requires_confirmation(tmp_path: Path):
    source = tmp_path / "ars"
    source.mkdir()
    (source / "SKILL.md").write_text("name: fixture", encoding="utf-8")
    manager = SuiteManager(manifest_path=_manifest(tmp_path / "manifest.json", source), codex_skills_dir=tmp_path / "skills", lock_path=tmp_path / "lock.json")
    assert manager.install("ars").status == "confirmation_required"


def test_doctor_reports_codex_home_detection(tmp_path: Path):
    source = tmp_path / "ars"
    source.mkdir()
    (source / "SKILL.md").write_text("fixture", encoding="utf-8")
    manager = SuiteManager(
        manifest_path=_manifest(tmp_path / "manifest.json", source),
        codex_skills_dir=tmp_path / "codex" / "skills",
        lock_path=tmp_path / "lock.json",
    )
    status = manager.doctor().to_dict()
    assert status["codex_home"] == str((tmp_path / "codex").resolve())
    assert status["codex_detected"] is False


def test_failed_activation_restores_previous_installation(tmp_path: Path, monkeypatch):
    source = tmp_path / "ars"
    source.mkdir()
    (source / "SKILL.md").write_text("new", encoding="utf-8")
    manifest = _manifest(tmp_path / "manifest.json", source)
    codex = tmp_path / "codex" / "skills"
    target = codex / "academic-research-suite"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("old", encoding="utf-8")
    manager = SuiteManager(manifest_path=manifest, codex_skills_dir=codex, core_version="1.0.0", lock_path=tmp_path / "lock.json")
    monkeypatch.setattr(manager, "_activate_staged", lambda *_: (_ for _ in ()).throw(OSError("boom")))
    result = manager.install("ars", confirm=True)
    assert result.status == "activation_rolled_back"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "old"


def test_successful_install_cleans_same_volume_staging_directories(tmp_path: Path):
    source = tmp_path / "ars"
    source.mkdir()
    (source / "SKILL.md").write_text("new", encoding="utf-8")
    manifest = _manifest(tmp_path / "manifest.json", source)
    codex = tmp_path / "codex" / "skills"
    manager = SuiteManager(manifest_path=manifest, codex_skills_dir=codex, core_version="1.0.0", lock_path=tmp_path / "lock.json")
    assert manager.install("ars", confirm=True).status == "installed"
    assert not list(codex.parent.glob(".polynexus-suite-*"))
