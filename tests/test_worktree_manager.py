from datetime import datetime, timedelta, timezone

from scripts.worktree_manager import cleanup_decision, normalize_worktree_path


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
