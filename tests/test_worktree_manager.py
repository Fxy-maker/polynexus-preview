from datetime import datetime, timedelta, timezone

from scripts.worktree_manager import (
    adoption_metadata,
    cleanup_decision,
    legacy_candidates,
    normalize_worktree_path,
)
import scripts.worktree_manager as manager


def test_cleanup_requires_agent_ownership_finished_commit_and_cooldown(tmp_path):
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    metadata = {
        "owner": "agent",
        "status": "pending_cleanup",
        "branch": "codex/example",
        "finished_commit": "abc123",
        "finished_at": (now - timedelta(hours=2)).isoformat(),
    }

    allowed, reasons = cleanup_decision(
        metadata,
        observed_branch="codex/example",
        observed_head="abc123",
        dirty=False,
        now=now,
        cooldown=timedelta(hours=1),
    )

    assert allowed is True
    assert reasons == []


def test_cleanup_rejects_dirty_mismatched_or_cooling_worktrees():
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
    base = {
        "owner": "agent",
        "status": "pending_cleanup",
        "branch": "codex/example",
        "finished_commit": "abc123",
        "finished_at": (now - timedelta(minutes=10)).isoformat(),
    }

    allowed, reasons = cleanup_decision(
        base,
        observed_branch="codex/other",
        observed_head="def456",
        dirty=True,
        now=now,
        cooldown=timedelta(hours=1),
    )

    assert allowed is False
    assert {"worktree is dirty", "branch differs from metadata",
            "HEAD differs from finished commit", "cooldown not elapsed"} <= set(reasons)


def test_cleanup_rejects_unknown_ownership():
    allowed, reasons = cleanup_decision(
        {"status": "pending_cleanup"},
        observed_branch="codex/example",
        observed_head="abc123",
        dirty=False,
        now=datetime.now(timezone.utc),
        cooldown=timedelta(hours=1),
    )

    assert allowed is False
    assert "worktree is not agent-owned" in reasons


def test_normalize_worktree_path_is_absolute_and_stable(tmp_path):
    assert normalize_worktree_path(tmp_path, "child") == str((tmp_path / "child").resolve())
    assert normalize_worktree_path(tmp_path, str(tmp_path / "child")) == str(
        (tmp_path / "child").resolve()
    )


def test_legacy_candidates_only_include_unregistered_codex_worktrees_under_managed_root(
    tmp_path,
):
    current_root = tmp_path / "current"
    managed_root = tmp_path / "managed"
    records = [
        {"worktree": str(managed_root / "old"), "HEAD": "oldhead", "branch": "refs/heads/codex/old"},
        {"worktree": str(current_root), "HEAD": "current", "branch": "refs/heads/codex/current"},
        {"worktree": str(managed_root / "main"), "HEAD": "main", "branch": "refs/heads/main"},
        {"worktree": str(tmp_path / "outside"), "HEAD": "outside", "branch": "refs/heads/codex/outside"},
        {"worktree": str(managed_root / "registered"), "HEAD": "registered", "branch": "refs/heads/codex/registered"},
    ]
    registry = {str((managed_root / "registered").resolve()): {"owner": "agent"}}

    candidates = legacy_candidates(records, registry, current_root, managed_root)

    assert candidates == [records[0]]


def test_adoption_metadata_marks_clean_and_dirty_records_differently():
    record = {
        "worktree": "C:/worktrees/legacy",
        "HEAD": "abc123",
        "branch": "refs/heads/codex/legacy",
    }
    now = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)

    clean = adoption_metadata(record, task="legacy/codex-legacy", dirty=False, now=now)
    dirty = adoption_metadata(record, task="legacy/codex-legacy", dirty=True, now=now)

    assert clean["owner"] == "agent"
    assert clean["status"] == "pending_cleanup"
    assert clean["finished_commit"] == "abc123"
    assert clean["finished_at"] == now.isoformat()
    assert dirty["status"] == "legacy_dirty"
    assert dirty["dirty"] is True


def test_adopt_legacy_report_is_read_only(tmp_path, monkeypatch, capsys):
    managed_root = tmp_path / "managed"
    current_root = tmp_path / "current"
    record = {
        "worktree": str(managed_root / "old"),
        "HEAD": "abc123",
        "branch": "refs/heads/codex/old",
    }
    saved = []
    monkeypatch.setattr(manager, "REGISTRY_ROOT", managed_root)
    monkeypatch.setattr(manager, "_git_worktree_records", lambda root: [record])
    monkeypatch.setattr(manager, "_registry", lambda: {})
    monkeypatch.setattr(manager, "_save_registry", lambda value: saved.append(value))
    monkeypatch.setattr(manager, "_status", lambda path: False)

    assert manager._adopt_legacy(current_root, False, False, "legacy-") == 0
    assert saved == []
    assert "would-apply" in capsys.readouterr().out


def test_adopt_legacy_apply_archives_dirty_and_registers_clean(tmp_path, monkeypatch):
    managed_root = tmp_path / "managed"
    current_root = tmp_path / "current"
    clean_record = {
        "worktree": str(managed_root / "clean"),
        "HEAD": "cleanhead",
        "branch": "refs/heads/codex/clean",
    }
    dirty_record = {
        "worktree": str(managed_root / "dirty"),
        "HEAD": "dirtyhead",
        "branch": "refs/heads/codex/dirty",
    }
    (managed_root / "clean").mkdir(parents=True)
    (managed_root / "dirty").mkdir(parents=True)
    registry = {}
    saved = []
    archived = []
    monkeypatch.setattr(manager, "REGISTRY_ROOT", managed_root)
    monkeypatch.setattr(
        manager,
        "_git_worktree_records",
        lambda root: [clean_record, dirty_record],
    )
    monkeypatch.setattr(manager, "_registry", lambda: registry)
    monkeypatch.setattr(manager, "_save_registry", lambda value: saved.append(dict(value)))
    monkeypatch.setattr(manager, "_status", lambda path: path.name == "dirty")
    monkeypatch.setattr(
        manager,
        "_archive",
        lambda root, target, reason: archived.append((target, reason)) or 0,
    )

    assert manager._adopt_legacy(current_root, True, True, "legacy-") == 0
    assert registry[str((managed_root / "clean").resolve())]["status"] == "pending_cleanup"
    assert registry[str((managed_root / "dirty").resolve())]["status"] == "legacy_dirty"
    assert len(saved) == 2
    assert archived == [
        (str((managed_root / "dirty").resolve()), "legacy worktree adopted while dirty")
    ]
