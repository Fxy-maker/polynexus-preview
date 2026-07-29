import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import conftest

from scripts.test_storage import (
    RunState,
    TestArtifact,
    begin_run_state,
    build_cleanup_plan,
    create_run_basetemp,
    discover_artifacts,
    finalize_run_state,
    is_path_referenced,
    read_run_state,
    resolve_legacy_test_roots,
    resolve_retention_profile,
    resolve_test_root,
    write_run_state,
)


def test_resolve_test_root_prefers_environment_override(tmp_path: Path):
    override = tmp_path / "external-tests"

    assert resolve_test_root(tmp_path, {"POLYNEXUS_TEST_ROOT": str(override)}) == override.resolve()


def test_resolve_test_root_defaults_to_project_drive(tmp_path: Path):
    expected = Path(tmp_path.anchor) / "PolyNexus-test-runs"

    assert resolve_test_root(tmp_path, {}) == expected.resolve()


def test_resolve_retention_profile_defaults_to_ephemeral():
    assert resolve_retention_profile({}) == "ephemeral"


def test_resolve_retention_profile_accepts_review_and_evidence():
    assert resolve_retention_profile({"POLYNEXUS_TEST_RETENTION": "review"}) == "review"
    assert resolve_retention_profile({"POLYNEXUS_TEST_RETENTION": "evidence"}) == "evidence"


def test_resolve_retention_profile_fails_closed_to_review():
    assert resolve_retention_profile({"POLYNEXUS_TEST_RETENTION": "unknown"}) == "review"


def test_run_state_round_trip(tmp_path: Path):
    run_path = tmp_path / "run-1"
    run_path.mkdir()
    created_at = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    state = RunState(
        schema_version=1,
        run_id="run-1",
        path=run_path,
        project_root=tmp_path,
        git_head="abc123",
        pid=123,
        process_started_at=created_at,
        profile="ephemeral",
        status="running",
        exit_code=None,
        created_at=created_at,
        finished_at=None,
        keep_until=None,
    )

    write_run_state(state)

    assert read_run_state(run_path) == state


def test_finalize_run_removes_owned_ephemeral_success(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(tmp_path / "run-1", project_root=tmp_path, profile="ephemeral", now=now)

    finalize_run_state(run, exit_code=0, now=now, process_active=False)

    assert not run.path.exists()


def test_finalize_run_keeps_ephemeral_failure_with_deadline(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(tmp_path / "run-1", project_root=tmp_path, profile="ephemeral", now=now)

    finalize_run_state(run, exit_code=1, now=now, process_active=False)

    state = read_run_state(run.path)
    assert state is not None
    assert state.status == "failed"
    assert state.keep_until == now + timedelta(hours=24)


def test_finalize_run_never_removes_evidence(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(tmp_path / "run-1", project_root=tmp_path, profile="evidence", now=now)

    finalize_run_state(run, exit_code=0, now=now, process_active=False)

    assert run.path.exists()
    state = read_run_state(run.path)
    assert state is not None
    assert state.status == "passed"


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
