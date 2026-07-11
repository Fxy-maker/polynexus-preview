"""Safe scratch artifact cleanup planner for PolyNexus worktrees."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.maintenance_common import relative_posix, split_display_items
from scripts.maintenance_audit import (
    PROTECTED_PATHS,
    SCRATCH_RULES,
    ScratchRule,
    find_scratch_paths,
    list_tracked_scratch,
)


@dataclass(frozen=True)
class CleanupCandidate:
    path: Path
    reason: str


@dataclass(frozen=True)
class CleanupPlan:
    removable: list[CleanupCandidate]
    skipped: list[CleanupCandidate]


def _is_protected(path: Path, root: Path, protected_prefixes: Iterable[str]) -> bool:
    relative = relative_posix(path, root)
    return any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in protected_prefixes)


def _is_tracked_or_contains_tracked(relative_path: str, tracked_paths: set[str]) -> bool:
    prefix = relative_path.rstrip("/") + "/"
    return relative_path in tracked_paths or any(path.startswith(prefix) for path in tracked_paths)


def build_cleanup_plan(
    root: Path,
    rules: Iterable[ScratchRule] = SCRATCH_RULES,
    tracked_paths: Iterable[Path] | None = None,
    protected_prefixes: Iterable[str] = PROTECTED_PATHS,
) -> CleanupPlan:
    root = root.resolve()
    tracked = {path.as_posix() for path in (tracked_paths if tracked_paths is not None else list_tracked_scratch(root, rules))}
    removable: list[CleanupCandidate] = []
    skipped: list[CleanupCandidate] = []

    for path, rule in find_scratch_paths(root, rules):
        relative = relative_posix(path, root)
        if _is_tracked_or_contains_tracked(relative, tracked):
            skipped.append(CleanupCandidate(path, "tracked by git"))
        elif _is_protected(path, root, protected_prefixes):
            skipped.append(CleanupCandidate(path, "protected path"))
        else:
            removable.append(CleanupCandidate(path, rule.description))

    return CleanupPlan(removable=removable, skipped=skipped)


def apply_cleanup(candidates: Iterable[CleanupCandidate], apply: bool = False) -> list[Path]:
    removed: list[Path] = []
    if not apply:
        return removed

    for candidate in candidates:
        path = candidate.path
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        removed.append(path)
    return removed


def format_plan(plan: CleanupPlan, root: Path, apply: bool, max_items: int = 40) -> str:
    removable, removable_remaining = split_display_items(plan.removable, max_items=max_items)
    skipped, skipped_remaining = split_display_items(plan.skipped, max_items=max_items)
    lines = [
        "PolyNexus maintenance cleanup",
        f"Root: {root}",
        f"Mode: {'apply' if apply else 'dry-run'}",
        "",
        f"Removable scratch artifacts: {len(plan.removable)} found",
    ]
    for candidate in removable:
        lines.append(f"- {relative_posix(candidate.path, root)} - {candidate.reason}")
    if removable_remaining > 0:
        lines.append(f"- ... {removable_remaining} more. Re-run with --all to list every artifact.")

    lines.extend(["", f"Skipped scratch artifacts: {len(plan.skipped)} found"])
    for candidate in skipped:
        lines.append(f"- {relative_posix(candidate.path, root)} - {candidate.reason}")
    if skipped_remaining > 0:
        lines.append(f"- ... {skipped_remaining} more. Re-run with --all to list every skipped artifact.")

    if not apply:
        lines.extend(["", "Dry-run only. Re-run with --apply to remove removable artifacts."])
    return "\n".join(lines)


def to_plan_dict(plan: CleanupPlan, root: Path, apply: bool, max_items: int = 40) -> dict[str, object]:
    removable, removable_remaining = split_display_items(plan.removable, max_items=max_items)
    skipped, skipped_remaining = split_display_items(plan.skipped, max_items=max_items)
    return {
        "root": root.as_posix(),
        "mode": "apply" if apply else "dry-run",
        "removable_count": len(plan.removable),
        "skipped_count": len(plan.skipped),
        "removable": [
            {"path": relative_posix(candidate.path, root), "reason": candidate.reason}
            for candidate in removable
        ],
        "skipped": [
            {"path": relative_posix(candidate.path, root), "reason": candidate.reason}
            for candidate in skipped
        ],
        "remaining_removable_count": removable_remaining,
        "remaining_skipped_count": skipped_remaining,
    }


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Plan or apply cleanup for local PolyNexus scratch artifacts.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--apply", action="store_true", help="Delete removable scratch artifacts.")
    parser.add_argument("--all", action="store_true", help="List every artifact instead of showing a capped list.")
    parser.add_argument("--max-items", type=int, default=40, help="Maximum artifacts to show unless --all is used.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    plan = build_cleanup_plan(root)
    max_items = len(plan.removable) + len(plan.skipped) if args.all else args.max_items
    removed = apply_cleanup(plan.removable, apply=args.apply)
    if args.json:
        import json

        payload = to_plan_dict(plan, root, apply=args.apply, max_items=max_items)
        if args.apply:
            payload["removed_count"] = len(removed)
            payload["removed"] = [
                relative_posix(candidate.path, root)
                for candidate in split_display_items(plan.removable, max_items=max_items)[0]
            ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_plan(plan, root, apply=args.apply, max_items=max_items))
    if args.apply and not args.json:
        print(f"Removed {len(removed)} scratch artifact(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
