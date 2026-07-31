import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import conftest
import pytest
import scripts.test_storage as test_storage

from scripts.test_storage import (
    RunState,
    TestArtifact,
    CleanupDecision,
    apply_cleanup,
    begin_run_state,
    build_cleanup_plan,
    create_run_basetemp,
    discover_artifacts,
    emergency_pressure,
    failure_deadline,
    finalize_run_state,
    is_path_referenced,
    main,
    reconcile_run_state,
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


def test_cleanup_rejects_symlinked_artifact(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    artifact = TestArtifact(link, "managed", 1, datetime.now(timezone.utc))

    removed = apply_cleanup(
        {artifact: CleanupDecision(eligible=True, reason="test")},
        apply=True,
        approved_roots=[tmp_path],
    )

    assert removed == []
    assert target.exists()


def test_cleanup_rejects_path_outside_approved_root(tmp_path: Path):
    outside = tmp_path.parent / f"outside-{tmp_path.name}"
    outside.mkdir()
    artifact = TestArtifact(outside, "managed", 1, datetime.now(timezone.utc))

    removed = apply_cleanup(
        {artifact: CleanupDecision(eligible=True, reason="test")},
        apply=True,
        approved_roots=[tmp_path],
    )

    assert removed == []
    assert outside.exists()


def test_detailed_cleanup_continues_after_one_deletion_failure(tmp_path: Path, monkeypatch):
    locked = tmp_path / "locked"
    removable = tmp_path / "removable"
    locked.mkdir()
    removable.mkdir()
    first = TestArtifact(locked, "managed", 1, datetime.now(timezone.utc))
    second = TestArtifact(removable, "managed", 1, datetime.now(timezone.utc))
    plan = {
        first: CleanupDecision(eligible=True, reason="test"),
        second: CleanupDecision(eligible=True, reason="test"),
    }
    detailed = test_storage.apply_cleanup_detailed
    original_rmtree = test_storage.shutil.rmtree

    def fake_rmtree(path):
        if Path(path) == locked:
            raise PermissionError("locked")
        original_rmtree(path)

    monkeypatch.setattr(test_storage.shutil, "rmtree", fake_rmtree)
    result = detailed(plan, apply=True, approved_roots=[tmp_path])

    assert result.removed == (removable,)
    assert len(result.failures) == 1
    assert result.failures[0].path == locked
    assert result.failures[0].error_type == "PermissionError"
    assert not removable.exists()
    assert locked.exists()


def test_cli_reports_partial_apply_and_nonzero_status(tmp_path: Path, monkeypatch, capsys):
    locked = tmp_path / "locked"
    removable = tmp_path / "removable"
    locked.mkdir()
    removable.mkdir()
    first = TestArtifact(locked, "managed", 1, datetime.now(timezone.utc))
    second = TestArtifact(removable, "managed", 1, datetime.now(timezone.utc))
    plan = {
        first: CleanupDecision(eligible=True, reason="test"),
        second: CleanupDecision(eligible=True, reason="test"),
    }
    monkeypatch.setattr(
        test_storage,
        "_build_plan",
        lambda _args: (tmp_path, plan, [tmp_path], False),
    )
    original_rmtree = test_storage.shutil.rmtree

    def fake_rmtree(path):
        if Path(path) == locked:
            raise PermissionError("locked")
        original_rmtree(path)

    monkeypatch.setattr(test_storage.shutil, "rmtree", fake_rmtree)
    exit_code = test_storage.main(
        ["clean", "--root", str(tmp_path), "--apply", "--json"]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["failures"] == [
        {
            "path": str(locked),
            "error_type": "PermissionError",
            "message": "locked",
        }
    ]
    removed = next(item for item in payload["artifacts"] if item["path"] == str(removable))
    assert removed["removed"] is True


def test_emergency_mode_shortens_only_ephemeral_failure_deadline():
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)

    assert failure_deadline("ephemeral", now, emergency=True) == now + timedelta(hours=2)


def test_emergency_mode_never_removes_review_or_evidence():
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)

    assert failure_deadline("review", now, emergency=True) == now + timedelta(days=7)
    assert failure_deadline("evidence", now, emergency=True) is None


def test_emergency_cleanup_releases_failed_ephemeral_after_two_hours(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    finished = now - timedelta(hours=3)
    artifact = TestArtifact(
        tmp_path / "run-failed",
        "managed",
        100,
        finished,
        profile="ephemeral",
        status="failed",
        finished_at=finished,
        keep_until=now + timedelta(hours=21),
    )

    plan = build_cleanup_plan(
        [artifact],
        now=now,
        older_than=timedelta(hours=24),
        emergency=True,
    )

    assert plan[artifact].eligible is True
    assert plan[artifact].emergency is True
    assert plan[artifact].reason == "eligible (emergency)"


def test_emergency_cleanup_releases_known_legacy_after_two_hours(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    artifact = TestArtifact(
        tmp_path / "PolyNexus_saxs_demo_matrix",
        "legacy",
        100,
        now - timedelta(hours=3),
    )

    plan = build_cleanup_plan(
        [artifact],
        now=now,
        older_than=timedelta(hours=24),
        emergency=True,
    )

    assert plan[artifact].eligible is True
    assert plan[artifact].emergency is True
    assert plan[artifact].reason == "eligible (emergency)"


def test_emergency_cleanup_keeps_young_legacy_protected(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    artifact = TestArtifact(
        tmp_path / "PolyNexus_saxs_demo_matrix",
        "legacy",
        100,
        now - timedelta(hours=1),
    )

    plan = build_cleanup_plan(
        [artifact],
        now=now,
        older_than=timedelta(hours=24),
        emergency=True,
    )

    assert plan[artifact].eligible is False
    assert plan[artifact].emergency is False
    assert plan[artifact].reason == "younger than retention"


def test_emergency_cleanup_preserves_review_and_evidence(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    artifacts = [
        TestArtifact(
            tmp_path / "run-review",
            "managed",
            100,
            now - timedelta(days=2),
            profile="review",
            status="failed",
            finished_at=now - timedelta(days=2),
            keep_until=now + timedelta(days=5),
        ),
        TestArtifact(
            tmp_path / "run-evidence",
            "managed",
            100,
            now - timedelta(days=2),
            profile="evidence",
            status="failed",
            finished_at=now - timedelta(days=2),
        ),
    ]

    plan = build_cleanup_plan(
        artifacts,
        now=now,
        older_than=timedelta(hours=24),
        emergency=True,
    )

    assert plan[artifacts[0]].eligible is False
    assert plan[artifacts[0]].reason == "younger than retention"
    assert plan[artifacts[1]].eligible is False
    assert plan[artifacts[1]].reason == "evidence profile"


def test_emergency_pressure_detects_low_volume(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "scripts.test_storage.shutil.disk_usage",
        lambda path: SimpleNamespace(total=100, used=92, free=8),
    )

    assert emergency_pressure(tmp_path) is True


def test_running_manifest_becomes_interrupted_only_after_process_exit(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(tmp_path / "run-1", project_root=tmp_path, profile="ephemeral", now=now)

    assert reconcile_run_state(run, process_active=True).status == "running"
    assert reconcile_run_state(run, process_active=False).status == "interrupted"


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


def test_discover_reconciles_dead_running_manifest(tmp_path: Path):
    test_root = tmp_path / "test-root"
    run_path = test_root / "pytest" / "run-dead"
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    begin_run_state(run_path, project_root=tmp_path, profile="ephemeral", now=now, pid=1234)

    artifacts = discover_artifacts(
        tmp_path,
        test_root=test_root,
        legacy_roots=[tmp_path],
        active_pids=set(),
        now=now + timedelta(hours=3),
        emergency=True,
    )

    artifact = next(item for item in artifacts if item.path == run_path)
    assert artifact.status == "interrupted"
    assert artifact.finished_at == now + timedelta(hours=3)


def test_discover_keeps_live_running_manifest(tmp_path: Path):
    test_root = tmp_path / "test-root"
    run_path = test_root / "pytest" / "run-live"
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    begin_run_state(run_path, project_root=tmp_path, profile="ephemeral", now=now, pid=1234)

    artifacts = discover_artifacts(
        tmp_path,
        test_root=test_root,
        legacy_roots=[tmp_path],
        active_pids={1234},
        now=now,
        emergency=True,
    )

    artifact = next(item for item in artifacts if item.path == run_path)
    assert artifact.status == "running"


def test_discover_known_legacy_patterns_but_rejects_archive_like_names(tmp_path: Path):
    legacy_root = tmp_path / "legacy"
    names = [
        "PolyNexus_saxs_demo_matrix",
        "PN_SAXS_MATRIX_X",
        "PolyNexus_demo_pytest",
        "PolyNexus_demo_archive",
        "PolyNexus_demo_evidence",
    ]
    for name in names:
        (legacy_root / name).mkdir(parents=True)

    artifacts = discover_artifacts(
        tmp_path,
        test_root=tmp_path / "managed",
        legacy_roots=[legacy_root],
    )

    assert [artifact.path.name for artifact in artifacts] == [
        "PN_SAXS_MATRIX_X",
        "PolyNexus_demo_pytest",
        "PolyNexus_saxs_demo_matrix",
    ]


def test_discover_historical_test_directories_but_protects_data_and_evidence(
    tmp_path: Path,
):
    legacy_root = tmp_path / "legacy"
    disposable = [
        "PolyNexus_full_boundary_current_head_20260730",
        "PolyNexus_native_ir_mapping_recheck_20260730_basetemp",
        "PolyNexus_gallery_editor_selection_verify_20260729",
        "PolyNexus_saxs_temperature_matrix",
        "SaxsAuxiliaryProvenanceRelated",
        "SaxsTemperatureAuxiliaryMatrix",
    ]
    protected = [
        "测试数据",
        "PolyNexus_saxs_review_matrix",
        "PolyNexus_saxs_evidence_matrix",
        "PolyNexus_release_baseline",
        "PolyNexus_demo_archive",
    ]
    for name in disposable + protected:
        (legacy_root / name).mkdir(parents=True)

    artifacts = discover_artifacts(
        tmp_path,
        test_root=tmp_path / "managed",
        legacy_roots=[legacy_root],
    )

    assert [artifact.path.name for artifact in artifacts] == sorted(disposable, key=str.casefold)


def test_discover_managed_artifact_reads_run_state(tmp_path: Path):
    test_root = tmp_path / "test-root"
    run_path = test_root / "pytest" / "run-1"
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(run_path, project_root=tmp_path, profile="review", now=now)
    finalize_run_state(run, exit_code=1, now=now, process_active=False)

    artifacts = discover_artifacts(tmp_path, test_root=test_root, legacy_roots=[tmp_path])

    managed = [artifact for artifact in artifacts if artifact.path == run_path]
    assert len(managed) == 1
    assert managed[0].profile == "review"
    assert managed[0].status == "failed"
    assert managed[0].keep_until == now + timedelta(days=7)


def test_cleanup_plan_protects_evidence_profile(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    artifact = TestArtifact(
        tmp_path / "run-evidence",
        "managed",
        100,
        now - timedelta(days=30),
        profile="evidence",
        status="passed",
    )

    plan = build_cleanup_plan(
        [artifact],
        now=now,
        older_than=timedelta(hours=1),
    )

    assert plan[artifact].eligible is False
    assert plan[artifact].reason == "evidence profile"


def test_cleanup_plan_does_not_cli_delete_passed_ephemeral_run(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    artifact = TestArtifact(
        tmp_path / "run-ephemeral",
        "managed",
        100,
        now - timedelta(days=30),
        profile="ephemeral",
        status="passed",
    )

    plan = build_cleanup_plan(
        [artifact],
        now=now,
        older_than=timedelta(hours=1),
    )

    assert plan[artifact].eligible is False
    assert plan[artifact].reason == "owned terminal cleanup only"


def test_cleanup_plan_protects_running_managed_manifest(tmp_path: Path):
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    artifact = TestArtifact(
        tmp_path / "run-running",
        "managed",
        100,
        now - timedelta(days=30),
        profile="ephemeral",
        status="running",
    )

    plan = build_cleanup_plan(
        [artifact],
        now=now,
        older_than=timedelta(hours=1),
        emergency=True,
    )

    assert plan[artifact].eligible is False
    assert plan[artifact].reason == "running manifest"


def test_report_json_includes_manifest_metadata(tmp_path: Path, monkeypatch, capsys):
    test_root = tmp_path / "test-root"
    run_path = test_root / "pytest" / "run-1"
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(run_path, project_root=tmp_path, profile="review", now=now)
    finalize_run_state(run, exit_code=1, now=now, process_active=False)
    monkeypatch.setenv("POLYNEXUS_LEGACY_TEST_ROOTS", str(tmp_path))

    assert main(["report", "--root", str(tmp_path), "--test-root", str(test_root), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    artifact = next(item for item in payload["artifacts"] if item["path"] == str(run_path))
    assert artifact["profile"] == "review"
    assert artifact["status"] == "failed"
    assert artifact["keep_until"] == (now + timedelta(days=7)).isoformat()


def test_report_json_marks_emergency_eligibility(tmp_path: Path, monkeypatch, capsys):
    test_root = tmp_path / "test-root"
    run_path = test_root / "pytest" / "run-1"
    now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
    run = begin_run_state(run_path, project_root=tmp_path, profile="ephemeral", now=now - timedelta(hours=3), pid=1234)
    finalize_run_state(run, exit_code=1, now=now - timedelta(hours=3), process_active=False)
    monkeypatch.setattr(test_storage, "emergency_pressure", lambda _path: False)
    monkeypatch.setattr(test_storage, "running_process_ids", lambda: set())

    assert main(["report", "--root", str(tmp_path), "--test-root", str(test_root), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    artifact = next(item for item in payload["artifacts"] if item["path"] == str(run_path))
    assert payload["emergency"] is False
    assert payload["summary"]["emergency_eligible_bytes"] == 0
    assert artifact["emergency"] is False


def test_report_json_marks_emergency_for_old_failed_run(tmp_path: Path, monkeypatch, capsys):
    test_root = tmp_path / "test-root"
    run_path = test_root / "pytest" / "run-1"
    finished = datetime(2026, 7, 29, 9, 0, tzinfo=timezone.utc)
    run = begin_run_state(run_path, project_root=tmp_path, profile="ephemeral", now=finished, pid=1234)
    finalize_run_state(run, exit_code=1, now=finished, process_active=False)
    monkeypatch.setattr(test_storage, "emergency_pressure", lambda _path: True)
    monkeypatch.setattr(test_storage, "running_process_ids", lambda: set())

    assert main(["report", "--root", str(tmp_path), "--test-root", str(test_root), "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    artifact = next(item for item in payload["artifacts"] if item["path"] == str(run_path))
    assert payload["emergency"] is True
    assert artifact["emergency"] is True
    assert artifact["reason"] == "eligible (emergency)"


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
