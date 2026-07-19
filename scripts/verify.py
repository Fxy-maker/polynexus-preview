"""Unified verification entry point for PolyNexus agent work."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


PROJECT_PYTHON_PREFIXES = ("polynexus/", "scripts/", "tests/", "rag/")
TYPE_CHECK_BASELINE = (
    "scripts/agent_memory.py",
    "scripts/task_check.py",
    "scripts/verify.py",
)


def command_for(*args: str) -> list[str]:
    """Build a subprocess command for Python modules/scripts or executables."""

    if not args:
        raise ValueError("at least one command argument is required")
    first = args[0].lower()
    if first == "-m" or first.endswith(".py"):
        return [sys.executable, *args]
    return list(args)


def _run(root: Path, *args: str) -> int:
    command = command_for(*args)
    print(f"[verify] {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=root, check=False)
    return int(completed.returncode)


def changed_python_paths(paths: Iterable[str]) -> list[str]:
    """Return sorted, repository-relative Python paths in project source areas."""

    selected = {
        path.replace("\\", "/")
        for path in paths
        if path.replace("\\", "/").endswith(".py")
        and path.replace("\\", "/").startswith(PROJECT_PYTHON_PREFIXES)
    }
    return sorted(selected)


def type_check_targets(paths: Iterable[str], include_all: bool = False) -> list[str]:
    """Return the current phased Pyright target set."""

    if include_all:
        return list(TYPE_CHECK_BASELINE)
    changed = set(changed_python_paths(paths))
    return [path for path in TYPE_CHECK_BASELINE if path in changed]


def _git_paths(root: Path, *args: str) -> list[str]:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        print(completed.stderr.strip(), file=sys.stderr)
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _changed_paths(root: Path, base: str | None) -> list[str]:
    paths = _git_paths(root, "diff", "--name-only", "--diff-filter=ACMR", "HEAD")
    paths += _git_paths(root, "ls-files", "--others", "--exclude-standard")
    if base:
        paths += _git_paths(root, "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
    return sorted(set(path.replace("\\", "/") for path in paths))


def _run_changed_checks(root: Path, base: str | None) -> int:
    python_paths = changed_python_paths(_changed_paths(root, base))
    if not python_paths:
        print("[verify] no changed project Python files to lint", flush=True)
        return 0

    ruff = shutil.which("ruff")
    if not ruff:
        print("[verify] ruff is required for --changed checks", file=sys.stderr)
        return 2

    result = _run(root, ruff, "check", *python_paths)
    if result != 0:
        return result
    return _run(root, "-m", "py_compile", *python_paths)


def _run_type_checks(root: Path, changed_paths: Iterable[str] | None = None) -> int:
    targets = type_check_targets(changed_paths or (), include_all=changed_paths is None)
    if not targets:
        print("[verify] no changed files in the current type-check baseline", flush=True)
        return 0

    pyright = shutil.which("pyright")
    if not pyright:
        print("[verify] pyright is required for --types checks", file=sys.stderr)
        return 2
    return _run(root, pyright, "-p", "pyrightconfig.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the standard PolyNexus verification workflow."
    )
    parser.add_argument("--full", action="store_true", help="Run the focused gate plus the full pytest suite.")
    parser.add_argument("--boundary", action="store_true", help="Run the read-only structural boundary audit after the quality gate.")
    parser.add_argument("--changed", action="store_true", help="Lint and compile changed project Python files before the quality gate.")
    parser.add_argument("--base", help="Base Git ref to include in --changed checks, such as origin/main.")
    parser.add_argument("--task", help="Validate a task-card Markdown file before running verification.")
    parser.add_argument("--types", action="store_true", help="Run the phased Pyright type-check baseline.")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    if args.task:
        task_check = root / "scripts" / "task_check.py"
        result = _run(root, str(task_check), "--task", args.task)
        if result != 0:
            return result

    memory_check = root / "scripts" / "agent_memory.py"
    result = _run(root, str(memory_check), "check", "--root", str(root))
    if result != 0:
        return result

    if args.changed:
        changed_paths = _changed_paths(root, args.base)
        result = _run_changed_checks(root, args.base)
        if result != 0:
            return result
        if args.types:
            result = _run_type_checks(root, changed_paths)
            if result != 0:
                return result
    elif args.types:
        result = _run_type_checks(root)
        if result != 0:
            return result

    quality_gate = root / "scripts" / "quality_gate.py"
    command = [str(quality_gate), "--root", str(root)]
    if args.full:
        command.append("--all-tests")

    result = _run(root, *command)
    if result != 0:
        return result

    if args.boundary:
        boundary_audit = root / "scripts" / "boundary_audit.py"
        result = _run(root, str(boundary_audit), "--root", str(root), "--json")
        if result != 0:
            return result

    print("[verify] selected checks passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
