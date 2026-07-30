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
LEGACY_TEST_ROOTS_ENV = "POLYNEXUS_LEGACY_TEST_ROOTS"
EXTERNAL_LEGACY_PATTERNS = ("temppolynexus", "usersfanxuy~1appdatalocaltemp")
RETENTION_ENV = "POLYNEXUS_TEST_RETENTION"
RETENTION_PROFILES = {"ephemeral", "review", "evidence", "legacy"}


@dataclass(frozen=True)
class RetentionPolicy:
    name: str
    success_after: timedelta | None
    failure_after: timedelta | None


@dataclass(frozen=True)
class RunState:
    schema_version: int
    run_id: str
    path: Path
    project_root: Path
    git_head: str
    pid: int
    process_started_at: datetime
    profile: str
    status: str
    exit_code: int | None
    created_at: datetime
    finished_at: datetime | None
    keep_until: datetime | None


RETENTION_POLICIES = {
    "ephemeral": RetentionPolicy("ephemeral", None, timedelta(hours=24)),
    "review": RetentionPolicy("review", timedelta(days=7), timedelta(days=7)),
    "evidence": RetentionPolicy("evidence", None, None),
    "legacy": RetentionPolicy("legacy", timedelta(hours=24), timedelta(hours=24)),
}


@dataclass(frozen=True)
class TestArtifact:
    __test__ = False

    path: Path
    kind: str
    size_bytes: int
    modified_at: datetime
    finished_at: datetime | None = None
    profile: str | None = None
    status: str | None = None
    exit_code: int | None = None
    keep_until: datetime | None = None
    manifest_error: str | None = None


@dataclass(frozen=True)
class CleanupDecision:
    eligible: bool
    reason: str
    emergency: bool = False


@dataclass(frozen=True)
class CleanupFailure:
    path: Path
    error_type: str
    message: str


@dataclass(frozen=True)
class CleanupApplyResult:
    removed: tuple[Path, ...] = ()
    failures: tuple[CleanupFailure, ...] = ()

    @property
    def success(self) -> bool:
        return not self.failures


def resolve_retention_profile(environ: Mapping[str, str] | None = None) -> str:
    """Resolve the requested run profile, failing closed to review."""

    values = os.environ if environ is None else environ
    requested = values.get(RETENTION_ENV, "").strip().lower()
    if not requested:
        return "ephemeral"
    return requested if requested in RETENTION_PROFILES else "review"


def run_state_path(path: Path) -> Path:
    """Return the manifest path for one managed run directory."""

    return path.resolve() / "run_state.json"


