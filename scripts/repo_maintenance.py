"""Run the safe local repository finish sequence for an atomic task."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable, TypedDict

from scripts.worktree_manager import REGISTRY_PATH


class WorktreeRecord(TypedDict):
    path: Path
    head: str
    branch: str


def build_verify_command(
    root: Path,
    *,
    task: str | None = None,
    full: bool = False,
    boundary: bool = False,
) -> list[str]:
    """Build the repository verifier command without invoking a shell."""

    command = [sys.executable, str(root / "scripts" / "verify.py")]
    if task:
        command += ["--task", task]
    command += ["--changed", "--types"]
    if full:
        command.append("--full")
    if boundary:
        command.append("--boundary")
    return command


def parse_worktree_records(porcelain: str) -> list[WorktreeRecord]:
    """Parse the stable fields emitted by ``git worktree list --porcelain``."""

    records: list[WorktreeRecord] = []
    current: dict[str, str] = {}
    for line in porcelain.splitlines() + [""]:
        if not line.strip():
            if current.get("worktree"):
                records.append(
                    {
                        "path": Path(current["worktree"]).resolve(),
                        "head": current.get("HEAD", ""),
                        "branch": current.get("branch", "").removeprefix("refs/heads/"),
                    }
                )
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return records


def find_worktree_for_branch(
    records: Iterable[WorktreeRecord], branch: str
) -> WorktreeRecord | None:
    """Return the worktree checked out on ``branch``."""

    return next((record for record in records if record["branch"] == branch), None)


def preflight_errors(
    *,
    staged_paths: Iterable[str],
    target: WorktreeRecord | None,
    source_path: Path,
    target_path: Path | None,
    target_dirty: bool,
) -> list[str]:
    """Return safety failures that must stop before verification or merging."""

    errors: list[str] = []
    if list(staged_paths):
        errors.append("source worktree has staged changes")
    if target is None:
        errors.append("target branch worktree was not found")
    if target_path is not None and source_path.resolve() == target_path.resolve():
        errors.append("source and target worktrees must be different")
    if target_dirty:
        errors.append("target worktree has uncommitted changes")
    return errors


def _run(root: Path, command: list[str]) -> int:
    print(f"[maintenance] {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=root, check=False).returncode


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )


def _git_output(root: Path, *args: str) -> str:
    result = _git(root, *args)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _staged_paths(root: Path) -> list[str]:
    return [
        line
        for line in _git_output(root, "diff", "--cached", "--name-only").splitlines()
        if line.strip()
    ]


def _worktree_records(root: Path) -> list[WorktreeRecord]:
    return parse_worktree_records(_git_output(root, "worktree", "list", "--porcelain"))


def _is_dirty(path: Path) -> bool:
    result = _git(path, "status", "--porcelain", "--untracked-files=all")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"cannot inspect worktree: {path}")
    return bool(result.stdout.strip())


def _source_branch(root: Path) -> str:
    branch = _git_output(root, "symbolic-ref", "--short", "HEAD")
    if not branch:
        raise RuntimeError("source worktree is detached")
    return branch


def _agent_owned(root: Path) -> bool:
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    metadata = registry.get(str(root.resolve()), {})
    return isinstance(metadata, dict) and metadata.get("owner") == "agent"


def finish(
    root: Path,
    *,
    target_branch: str,
    files: list[str],
    message: str,
    task: str | None = None,
    full: bool = False,
    boundary: bool = False,
    cleanup: bool = False,
    cooldown_hours: float = 1.0,
) -> int:
    """Verify, checkpoint, locally merge, and optionally clean worktrees."""

    root = root.resolve()
    source_branch = _source_branch(root)
    target = find_worktree_for_branch(_worktree_records(root), target_branch)
    target_path = target["path"] if target else None
    errors = preflight_errors(
        staged_paths=_staged_paths(root),
        target=target,
        source_path=root,
        target_path=target_path,
        target_dirty=_is_dirty(target_path) if target_path else False,
    )
    if source_branch == target_branch:
        errors.append("source and target branches must be different")
    if errors:
        for error in errors:
            print(f"[maintenance] {error}", file=sys.stderr)
        return 1

    verify = build_verify_command(root, task=task, full=full, boundary=boundary)
    if _run(root, verify) != 0:
        return 1

    commit = [
        sys.executable,
        str(root / "scripts" / "auto_commit.py"),
        "--message",
        message,
        "--files",
        *files,
    ]
    if _run(root, commit) != 0:
        return 1

    if target_path is None:
        raise RuntimeError("target worktree disappeared after preflight")
    merge = ["git", "merge", "--ff-only", source_branch]
    if _run(target_path, merge) != 0:
        return 1

    if cleanup:
        manager = str(root / "scripts" / "worktree_manager.py")
        if _agent_owned(root) and root != target_path:
            finish_worktree = [
                sys.executable,
                manager,
                "--root",
                str(root),
                "finish",
                str(root),
                "--reason",
                f"merged {source_branch} into {target_branch}",
            ]
            if _run(root, finish_worktree) != 0:
                return 1
        clean = [
            sys.executable,
            manager,
            "--root",
            str(root),
            "clean",
            "--apply",
            "--cooldown-hours",
            str(cooldown_hours),
        ]
        if _run(root, clean) != 0:
            return 1

    print(f"[maintenance] merged {source_branch} into {target_branch}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    finish_parser = subparsers.add_parser("finish", help=finish.__doc__)
    finish_parser.add_argument("--root", default=".")
    finish_parser.add_argument("--target", default="main", dest="target_branch")
    finish_parser.add_argument("--files", nargs="+", required=True)
    finish_parser.add_argument("--message", required=True)
    finish_parser.add_argument("--task")
    finish_parser.add_argument("--full", action="store_true")
    finish_parser.add_argument("--boundary", action="store_true")
    finish_parser.add_argument("--cleanup", action="store_true")
    finish_parser.add_argument("--cooldown-hours", type=float, default=1.0)
    args = parser.parse_args(argv)

    if args.command != "finish":
        parser.error(f"unsupported command: {args.command}")
    try:
        return finish(
            Path(args.root),
            target_branch=args.target_branch,
            files=args.files,
            message=args.message,
            task=args.task,
            full=args.full,
            boundary=args.boundary,
            cleanup=args.cleanup,
            cooldown_hours=args.cooldown_hours,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[maintenance] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
