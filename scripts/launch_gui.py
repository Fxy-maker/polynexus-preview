"""Launch the PolyNexus GUI from a verified source worktree."""

from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class LaunchError(RuntimeError):
    """Raised when the GUI launch boundary cannot be verified."""


@dataclass(frozen=True)
class LaunchInfo:
    root: Path
    interpreter: Path
    package_path: Path
    branch: str
    commit: str


def resolve_worktree_root(
    *, launcher_path: Path | None = None, requested_root: str | None = None
) -> Path:
    """Resolve an explicit worktree or the repository containing this script."""
    candidate = (
        Path(requested_root).expanduser()
        if requested_root
        else (launcher_path or Path(__file__)).resolve().parent.parent
    ).resolve()
    if not (candidate / "pyproject.toml").is_file():
        raise LaunchError(f"missing pyproject.toml under resolved worktree: {candidate}")
    if not (candidate / "polynexus" / "__init__.py").is_file():
        raise LaunchError(f"missing polynexus package under resolved worktree: {candidate}")
    return candidate


def validate_package_path(root: Path, package_path: Path) -> Path:
    """Reject an import that resolves outside the selected worktree."""
    resolved_root = root.resolve()
    resolved_package = package_path.resolve()
    package_root = resolved_root / "polynexus"
    try:
        resolved_package.relative_to(package_root)
    except ValueError as exc:
        raise LaunchError(
            "imported polynexus package is outside resolved worktree: "
            f"{resolved_package} (root: {resolved_root})"
        ) from exc
    return resolved_package


def prepare_environment(root: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    """Put the selected root first while preserving the caller environment."""
    env = dict(os.environ if base_env is None else base_env)
    existing = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
    ordered = [str(root), *[entry for entry in existing if Path(entry).resolve() != root]]
    env["PYTHONPATH"] = os.pathsep.join(ordered)
    env["POLYNEXUS_SOURCE_ROOT"] = str(root)
    return env


def _run_text(command: list[str], *, root: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LaunchError(f"command failed ({completed.returncode}): {detail}")
    return completed.stdout.strip()


def _git_value(root: Path, *arguments: str) -> str:
    value = _run_text(
        ["git", "-C", str(root), *arguments],
        root=root,
        env=prepare_environment(root),
    )
    return value or "detached"


def collect_launch_info(
    root: Path,
    *,
    interpreter: Path | None = None,
    base_env: dict[str, str] | None = None,
) -> LaunchInfo:
    """Probe the selected interpreter and collect the source identity."""
    selected_interpreter = (interpreter or Path(sys.executable)).resolve()
    if not selected_interpreter.is_file():
        raise LaunchError(f"GUI interpreter does not exist: {selected_interpreter}")
    env = prepare_environment(root, base_env)
    probe = _run_text(
        [
            str(selected_interpreter),
            "-c",
            "from pathlib import Path; import polynexus; "
            "print(Path(polynexus.__file__).resolve())",
        ],
        root=root,
        env=env,
    )
    package_path = validate_package_path(root, Path(probe.splitlines()[-1]))
    return LaunchInfo(
        root=root,
        interpreter=selected_interpreter,
        package_path=package_path,
        branch=_git_value(root, "branch", "--show-current"),
        commit=_git_value(root, "rev-parse", "--short", "HEAD"),
    )


def format_diagnostics(info: LaunchInfo) -> str:
    """Format source identity as stable key/value lines."""
    return "\n".join(
        [
            f"source_root={info.root}",
            f"python={info.interpreter}",
            f"branch={info.branch}",
            f"commit={info.commit}",
            f"package={info.package_path}",
        ]
    )


def build_gui_command(interpreter: Path, extra_args: list[str] | None = None) -> list[str]:
    """Build the normal PolyNexus GUI entry-point command."""
    return [str(interpreter), "-m", "polynexus", "--gui", *(extra_args or [])]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch PolyNexus GUI from one verified worktree"
    )
    parser.add_argument("--diagnose", action="store_true", help="print source identity and exit")
    parser.add_argument(
        "--worktree",
        help="explicit worktree root; defaults to this script's repository",
    )
    parser.add_argument("gui_args", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        root = resolve_worktree_root(requested_root=args.worktree)
        info = collect_launch_info(root)
        if args.diagnose:
            print(format_diagnostics(info))
            return 0
        extra_args = list(args.gui_args)
        if extra_args[:1] == ["--"]:
            extra_args.pop(0)
        return subprocess.run(
            build_gui_command(info.interpreter, extra_args),
            cwd=root,
            env=prepare_environment(root),
            check=False,
        ).returncode
    except LaunchError as exc:
        message = f"PolyNexus GUI launch failed: {exc}"
        print(message, file=sys.stderr)
        if sys.platform == "win32" and Path(sys.executable).stem.lower() == "pythonw":
            try:
                ctypes.windll.user32.MessageBoxW(None, message, "PolyNexus", 0x10)
            except Exception:
                pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
