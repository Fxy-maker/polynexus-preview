"""Run local maintenance verification commands for PolyNexus."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class GateCommand:
    label: str
    argv: list[str]


Runner = Callable[[GateCommand], int]

_PUBLICATION_EXTENSION = re.compile(
    r"\.(?:pdf|svg|png|jpe?g|tiff)(?:$|[^A-Za-z0-9])",
    re.IGNORECASE,
)


def scan_migrated_figure_provider(path: Path) -> list[str]:
    """Reject output behavior in a migrated scientific figure provider."""

    path = Path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if _tree_calls_savefig(tree):
        return [
            f"{path.name}: migrated figure providers must not call savefig"
        ]
    if _tree_contains_publication_extension(tree):
        return [
            f"{path.name}: migrated figure providers must not choose output formats"
        ]
    return []


def scan_figure_lifecycle_sources(root: Path) -> list[str]:
    """Apply figure ownership boundaries to all currently migrated sources."""

    root = Path(root)
    failures: list[str] = []
    provider = root / "polynexus" / "core" / "ir_engine" / "figure_provider.py"
    if provider.is_file():
        failures.extend(scan_migrated_figure_provider(provider))

    figures_dir = root / "polynexus" / "core" / "figures"
    excluded = {"renderer.py", "export_service.py"}
    for path in sorted(figures_dir.glob("*.py")):
        if path.name in excluded:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _tree_calls_savefig(tree):
            failures.append(
                f"{path.name}: only the shared renderer/export service may call savefig"
            )
        if path.name != "profiles.py" and _tree_contains_publication_extension(tree):
            failures.append(
                f"{path.name}: only global profiles may choose output formats"
            )
    return failures


def _tree_calls_savefig(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "savefig":
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "savefig":
            return True
    return False


def _tree_contains_publication_extension(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _PUBLICATION_EXTENSION.search(node.value)
        for node in ast.walk(tree)
    )


def default_commands(include_all_tests: bool = False) -> list[GateCommand]:
    commands = [
        GateCommand("compile", ["python", "-m", "compileall", "scripts", "polynexus", "tests", "-q"]),
        GateCommand(
            "focused-tests",
            [
                "pytest",
                "tests/test_core.py",
                "tests/test_analysis_history_service.py",
                "tests/test_analysis_run_service.py",
                "tests/test_boundary_audit.py",
                "tests/test_cli_output.py",
                "tests/test_cli_parser.py",
                "tests/test_cli_wrappers.py",
                "tests/test_export_context_service.py",
                "tests/test_context_suggestion_service.py",
                "tests/test_history_table_service.py",
                "tests/test_figure_window_service.py",
                "tests/test_maintenance_audit.py",
                "tests/test_maintenance_cleanup.py",
                "tests/test_results_review_service.py",
                "tests/test_results_table_service.py",
                "tests/test_sample_analysis_service.py",
                "tests/test_work_memory_service.py",
                "tests/test_quality_gate.py",
                "-q",
            ],
        ),
    ]
    if include_all_tests:
        commands.append(GateCommand("all-tests", ["pytest", "-q"]))
    commands.append(GateCommand("whitespace", ["git", "diff", "--check"]))
    return commands


def subprocess_runner(root: Path) -> Runner:
    def run(command: GateCommand) -> int:
        completed = subprocess.run(command.argv, cwd=root, check=False)
        return int(completed.returncode)

    return run


def run_commands(commands: Iterable[GateCommand], runner: Runner) -> int:
    for command in commands:
        print(f"[quality-gate] {command.label}: {' '.join(command.argv)}", flush=True)
        result = runner(command)
        if result != 0:
            print(f"[quality-gate] {command.label} failed with exit code {result}", file=sys.stderr)
            return result
    print("[quality-gate] all selected checks passed", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser(description="Run local PolyNexus maintenance checks.")
    parser.add_argument("--root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--all-tests", action="store_true", help="Include full pytest -q after focused tests.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    boundary_failures = scan_figure_lifecycle_sources(root)
    if boundary_failures:
        for failure in boundary_failures:
            print(f"[quality-gate] {failure}", file=sys.stderr)
        return 1
    return run_commands(default_commands(include_all_tests=args.all_tests), subprocess_runner(root))


if __name__ == "__main__":
    raise SystemExit(main())
