import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import conftest

from scripts.test_storage import (
    TestArtifact,
    build_cleanup_plan,
    create_run_basetemp,
    discover_artifacts,
    is_path_referenced,
    resolve_legacy_test_roots,
    resolve_test_root,
)


def test_resolve_test_root_prefers_environment_override(tmp_path: Path):
    override = tmp_path / "external-tests"

    assert resolve_test_root(tmp_path, {"POLYNEXUS_TEST_ROOT": str(override)}) == override.resolve()


def test_resolve_test_root_defaults_to_project_drive(tmp_path: Path):
    expected = Path(tmp_path.anchor) / "PolyNexus-test-runs"

    assert resolve_test_root(tmp_path, {}) == expected.resolve()


def test_resolve_legacy_test_roots_accepts_path_list_override(tmp_path: Path):
    first = tmp_path / "legacy-one"
    second = tmp_path / "legacy-two"
    value = f"{first}{os.pathsep}{second}"

    roots = resolve_legacy_test_roots(tmp_path, {"POLYNEXUS_LEGACY_TEST_ROOTS": value})

    assert roots == [tmp_path.resolve(), first.resolve(), second.resolve()]


def test_discover_artifacts_includes_external_legacy_test_root(tmp_path: Path):
    legacy_root = tmp_path / "external"
    artifact = legacy_root / "TempPolyNexus_old-run"
    artifact.mkdir(parents=True)
    (artifact / "result.bin").write_bytes(b"test")

    artifacts = discover_artifacts(
        tmp_path,
        test_root=tmp_path / "managed",
        legacy_roots=[legacy_root],
    )

    assert [item.path for item in artifacts] == [artifact.resolve()]
    assert artifacts[0].kind == "legacy-external"


def test_create_run_basetemp_is_unique_and_external(tmp_path: Path):
    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)

    first = create_run_basetemp(tmp_path, now=now, pid=123)
    second = create_run_basetemp(tmp_path, now=now, pid=123)

    assert first != second
    assert first.parent == resolve_test_root(tmp_path) / "pytest"
    assert first.is_dir()
    assert second.is_dir()


def test_pytest_hook_keeps_explicit_basetemp(tmp_path: Path):
    config = SimpleNamespace(option=SimpleNamespace(basetemp=str(tmp_path / "explicit")))

    conftest.pytest_configure(config)

    assert config.option.basetemp == str(tmp_path / "explicit")


def test_pytest_hook_assigns_external_basetemp_when_missing(tmp_path: Path, monkeypatch):
    config = SimpleNamespace(option=SimpleNamespace(basetemp=None))
    monkeypatch.setattr(conftest, "Path", lambda value: tmp_path)

    conftest.pytest_configure(config)

    assert Path(config.option.basetemp).parent.name == "pytest"
    assert Path(config.option.basetemp).is_dir()


def test_is_path_referenced_normalizes_windows_slashes():
    path = Path("D:/PolyNexus-test-runs/pytest/run-123")

    assert is_path_referenced(path, ['python -m pytest --basetemp="D:\\PolyNexus-test-runs\\pytest\\run-123"'])
    assert not is_path_referenced(path, ["python -m pytest tests/test_core.py"])


def test_cleanup_plan_skips_young_active_tracked_and_protected_artifacts(tmp_path: Path):
    now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    old = TestArtifact(tmp_path / "old", "legacy", 100, now - timedelta(hours=48))
    young = TestArtifact(tmp_path / "young", "legacy", 100, now - timedelta(hours=1))
    active = TestArtifact(tmp_path / "active", "managed", 100, now - timedelta(hours=48))
    tracked = TestArtifact(tmp_path / "tracked", "legacy", 100, now - timedelta(hours=48))
    protected = TestArtifact(tmp_path / "protected", "legacy", 100, now - timedelta(hours=48))

    plan = build_cleanup_plan(
        [old, young, active, tracked, protected],
        now=now,
        older_than=timedelta(hours=24),
        active_command_lines=[f"pytest --basetemp={active.path}"],
        tracked_paths=[tracked.path],
        protected_paths=[protected.path],
    )

    assert plan[old].eligible is True
    assert plan[young].reason == "younger than retention"
    assert plan[active].reason == "referenced by a running process"
    assert plan[tracked].reason == "tracked by Git"
    assert plan[protected].reason == "protected path"


def test_cleanup_plan_protects_external_legacy_artifacts_while_pytest_runs(tmp_path: Path):
    artifact = TestArtifact(
        tmp_path / "TempPolyNexus_old-run",
        "legacy-external",
        100,
        datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc) - timedelta(hours=48),
    )

    plan = build_cleanup_plan(
        [artifact],
        now=datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc),
        older_than=timedelta(hours=24),
        active_command_lines=["python -m pytest tests/test_test_storage.py"],
    )

    assert plan[artifact].reason == "referenced by a running process"
