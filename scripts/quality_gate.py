"""Run local maintenance verification commands for PolyNexus."""

from __future__ import annotations

import argparse
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
    return run_commands(default_commands(include_all_tests=args.all_tests), subprocess_runner(root))


if __name__ == "__main__":
    raise SystemExit(main())
