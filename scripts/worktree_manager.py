"""Register, inspect, archive, and safely clean PolyNexus worktrees."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REGISTRY_ROOT = Path.home() / ".config" / "superpowers" / "worktrees" / "PolyNexus"
REGISTRY_PATH = REGISTRY_ROOT / "worktree-registry.json"
ARCHIVE_ROOT = REGISTRY_ROOT / "wip-archives"
DEFAULT_COOLDOWN = timedelta(hours=1)


def normalize_worktree_path(root: Path, raw_path: str) -> str:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = root / path
    return str(path.resolve())


def cleanup_decision(
    metadata: dict[str, Any],
    *,
    observed_branch: str,
    observed_head: str,
    dirty: bool,
    now: datetime,
    cooldown: timedelta = DEFAULT_COOLDOWN,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if metadata.get("owner") != "agent":
        reasons.append("worktree is not agent-owned")
    if metadata.get("status") != "pending_cleanup":
        reasons.append("status is not pending_cleanup")
    if dirty:
        reasons.append("worktree is dirty")
    if metadata.get("branch") != observed_branch:
        reasons.append("branch differs from metadata")
    if metadata.get("finished_commit") != observed_head:
        reasons.append("HEAD differs from finished commit")

    finished_at = _parse_datetime(metadata.get("finished_at"))
    if finished_at is None or now < finished_at + cooldown:
        reasons.append("cooldown not elapsed")
    return not reasons, reasons


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _git(path: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=path, check=False, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _git_worktree_records(root: Path) -> list[dict[str, str]]:
    lines = _git(root, "worktree", "list", "--porcelain").splitlines()
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in lines + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return records


def _branch(record: dict[str, str]) -> str:
    return record.get("branch", "").removeprefix("refs/heads/")


def _registry() -> dict[str, dict[str, Any]]:
    if not REGISTRY_PATH.is_file():
        return {}
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def legacy_candidates(
    records: list[dict[str, str]],
    registry: dict[str, dict[str, Any]],
    current_root: Path,
    managed_root: Path,
) -> list[dict[str, str]]:
    """Select unregistered legacy ``codex/*`` worktrees under ``managed_root``."""

    current = current_root.resolve()
    managed = managed_root.resolve()
    candidates: list[dict[str, str]] = []
    for record in records:
        path = Path(record.get("worktree", "")).resolve()
        branch = _branch(record)
        if path == current or path == managed or managed not in path.parents:
            continue
        if not branch.startswith("codex/") or str(path) in registry:
            continue
        candidates.append(record)
    return candidates


def adoption_metadata(
    record: dict[str, str], *, task: str, dirty: bool, now: datetime
) -> dict[str, Any]:
    """Build registry metadata for one explicitly adopted legacy worktree."""

    adopted_at = now.isoformat()
    return {
        "owner": "agent",
        "status": "legacy_dirty" if dirty else "pending_cleanup",
        "task": task,
        "path": str(Path(record["worktree"]).resolve()),
        "branch": _branch(record),
        "finished_commit": "" if dirty else record.get("HEAD", ""),
        "finished_at": "" if dirty else adopted_at,
        "legacy_adopted_at": adopted_at,
        "dirty": dirty,
    }


def _save_registry(value: dict[str, dict[str, Any]]) -> None:
    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = REGISTRY_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(REGISTRY_PATH)


def _find_record(root: Path, target: str) -> tuple[dict[str, str], Path] | None:
    wanted = normalize_worktree_path(root, target)
    for record in _git_worktree_records(root):
        path = Path(record.get("worktree", "")).resolve()
        if str(path) == wanted or path.name == target or _branch(record) == target:
            return record, path
    return None


def _status(path: Path) -> bool:
    return bool(_git(path, "status", "--porcelain", check=False).strip())


def _register(root: Path, target: str, task: str, owner: str) -> int:
    found = _find_record(root, target)
    if found is None:
        print(f"[worktree] not found: {target}", file=sys.stderr)
        return 1
    record, path = found
    registry = _registry()
    key = str(path)
    current = registry.get(key, {})
    current.update(
        {
            "owner": owner,
            "task": task,
            "status": current.get("status", "active"),
            "path": key,
            "branch": _branch(record),
            "registered_at": current.get("registered_at", _now().isoformat()),
        }
    )
    registry[key] = current
    _save_registry(registry)
    print(f"[worktree] registered {key}")
    return 0


def _finish(root: Path, target: str, reason: str) -> int:
    found = _find_record(root, target)
    if found is None:
        print(f"[worktree] not found: {target}", file=sys.stderr)
        return 1
    record, path = found
    if _status(path):
        print("[worktree] cannot mark dirty worktree finished", file=sys.stderr)
        return 1
    registry = _registry()
    key = str(path)
    metadata = registry.get(key, {})
    metadata.update(
        {
            "owner": metadata.get("owner", "unknown"),
            "status": "pending_cleanup",
            "branch": _branch(record),
            "finished_commit": record.get("HEAD", ""),
            "finished_at": _now().isoformat(),
            "finish_reason": reason,
        }
    )
    registry[key] = metadata
    _save_registry(registry)
    print(f"[worktree] marked pending_cleanup: {key}")
    return 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _archive(root: Path, target: str, reason: str) -> int:
    found = _find_record(root, target)
    if found is None:
        print(f"[worktree] not found: {target}", file=sys.stderr)
        return 1
    record, path = found
    if not path.is_dir():
        print(f"[worktree] worktree directory is missing: {path}", file=sys.stderr)
        return 1
    metadata = _registry().get(str(path), {})
    stamp = _now().strftime("%Y%m%dT%H%M%SZ")
    archive = ARCHIVE_ROOT / (metadata.get("task") or path.name) / stamp
    archive.mkdir(parents=True, exist_ok=False)

    diff = _git(path, "diff", "HEAD", check=False)
    (archive / "diff.patch").write_text(diff, encoding="utf-8")
    untracked = _git(path, "ls-files", "--others", "--exclude-standard", check=False)
    untracked_root = archive / "untracked_files"
    for relative in (line.strip() for line in untracked.splitlines() if line.strip()):
        source = path / relative
        if not source.is_file():
            continue
        destination = untracked_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    state = dict(metadata)
    state.update(
        {
            "path": str(path),
            "branch": _branch(record),
            "head": record.get("HEAD", ""),
            "dirty": _status(path),
            "archived_at": _now().isoformat(),
            "reason": reason,
        }
    )
    (archive / "task_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (archive / "reason.md").write_text(
        f"# Worktree archive\n\nReason: {reason}\n\n"
        f"Source: `{path}`\nBranch: `{_branch(record) or 'detached'}`\n",
        encoding="utf-8",
    )
    print(f"[worktree] archive created: {archive}")
    return 0


def _adopt_legacy(root: Path, apply: bool, as_json: bool, task_prefix: str) -> int:
    registry = _registry()
    candidates = legacy_candidates(
        _git_worktree_records(root), registry, root, REGISTRY_ROOT
    )
    items: list[dict[str, Any]] = []
    for record in candidates:
        path = Path(record["worktree"]).resolve()
        dirty = _status(path) if path.is_dir() else True
        branch = _branch(record)
        task = f"{task_prefix}{branch.replace('/', '-') }"
        item: dict[str, Any] = {
            "path": str(path),
            "branch": branch,
            "head": record.get("HEAD", ""),
            "dirty": dirty,
            "action": "archive-and-retain" if dirty else "register-pending_cleanup",
            "applied": False,
        }
        if apply:
            metadata = adoption_metadata(
                record, task=task, dirty=dirty, now=_now()
            )
            registry[str(path)] = metadata
            _save_registry(registry)
            if dirty:
                archive_result = _archive(
                    root, str(path), "legacy worktree adopted while dirty"
                )
                if archive_result != 0:
                    return archive_result
            item["applied"] = True
        items.append(item)

    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=2, sort_keys=True))
    elif not items:
        print("[worktree] no eligible legacy worktrees")
    else:
        print("PATH                                                   BRANCH                 ACTION")
        for item in items:
            state = "applied" if item["applied"] else "would-apply"
            print(
                f"{item['path'][:52]:<52} {item['branch'][:22]:<22} "
                f"{state}:{item['action']}"
            )
    return 0


def _list(root: Path, as_json: bool) -> int:
    registry = _registry()
    items: list[dict[str, Any]] = []
    for record in _git_worktree_records(root):
        path = Path(record.get("worktree", "")).resolve()
        metadata = registry.get(str(path), {})
        items.append(
            {
                "path": str(path),
                "branch": _branch(record),
                "head": record.get("HEAD", ""),
                "dirty": _status(path) if path.is_dir() else True,
                "owner": metadata.get("owner", "unknown"),
                "task": metadata.get("task", ""),
                "status": metadata.get("status", "unregistered"),
                "finished_at": metadata.get("finished_at", ""),
            }
        )
    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print("STATUS             DIR                                      BRANCH")
        for item in items:
            print(f"{item['status']:<18} {Path(item['path']).name[:40]:<40} {item['branch']}")
    return 0


def _inspect(root: Path, target: str) -> int:
    found = _find_record(root, target)
    if found is None:
        print(f"[worktree] not found: {target}", file=sys.stderr)
        return 1
    record, path = found
    metadata = _registry().get(str(path), {})
    payload = {
        "path": str(path),
        "branch": _branch(record),
        "head": record.get("HEAD", ""),
        "dirty": _status(path) if path.is_dir() else True,
        "metadata": metadata,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _clean(root: Path, apply: bool, cooldown: timedelta) -> int:
    registry = _registry()
    now = _now()
    candidates: list[tuple[Path, dict[str, str]]] = []
    for record in _git_worktree_records(root):
        path = Path(record.get("worktree", "")).resolve()
        if path == root.resolve():
            continue
        metadata = registry.get(str(path), {})
        allowed, reasons = cleanup_decision(
            metadata,
            observed_branch=_branch(record),
            observed_head=record.get("HEAD", ""),
            dirty=_status(path) if path.is_dir() else True,
            now=now,
            cooldown=cooldown,
        )
        if allowed:
            candidates.append((path, record))
        else:
            print(f"[worktree] keep {path}: {', '.join(reasons)}")

    for path, _ in candidates:
        print(f"[worktree] {'remove' if apply else 'would remove'} {path}")
        if apply:
            subprocess.run(["git", "worktree", "remove", str(path)], cwd=root, check=True)
            registry.pop(str(path), None)
    if apply:
        _save_registry(registry)
        _git(root, "worktree", "prune")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Any PolyNexus worktree.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--json", action="store_true")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("target")
    register = subparsers.add_parser("register")
    register.add_argument("target")
    register.add_argument("--task", required=True)
    register.add_argument("--owner", default="agent")
    finish = subparsers.add_parser("finish")
    finish.add_argument("target")
    finish.add_argument("--reason", required=True)
    archive = subparsers.add_parser("archive")
    archive.add_argument("target")
    archive.add_argument("--reason", required=True)
    adopt = subparsers.add_parser(
        "adopt-legacy", help="Report or explicitly adopt old Superpowers worktrees."
    )
    adopt.add_argument("--apply", action="store_true")
    adopt.add_argument("--json", action="store_true", dest="as_json")
    adopt.add_argument("--task-prefix", default="legacy-")
    clean = subparsers.add_parser("clean")
    clean.add_argument("--apply", action="store_true")
    clean.add_argument("--cooldown-hours", type=float, default=1.0)

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.command == "list":
            return _list(root, args.json)
        if args.command == "inspect":
            return _inspect(root, args.target)
        if args.command == "register":
            return _register(root, args.target, args.task, args.owner)
        if args.command == "finish":
            return _finish(root, args.target, args.reason)
        if args.command == "archive":
            return _archive(root, args.target, args.reason)
        if args.command == "adopt-legacy":
            return _adopt_legacy(root, args.apply, args.as_json, args.task_prefix)
        return _clean(root, args.apply, timedelta(hours=args.cooldown_hours))
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[worktree] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
