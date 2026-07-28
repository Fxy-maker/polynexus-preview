"""Report and safely clean PolyNexus pytest storage."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping


TEST_ROOT_ENV = "POLYNEXUS_TEST_ROOT"


@dataclass(frozen=True)
class TestArtifact:
    __test__ = False

    path: Path
    kind: str
    size_bytes: int
    modified_at: datetime


@dataclass(frozen=True)
class CleanupDecision:
    eligible: bool
    reason: str


def resolve_test_root(project_root: Path, environ: Mapping[str, str] | None = None) -> Path:
    """Resolve the external test-storage root for one repository."""

    values = os.environ if environ is None else environ
    override = values.get(TEST_ROOT_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    anchor = Path(project_root).resolve().anchor
    return (Path(anchor) / "PolyNexus-test-runs").resolve()


def create_run_basetemp(
    project_root: Path,
    *,
    now: datetime | None = None,
    pid: int | None = None,
) -> Path:
    """Create a unique external per-process pytest basetemp directory."""

    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%S%fZ")
    run_root = resolve_test_root(project_root) / "pytest"
    run_root.mkdir(parents=True, exist_ok=True)
    base_name = f"run-{timestamp}-{pid or os.getpid()}"
    candidate = run_root / base_name
    suffix = 0
    while candidate.exists():
        suffix += 1
        candidate = run_root / f"{base_name}-{suffix}"
    candidate.mkdir()
    return candidate


def is_path_referenced(path: Path, command_lines: Iterable[str]) -> bool:
    """Return whether a normalized path occurs in a process command line."""

    wanted = str(path.resolve()).replace("\\", "/").lower()
    return any(wanted in line.replace("\\", "/").lower() for line in command_lines)


def pytest_process_active(command_lines: Iterable[str]) -> bool:
    """Return whether any supplied process command line is running pytest."""

    return any("pytest" in line.lower() for line in command_lines)


def build_cleanup_plan(
    artifacts: Iterable[TestArtifact],
    *,
    now: datetime,
    older_than: timedelta,
    active_command_lines: Iterable[str] = (),
    tracked_paths: Iterable[Path] = (),
    protected_paths: Iterable[Path] = (),
) -> dict[TestArtifact, CleanupDecision]:
    """Classify artifacts without touching the filesystem."""

    commands = list(active_command_lines)
    tracked = [path.resolve() for path in tracked_paths]
    protected = [path.resolve() for path in protected_paths]
    pytest_active = pytest_process_active(commands)
    plan: dict[TestArtifact, CleanupDecision] = {}
    for artifact in artifacts:
        path = artifact.path.resolve()
        if any(path == item or item in path.parents for item in protected):
            reason = "protected path"
            eligible = False
        elif any(item == path or path in item.parents for item in tracked):
            reason = "tracked by Git"
            eligible = False
        elif is_path_referenced(path, commands) or (
            artifact.kind == "legacy" and path.name == ".pytest_tmp" and pytest_active
        ):
            reason = "referenced by a running process"
            eligible = False
        else:
            modified_at = artifact.modified_at
            if modified_at.tzinfo is None:
                modified_at = modified_at.replace(tzinfo=timezone.utc)
            eligible = now - modified_at >= older_than
            reason = "eligible" if eligible else "younger than retention"
        plan[artifact] = CleanupDecision(eligible=eligible, reason=reason)
    return plan


def _directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


def _modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)


def discover_artifacts(project_root: Path, test_root: Path | None = None) -> list[TestArtifact]:
    """Find legacy repository basetemps and managed per-run basetemps."""

    root = project_root.resolve()
    artifacts: list[TestArtifact] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        lowered = path.name.lower()
        if "pytest_tmp" in lowered or "tmp_pytest" in lowered:
            artifacts.append(TestArtifact(path, "legacy", _directory_size(path), _modified_at(path)))

    managed_root = (test_root or resolve_test_root(root)) / "pytest"
    if managed_root.is_dir():
        for path in managed_root.glob("run-*"):
            if path.is_dir():
                artifacts.append(TestArtifact(path, "managed", _directory_size(path), _modified_at(path)))
    return sorted(artifacts, key=lambda item: str(item.path).lower())


def running_process_command_lines() -> list[str]:
    """Read process command lines on Windows; return empty on other systems."""

    if os.name != "nt":
        return []
    command = "Get-CimInstance Win32_Process | Select-Object -ExpandProperty CommandLine"
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def tracked_paths(project_root: Path) -> list[Path]:
    """Return Git-tracked paths for protection checks."""

    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [(project_root / line).resolve() for line in completed.stdout.splitlines() if line.strip()]


def apply_cleanup(plan: Mapping[TestArtifact, CleanupDecision], *, apply: bool = False) -> list[Path]:
    """Remove only eligible artifact directories when explicitly requested."""

    if not apply:
        return []
    removed: list[Path] = []
    for artifact, decision in plan.items():
        if not decision.eligible:
            continue
        shutil.rmtree(artifact.path)
        removed.append(artifact.path)
    return removed


def _protected_paths(project_root: Path) -> list[Path]:
    return [
        project_root / "tests" / "eval",
        project_root / "docs" / "baselines",
        project_root / "测试数据",
    ]


def _build_plan(args: argparse.Namespace) -> tuple[Path, dict[TestArtifact, CleanupDecision]]:
    project_root = Path(args.root).resolve()
    test_root = Path(args.test_root).resolve() if args.test_root else resolve_test_root(project_root)
    artifacts = discover_artifacts(project_root, test_root)
    plan = build_cleanup_plan(
        artifacts,
        now=datetime.now(timezone.utc),
        older_than=timedelta(hours=args.older_than_hours),
        active_command_lines=running_process_command_lines(),
        tracked_paths=tracked_paths(project_root),
        protected_paths=_protected_paths(project_root),
    )
    return project_root, plan


def _emit_report(
    project_root: Path,
    plan: Mapping[TestArtifact, CleanupDecision],
    *,
    mode: str,
    removed: Iterable[Path] = (),
    as_json: bool,
) -> None:
    removed_paths = {str(path.resolve()) for path in removed}
    if as_json:
        payload = {
            "root": str(project_root),
            "mode": mode,
            "artifacts": [
                {
                    "path": str(artifact.path),
                    "kind": artifact.kind,
                    "size_bytes": artifact.size_bytes,
                    "modified_at": artifact.modified_at.isoformat(),
                    "eligible": decision.eligible,
                    "reason": decision.reason,
                    "removed": str(artifact.path.resolve()) in removed_paths,
                }
                for artifact, decision in plan.items()
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"PolyNexus test storage ({mode})")
    print(f"Root: {project_root}")
    print(f"Artifacts: {len(plan)}")
    for artifact, decision in plan.items():
        size_mb = artifact.size_bytes / (1024 * 1024)
        state = "eligible" if decision.eligible else decision.reason
        if str(artifact.path.resolve()) in removed_paths:
            state = "removed"
        print(f"- {artifact.path} [{artifact.kind}] {size_mb:.1f} MB - {state}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("report", "clean"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--root", default=".")
        subparser.add_argument("--test-root")
        subparser.add_argument("--older-than-hours", type=float, default=24.0)
        subparser.add_argument("--json", action="store_true", dest="as_json")
        if name == "clean":
            subparser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        project_root, plan = _build_plan(args)
        removed = apply_cleanup(plan, apply=getattr(args, "apply", False))
        _emit_report(
            project_root,
            plan,
            mode="apply" if getattr(args, "apply", False) else "dry-run",
            removed=removed,
            as_json=args.as_json,
        )
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[test-storage] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
