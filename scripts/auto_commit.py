"""Safely create one commit from an explicit file allowlist."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def normalize_requested_files(root: Path, files: Iterable[str]) -> list[str]:
    """Return unique repository-relative files, rejecting paths outside root."""

    root = root.resolve()
    normalized: set[str] = set()
    for raw in files:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if path == root or root not in path.parents:
            raise ValueError(f"path is outside repository: {raw}")
        if not path.is_file():
            raise ValueError(f"file does not exist: {raw}")
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            raise ValueError(f"cannot commit Git metadata: {raw}")
        normalized.add(relative)
    if not normalized:
        raise ValueError("at least one changed file is required")
    return sorted(normalized)


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, text=True, capture_output=True
    )
    if check and completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed


def _staged_paths(root: Path) -> list[str]:
    completed = _git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return sorted(path.replace("\\", "/") for path in completed.stdout.splitlines() if path.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True, help="Commit message.")
    parser.add_argument("--files", nargs="+", required=True, help="Exact files to commit.")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    try:
        requested = normalize_requested_files(root, args.files)
        existing_staged = _staged_paths(root)
        if existing_staged:
            raise RuntimeError(
                "staged files already exist; automatic commit refuses to mix tasks: "
                + ", ".join(existing_staged)
            )

        _git(root, "add", "--", *requested)
        staged = _staged_paths(root)
        if staged != requested:
            _git(root, "reset", "--", *staged, check=False)
            raise RuntimeError(
                "staged file set differs from requested file set: "
                f"requested={requested}, staged={staged}"
            )

        diff_check = _git(root, "diff", "--cached", "--check")
        if diff_check.returncode != 0:
            _git(root, "reset", "--", *staged, check=False)
            raise RuntimeError(diff_check.stderr.strip() or "staged diff check failed")

        commit = _git(root, "commit", "-m", args.message)
        print(commit.stdout.strip())
        print("[auto-commit] committed requested files only; no push was performed")
        return 0
    except (RuntimeError, ValueError) as error:
        print(f"[auto-commit] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