def _datetime_to_json(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat()


def _datetime_from_json(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def write_run_state(state: RunState) -> None:
    """Write operational run metadata without copying test artifacts."""

    payload = {
        "schema_version": state.schema_version,
        "run_id": state.run_id,
        "path": str(state.path.resolve()),
        "project_root": str(state.project_root.resolve()),
        "git_head": state.git_head,
        "pid": state.pid,
        "process_started_at": _datetime_to_json(state.process_started_at),
        "profile": state.profile,
        "status": state.status,
        "exit_code": state.exit_code,
        "created_at": _datetime_to_json(state.created_at),
        "finished_at": _datetime_to_json(state.finished_at),
        "keep_until": _datetime_to_json(state.keep_until),
    }
    run_state_path(state.path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def read_run_state(path: Path) -> RunState | None:
    """Read a run manifest, returning None when it does not exist."""

    manifest = run_state_path(path)
    if not manifest.is_file():
        return None
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return RunState(
        schema_version=int(payload["schema_version"]),
        run_id=str(payload["run_id"]),
        path=Path(payload["path"]).resolve(),
        project_root=Path(payload["project_root"]).resolve(),
        git_head=str(payload["git_head"]),
        pid=int(payload["pid"]),
        process_started_at=_datetime_from_json(payload["process_started_at"]),
        profile=str(payload["profile"]),
        status=str(payload["status"]),
        exit_code=None if payload["exit_code"] is None else int(payload["exit_code"]),
        created_at=_datetime_from_json(payload["created_at"]),
        finished_at=_datetime_from_json(payload["finished_at"]),
        keep_until=_datetime_from_json(payload["keep_until"]),
    )


def _git_head(project_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return "unknown"
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def begin_run_state(
    path: Path,
    *,
    project_root: Path,
    profile: str,
    now: datetime | None = None,
    pid: int | None = None,
    git_head: str | None = None,
) -> RunState:
    """Create and persist a running manifest for an owned pytest directory."""

    created_at = now or datetime.now(timezone.utc)
    resolved_path = path.resolve()
    resolved_path.mkdir(parents=True, exist_ok=True)
    state = RunState(
        schema_version=1,
        run_id=resolved_path.name,
        path=resolved_path,
        project_root=Path(project_root).resolve(),
        git_head=git_head or _git_head(Path(project_root).resolve()),
        pid=pid or os.getpid(),
        process_started_at=created_at,
        profile=profile if profile in RETENTION_PROFILES else "review",
        status="running",
        exit_code=None,
        created_at=created_at,
        finished_at=None,
        keep_until=None,
    )
    write_run_state(state)
    return state


def _keep_until(profile: str, *, passed: bool, now: datetime) -> datetime | None:
    policy = RETENTION_POLICIES[profile]
    duration = policy.success_after if passed else policy.failure_after
    return None if duration is None else now + duration


def failure_deadline(profile: str, now: datetime, *, emergency: bool = False) -> datetime | None:
    """Return the retention deadline for a failed or interrupted run."""

    policy = RETENTION_POLICIES.get(profile, RETENTION_POLICIES["review"])
    if emergency and profile == "ephemeral":
        return now + timedelta(hours=2)
    return None if policy.failure_after is None else now + policy.failure_after


def emergency_pressure(path: Path, *, threshold: float = 0.10) -> bool:
    """Return whether the volume containing ``path`` is below free-space threshold."""

    usage = shutil.disk_usage(path.anchor or path)
    return usage.total > 0 and usage.free / usage.total < threshold


def finalize_run_state(
    state: RunState,
    *,
    exit_code: int,
    now: datetime | None = None,
    process_active: bool = False,
) -> RunState:
    """Persist a terminal outcome and remove only owned ephemeral successes."""

    finished_at = now or datetime.now(timezone.utc)
    passed = exit_code == 0
    status = "passed" if passed else "failed"
    if process_active:
        status = "cleanup_pending"
    updated = RunState(
        schema_version=state.schema_version,
        run_id=state.run_id,
        path=state.path,
        project_root=state.project_root,
        git_head=state.git_head,
        pid=state.pid,
        process_started_at=state.process_started_at,
        profile=state.profile,
        status=status,
        exit_code=exit_code,
        created_at=state.created_at,
        finished_at=finished_at,
        keep_until=_keep_until(state.profile, passed=passed, now=finished_at),
    )
    write_run_state(updated)
    if passed and state.profile == "ephemeral" and not process_active and not state.path.is_symlink():
        shutil.rmtree(state.path)
    return updated


def reconcile_run_state(state: RunState, *, process_active: bool, now: datetime | None = None) -> RunState:
    """Mark an abandoned running process as interrupted after it exits."""

    if state.status != "running" or process_active:
        return state
    finished_at = now or datetime.now(timezone.utc)
    updated = RunState(
        schema_version=state.schema_version,
        run_id=state.run_id,
        path=state.path,
        project_root=state.project_root,
        git_head=state.git_head,
        pid=state.pid,
        process_started_at=state.process_started_at,
        profile=state.profile,
        status="interrupted",
        exit_code=None,
        created_at=state.created_at,
        finished_at=finished_at,
        keep_until=failure_deadline(
            state.profile,
            finished_at,
            emergency=emergency_pressure(state.path),
        ),
    )
    write_run_state(updated)
    return updated


def resolve_test_root(project_root: Path, environ: Mapping[str, str] | None = None) -> Path:
    """Resolve the external test-storage root for one repository."""

    values = os.environ if environ is None else environ
    override = values.get(TEST_ROOT_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    anchor = Path(project_root).resolve().anchor
    return (Path(anchor) / "PolyNexus-test-runs").resolve()


def resolve_legacy_test_roots(
    project_root: Path,
    environ: Mapping[str, str] | None = None,
    *,
    extra_roots: Iterable[str | Path] = (),
) -> list[Path]:
    """Resolve roots that may contain legacy test output directories.

    The repository root is always included. On Windows, the system drive is
    also scanned for the historical ``TempPolyNexus*`` naming convention.
    ``POLYNEXUS_LEGACY_TEST_ROOTS`` can replace that automatic external-root
    choice, and CLI-supplied roots are appended explicitly.
    """

    values = os.environ if environ is None else environ
    roots: list[Path] = [Path(project_root).resolve()]
    configured = values.get(LEGACY_TEST_ROOTS_ENV, "").strip()
    if configured:
        roots.extend(Path(value).expanduser() for value in configured.split(os.pathsep) if value.strip())
    elif os.name == "nt":
        system_drive = values.get("SystemDrive", "C:").strip() or "C:"
        roots.append(Path(system_drive.rstrip("\\/") + "\\"))
    roots.extend(Path(value).expanduser() for value in extra_roots)

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        resolved = root.resolve()
        key = str(resolved).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique


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
    emergency: bool = False,
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
        emergency_decision = False
        path = artifact.path.resolve()
        if any(path == item or item in path.parents for item in protected):
            reason = "protected path"
            eligible = False
        elif any(item == path or path in item.parents for item in tracked):
            reason = "tracked by Git"
            eligible = False
        elif is_path_referenced(path, commands) or (
            artifact.kind == "legacy-external" and pytest_active
        ) or (
            artifact.kind == "legacy" and path.name == ".pytest_tmp" and pytest_active
        ):
            reason = "referenced by a running process"
            eligible = False
        elif artifact.manifest_error == "invalid":
            reason = "manifest-invalid"
            eligible = False
        elif artifact.profile == "evidence":
            reason = "evidence profile"
            eligible = False
        elif artifact.profile == "ephemeral" and artifact.status == "passed":
            reason = "owned terminal cleanup only"
            eligible = False
        elif emergency and (
            (
                artifact.profile == "ephemeral"
                and artifact.status in {"failed", "interrupted", "cleanup_pending"}
            )
            or (
                artifact.manifest_error is None
                and (artifact.profile == "legacy" or artifact.kind in {"legacy", "legacy-external"})
            )
        ):
            reference_time = artifact.finished_at or artifact.modified_at
            if reference_time.tzinfo is None:
                reference_time = reference_time.replace(tzinfo=timezone.utc)
            eligible = now - reference_time >= timedelta(hours=2)
            reason = "eligible (emergency)" if eligible else "younger than retention"
            emergency_decision = eligible
        elif artifact.keep_until is not None:
            modified_at = artifact.keep_until
            if modified_at.tzinfo is None:
                modified_at = modified_at.replace(tzinfo=timezone.utc)
            eligible = now >= modified_at
            reason = "eligible" if eligible else "younger than retention"
            emergency_decision = False
        else:
            modified_at = artifact.modified_at
            if modified_at.tzinfo is None:
                modified_at = modified_at.replace(tzinfo=timezone.utc)
            eligible = now - modified_at >= older_than
            reason = "eligible" if eligible else "younger than retention"
            emergency_decision = False
        plan[artifact] = CleanupDecision(
            eligible=eligible,
            reason=reason,
            emergency=emergency_decision,
        )
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


def discover_artifacts(
    project_root: Path,
    test_root: Path | None = None,
    *,
    legacy_roots: Iterable[Path] | None = None,
) -> list[TestArtifact]:
    """Find legacy basetemps and managed per-run basetemps.

    ``legacy_roots`` is explicit for library callers. The CLI supplies the
    repository root plus configured/system-drive roots so old C-drive test
    output is visible without scanning arbitrary user directories.
    """

    root = project_root.resolve()
    artifacts: list[TestArtifact] = []
    roots = [root] if legacy_roots is None else [Path(path).resolve() for path in legacy_roots]
    seen: set[str] = set()
    for legacy_root in roots:
        key = str(legacy_root).casefold()
        if key in seen or not legacy_root.is_dir():
            continue
        seen.add(key)
        try:
            candidates = list(legacy_root.iterdir())
        except OSError:
            continue
        for path in candidates:
            if not path.is_dir():
                continue
            lowered = path.name.lower()
            is_project_legacy = "pytest_tmp" in lowered or "tmp_pytest" in lowered
            is_external_legacy = any(lowered.startswith(prefix) for prefix in EXTERNAL_LEGACY_PATTERNS)
            if (legacy_root == root and is_project_legacy) or (legacy_root != root and is_external_legacy):
                kind = "legacy" if legacy_root == root else "legacy-external"
                artifacts.append(TestArtifact(path, kind, _directory_size(path), _modified_at(path)))

    managed_root = (test_root or resolve_test_root(root)) / "pytest"
    if managed_root.is_dir():
        for path in managed_root.glob("run-*"):
            if path.is_dir():
                state: RunState | None = None
                manifest_error: str | None = None
                try:
                    state = read_run_state(path)
                except (OSError, TypeError, ValueError, KeyError):
                    manifest_error = "invalid"
                artifacts.append(
                    TestArtifact(
                        path,
                        "managed",
                        _directory_size(path),
                        _modified_at(path),
                        profile=state.profile if state else "legacy",
                        status=state.status if state else "manifest-invalid" if manifest_error else "legacy",
                        exit_code=state.exit_code if state else None,
                        keep_until=state.keep_until if state else None,
                        manifest_error=manifest_error,
                    )
                )
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


def apply_cleanup_detailed(
    plan: Mapping[TestArtifact, CleanupDecision],
    *,
    apply: bool = False,
    approved_roots: Iterable[Path] | None = None,
) -> CleanupApplyResult:
    """Remove eligible directories independently and record deletion failures."""

    if not apply:
        return CleanupApplyResult()
    roots = [Path(root).resolve() for root in approved_roots or ()]
    removed: list[Path] = []
    failures: list[CleanupFailure] = []
    for artifact, decision in plan.items():
        if not decision.eligible:
            continue
        path = artifact.path
        resolved = path.resolve()
        if roots and (path.is_symlink() or not any(root == resolved or root in resolved.parents for root in roots)):
            continue
        try:
            shutil.rmtree(path)
        except OSError as error:
            failures.append(
                CleanupFailure(
                    path=artifact.path,
                    error_type=type(error).__name__,
                    message=str(error),
                )
            )
            continue
        removed.append(artifact.path)
    return CleanupApplyResult(tuple(removed), tuple(failures))


def apply_cleanup(
    plan: Mapping[TestArtifact, CleanupDecision],
    *,
    apply: bool = False,
    approved_roots: Iterable[Path] | None = None,
) -> list[Path]:
    """Compatibility wrapper returning only successfully removed paths."""

    return list(
        apply_cleanup_detailed(
            plan,
            apply=apply,
            approved_roots=approved_roots,
        ).removed
    )


def _protected_paths(project_root: Path) -> list[Path]:
    return [
        project_root / "tests" / "eval",
        project_root / "docs" / "baselines",
        project_root / "测试数据",
    ]


def _build_plan(
    args: argparse.Namespace,
) -> tuple[Path, dict[TestArtifact, CleanupDecision], list[Path]]:
    project_root = Path(args.root).resolve()
    test_root = Path(args.test_root).resolve() if args.test_root else resolve_test_root(project_root)
    legacy_roots = resolve_legacy_test_roots(project_root, extra_roots=args.legacy_root)
    artifacts = discover_artifacts(
        project_root,
        test_root,
        legacy_roots=legacy_roots,
    )
    plan = build_cleanup_plan(
        artifacts,
        now=datetime.now(timezone.utc),
        older_than=timedelta(hours=args.older_than_hours),
        active_command_lines=running_process_command_lines(),
        tracked_paths=tracked_paths(project_root),
        protected_paths=_protected_paths(project_root),
    )
    approved_roots = [test_root / "pytest", *legacy_roots]
    return project_root, plan, approved_roots


def _json_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _report_summary(
    plan: Mapping[TestArtifact, CleanupDecision],
) -> dict[str, object]:
    by_profile: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    total_bytes = 0
    eligible_bytes = 0
    for artifact, decision in plan.items():
        total_bytes += artifact.size_bytes
        if decision.eligible:
            eligible_bytes += artifact.size_bytes
        profile = artifact.profile or "legacy"
        by_profile[profile] = by_profile.get(profile, 0) + 1
        by_reason[decision.reason] = by_reason.get(decision.reason, 0) + 1
    return {
        "artifact_count": len(plan),
        "total_bytes": total_bytes,
        "eligible_bytes": eligible_bytes,
        "by_profile": dict(sorted(by_profile.items())),
        "by_reason": dict(sorted(by_reason.items())),
    }


def _emit_report(
    project_root: Path,
    plan: Mapping[TestArtifact, CleanupDecision],
    *,
    mode: str,
    removed: Iterable[Path] = (),
    failures: Iterable[CleanupFailure] = (),
    as_json: bool,
) -> None:
    removed_paths = {str(path.resolve()) for path in removed}
    cleanup_failures = tuple(failures)
    summary = _report_summary(plan)
    if as_json:
        payload = {
            "root": str(project_root),
            "mode": mode,
            "summary": summary,
            "artifacts": [
                {
                    "path": str(artifact.path),
                    "kind": artifact.kind,
                    "size_bytes": artifact.size_bytes,
                    "modified_at": artifact.modified_at.isoformat(),
                    "profile": artifact.profile,
                    "status": artifact.status,
                    "exit_code": artifact.exit_code,
                    "keep_until": _json_datetime(artifact.keep_until),
                    "manifest_error": artifact.manifest_error,
                    "eligible": decision.eligible,
                    "reason": decision.reason,
                    "removed": str(artifact.path.resolve()) in removed_paths,
                }
                for artifact, decision in plan.items()
            ],
            "failures": [
                {
                    "path": str(failure.path),
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
                for failure in cleanup_failures
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"PolyNexus test storage ({mode})")
    print(f"Root: {project_root}")
    print(f"Artifacts: {summary['artifact_count']}")
    print(f"Total: {summary['total_bytes']} bytes")
    print(f"Eligible: {summary['eligible_bytes']} bytes")
    print(f"By profile: {summary['by_profile']}")
    print(f"By reason: {summary['by_reason']}")
    print(f"Cleanup failures: {len(cleanup_failures)}")
    for artifact, decision in plan.items():
        size_mb = artifact.size_bytes / (1024 * 1024)
        state = "eligible" if decision.eligible else decision.reason
        if str(artifact.path.resolve()) in removed_paths:
            state = "removed"
        print(f"- {artifact.path} [{artifact.kind}] {size_mb:.1f} MB - {state}")
    for failure in cleanup_failures:
        print(
            f"! {failure.path} [{failure.error_type}] - {failure.message}",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("report", "clean"):
        subparser = subparsers.add_parser(name)
        subparser.add_argument("--root", default=".")
        subparser.add_argument("--test-root")
        subparser.add_argument(
            "--legacy-root",
            action="append",
            default=[],
            help="Additional root containing legacy TempPolyNexus test directories",
        )
        subparser.add_argument("--older-than-hours", type=float, default=24.0)
        subparser.add_argument("--json", action="store_true", dest="as_json")
        if name == "clean":
            subparser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        project_root, plan, approved_roots = _build_plan(args)
        apply_result = apply_cleanup_detailed(
            plan,
            apply=getattr(args, "apply", False),
            approved_roots=approved_roots,
        )
        _emit_report(
            project_root,
            plan,
            mode="apply" if getattr(args, "apply", False) else "dry-run",
            removed=apply_result.removed,
            failures=apply_result.failures,
            as_json=args.as_json,
        )
        return 1 if apply_result.failures else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[test-storage] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
