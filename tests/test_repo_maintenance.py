from pathlib import Path
import sys

from scripts.repo_maintenance import (
    build_verify_command,
    finish,
    find_worktree_for_branch,
    parse_worktree_records,
    preflight_errors,
)
import scripts.repo_maintenance as maintenance


def test_build_verify_command_includes_structured_task_and_flags(tmp_path: Path):
    command = build_verify_command(
        tmp_path,
        task="docs/agent/tasks/example.md",
        full=True,
        boundary=True,
    )

    assert command == [
        sys.executable,
        str(tmp_path / "scripts" / "verify.py"),
        "--task",
        "docs/agent/tasks/example.md",
        "--changed",
        "--types",
        "--full",
        "--boundary",
    ]


def test_parse_and_find_worktree_records_by_branch():
    porcelain = """\
worktree D:/PolyNexus
HEAD abc123
branch refs/heads/codex/feature

worktree C:/worktrees/PolyNexus-main
HEAD def456
branch refs/heads/main
"""

    records = parse_worktree_records(porcelain)

    assert find_worktree_for_branch(records, "main") == {
        "path": Path("C:/worktrees/PolyNexus-main"),
        "head": "def456",
        "branch": "main",
    }


def test_preflight_rejects_staged_changes_missing_target_dirty_target_and_same_path(
    tmp_path: Path,
):
    errors = preflight_errors(
        staged_paths=["scripts/example.py"],
        target=None,
        source_path=tmp_path,
        target_path=tmp_path,
        target_dirty=True,
    )

    assert errors == [
        "source worktree has staged changes",
        "target branch worktree was not found",
        "source and target worktrees must be different",
        "target worktree has uncommitted changes",
    ]


def test_preflight_accepts_distinct_clean_target():
    root = Path("D:/PolyNexus")
    target = {"path": Path("C:/worktrees/PolyNexus-main"), "head": "def456", "branch": "main"}

    assert preflight_errors(
        staged_paths=[],
        target=target,
        source_path=root,
        target_path=target["path"],
        target_dirty=False,
    ) == []


def test_finish_runs_verify_commit_and_fast_forward_merge_in_order(
    tmp_path: Path, monkeypatch
):
    target_path = tmp_path / "main"
    calls: list[tuple[Path, list[str]]] = []
    record = {"path": target_path, "head": "def456", "branch": "main"}

    monkeypatch.setattr(maintenance, "_source_branch", lambda root: "codex/task")
    monkeypatch.setattr(maintenance, "_worktree_records", lambda root: [record])
    monkeypatch.setattr(maintenance, "_staged_paths", lambda root: [])
    monkeypatch.setattr(maintenance, "_is_dirty", lambda path: False)
    monkeypatch.setattr(
        maintenance,
        "_run",
        lambda cwd, command: calls.append((cwd, command)) or 0,
    )

    assert finish(
        tmp_path,
        target_branch="main",
        files=["scripts/example.py"],
        message="feat: example",
    ) == 0

    assert Path(calls[0][1][1]).parts[-2:] == ("scripts", "verify.py")
    assert Path(calls[1][1][1]).parts[-2:] == ("scripts", "auto_commit.py")
    assert calls[2] == (target_path, ["git", "merge", "--ff-only", "codex/task"])


def test_finish_does_not_run_commands_when_target_is_dirty(tmp_path: Path, monkeypatch):
    target_path = tmp_path / "main"
    calls: list[list[str]] = []
    record = {"path": target_path, "head": "def456", "branch": "main"}

    monkeypatch.setattr(maintenance, "_source_branch", lambda root: "codex/task")
    monkeypatch.setattr(maintenance, "_worktree_records", lambda root: [record])
    monkeypatch.setattr(maintenance, "_staged_paths", lambda root: [])
    monkeypatch.setattr(maintenance, "_is_dirty", lambda path: True)
    monkeypatch.setattr(
        maintenance,
        "_run",
        lambda cwd, command: calls.append(command) or 0,
    )

    assert finish(
        tmp_path,
        target_branch="main",
        files=["scripts/example.py"],
        message="feat: example",
    ) == 1
    assert calls == []
