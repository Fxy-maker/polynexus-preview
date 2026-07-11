"""Read-only maintenance audit helpers for local PolyNexus worktrees."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.maintenance_common import split_display_items


@dataclass(frozen=True)
class ScratchRule:
    pattern: str
    description: str


SCRATCH_RULES: tuple[ScratchRule, ...] = (
    ScratchRule(".pytest_tmp*", "pytest temp directory"),
    ScratchRule(".tmp_pytest*", "pytest temp directory"),
    ScratchRule("test_output", "generated test output"),
    ScratchRule("results", "generated analysis output"),
    ScratchRule("polynexus.log", "runtime log"),
    ScratchRule("_*.py", "root-level diagnostic script"),
)

PROTECTED_PATHS: tuple[str, ...] = (
    "tests/eval/cases/",
    "tests/eval/synth_data/",
    "测试数据/",
    "docs/baselines/",
)

VERIFY_COMMANDS: tuple[str, ...] = (
    "python scripts/quality_gate.py --root .",
    "python scripts/quality_gate.py --root . --all-tests",
)


def find_scratch_paths(
    root: Path, rules: Iterable[ScratchRule] = SCRATCH_RULES
) -> list[tuple[Path, ScratchRule]]:
    found: list[tuple[Path, ScratchRule]] = []
    for rule in rules:
        for path in root.glob(rule.pattern):
            found.append((path, rule))
    return sorted(found, key=lambda item: item[0].name.lower())


def parse_git_ls_files(output: str) -> list[Path]:
    return [Path(line.strip()) for line in output.splitlines() if line.strip()]


def list_tracked_scratch(root: Path, rules: Iterable[ScratchRule] = SCRATCH_RULES) -> list[Path]:
    patterns = [rule.pattern for rule in rules]
    try:
        completed = subprocess.run(
            ["git", "ls-files", *patterns],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []
    if completed.returncode not in (0, 1):
        return []
    return parse_git_ls_files(completed.stdout)


def format_report(
    root: Path,
    rules: Iterable[ScratchRule] = SCRATCH_RULES,
    max_items: int = 40,
    list_all: bool = False,
) -> str:
    scratch_paths = find_scratch_paths(root, rules)
    tracked = list_tracked_scratch(root, rules)
    displayed_paths, remaining = split_display_items(scratch_paths, max_items=max_items, list_all=list_all)
    lines = [
        "PolyNexus maintenance audit",
        f"Root: {root}",
        "",
        f"Scratch artifacts: {len(scratch_paths)} found",
    ]
    if scratch_paths:
        for path, rule in displayed_paths:
            kind = "dir" if path.is_dir() else "file"
            lines.append(f"- {path.name} [{kind}] - {rule.description}")
        if remaining > 0:
            lines.append(f"- ... {remaining} more. Re-run with --all to list every artifact.")
    else:
        lines.append("- none found")

    lines.extend(["", "Tracked scratch artifacts:"])
    if tracked:
        for path in tracked:
            lines.append(f"- {path.as_posix()}")
    else:
        lines.append("- none found")

    lines.extend(["", "Protected paths:"])
    for path in PROTECTED_PATHS:
        lines.append(f"- {path}")

    lines.extend(["", "Suggested verification commands:"])
    for command in VERIFY_COMMANDS:
        lines.append(f"- {command}")

    lines.extend(
        [
            "",
            "This command is read-only. Review git status before deleting any artifact.",
        ]
    )
    return "\n".join(lines)


def _scratch_path_to_dict(path: Path, rule: ScratchRule, root: Path) -> dict[str, str]:
    try:
        relative_path = path.relative_to(root).as_posix()
    except ValueError:
        relative_path = path.as_posix()
    return {
        "name": path.name,
        "path": relative_path,
        "kind": "dir" if path.is_dir() else "file",
        "description": rule.description,
    }


def to_report_dict(
    root: Path,
    rules: Iterable[ScratchRule] = SCRATCH_RULES,
    max_items: int = 40,
    list_all: bool = False,
) -> dict[str, object]:
    scratch_paths = find_scratch_paths(root, rules)
    tracked = list_tracked_scratch(root, rules)
    displayed_paths, remaining = split_display_items(scratch_paths, max_items=max_items, list_all=list_all)
    return {
        "root": root.as_posix(),
        "scratch_count": len(scratch_paths),
        "scratch_artifacts": [
            _scratch_path_to_dict(path, rule, root) for path, rule in displayed_paths
        ],
        "remaining_scratch_count": remaining,
        "tracked_scratch_artifacts": [path.as_posix() for path in tracked],
        "protected_paths": list(PROTECTED_PATHS),
        "suggested_verification_commands": list(VERIFY_COMMANDS),
    }


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(
        description="Report local maintenance artifacts without deleting anything."
    )
    parser.add_argument("--root", default=".", help="Repository root to audit. Defaults to current directory.")
    parser.add_argument("--all", action="store_true", help="List every scratch artifact instead of showing a capped list.")
    parser.add_argument(
        "--max-items",
        type=int,
        default=40,
        help="Maximum scratch artifacts to show unless --all is used. Defaults to 40.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.json:
        import json

        print(json.dumps(to_report_dict(root, max_items=args.max_items, list_all=args.all), ensure_ascii=False, indent=2))
    else:
        print(format_report(root, max_items=args.max_items, list_all=args.all))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
