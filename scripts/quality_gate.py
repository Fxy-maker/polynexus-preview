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
_MIGRATED_FIGURE_WRAPPERS = (
    "saxs.py",
    "waxs.py",
    "dsc.py",
    "ir.py",
    "nmr.py",
)
_LEGACY_FIGURE_WRITERS = {
    "generate_all_figures",
    "generate_temperature_figures",
    "generate_strain_figures",
    "generate_temperature_2d_figures",
}
_TECHNIQUE_OUTPUT_SELECTORS = {
    "fig_format",
    "figure_format",
    "fig_dpi",
    "figure_dpi",
    "publication_png_dpi",
}


def _parse_python(path: Path) -> ast.Module:
    path = Path(path)
    return ast.parse(
        path.read_text(encoding="utf-8-sig"),
        filename=str(path),
    )


def scan_migrated_figure_provider(path: Path) -> list[str]:
    """Reject output behavior in a migrated scientific figure provider."""

    path = Path(path)
    tree = _parse_python(path)
    if _tree_calls_savefig(tree):
        return [f"{path.name}: migrated figure providers must not call savefig"]
    if _tree_contains_publication_extension(tree):
        return [f"{path.name}: migrated figure providers must not choose output formats"]
    if _tree_uses_technique_output_selector(tree):
        return [
            f"{path.name}: migrated wrappers/providers must not choose figure "
            "formats or publication DPI"
        ]
    return []


def scan_migrated_figure_wrapper(path: Path) -> list[str]:
    """Reject legacy writers and technique-local export choices in a wrapper."""

    path = Path(path)
    tree = _parse_python(path)
    failures: list[str] = []
    if _tree_imports_or_calls_legacy_writer(tree):
        failures.append(
            f"{path.name}: migrated wrappers must not import or call legacy figure writers"
        )
    if _tree_calls_savefig(tree):
        failures.append(f"{path.name}: migrated wrappers must not call savefig")
    if _tree_contains_publication_extension(tree):
        failures.append(f"{path.name}: migrated wrappers/providers must not choose output formats")
    if _tree_uses_technique_output_selector(tree):
        failures.append(
            f"{path.name}: migrated wrappers/providers must not choose figure "
            "formats or publication DPI"
        )
    return failures


def scan_recursive_figure_discovery(path: Path) -> list[str]:
    """Reserve recursive figure discovery for the explicit recovery module."""

    path = Path(path)
    if path.name == "legacy_recovery.py":
        return []
    tree = _parse_python(path)
    if _tree_recursively_discovers_files(tree):
        return [f"{path.name}: recursive figure discovery is reserved for legacy_recovery.py"]
    return []


def scan_figure_lifecycle_sources(root: Path) -> list[str]:
    """Apply figure ownership boundaries to all currently migrated sources."""

    root = Path(root)
    failures: list[str] = []
    core_dir = root / "polynexus" / "core"
    for wrapper_name in _MIGRATED_FIGURE_WRAPPERS:
        wrapper = core_dir / wrapper_name
        if not wrapper.is_file():
            continue
        failures.extend(scan_migrated_figure_wrapper(wrapper))
        failures.extend(scan_recursive_figure_discovery(wrapper))

    for provider in sorted(core_dir.glob("*_engine/figure_provider.py")):
        failures.extend(scan_migrated_figure_provider(provider))
        failures.extend(scan_recursive_figure_discovery(provider))

    figures_dir = core_dir / "figures"
    excluded = {"export_service.py"}
    for path in sorted(figures_dir.glob("*.py")):
        tree = _parse_python(path)
        if path.name not in excluded and _tree_calls_savefig(tree):
            failures.append(f"{path.name}: only the shared export service may call savefig")
        if path.name not in {"profiles.py", "legacy_recovery.py"} and (
            _tree_contains_publication_extension(tree)
        ):
            failures.append(f"{path.name}: only global profiles may choose output formats")
        failures.extend(scan_recursive_figure_discovery(path))

    gui_dir = root / "polynexus" / "gui"
    gallery_mixin = gui_dir / "main_window_figure_mixin.py"
    if gallery_mixin.is_file():
        failures.extend(scan_normal_gallery_discovery(gallery_mixin))
    for relative_path in (
        Path("main_window_figure_mixin.py"),
        Path("plot_gallery_service.py"),
        Path("legacy_figure_recovery_service.py"),
        Path("widgets/chart_viewer.py"),
    ):
        gallery_path = gui_dir / relative_path
        if gallery_path.is_file():
            failures.extend(scan_recursive_figure_discovery(gallery_path))

    editor_service = gui_dir / "figure_window_service.py"
    if editor_service.is_file():
        failures.extend(scan_manifest_editor_capability_boundary(editor_service))
    return failures


def scan_normal_gallery_discovery(path: Path) -> list[str]:
    """Reject recursive filesystem discovery from the normal gallery surface."""

    path = Path(path)
    tree = _parse_python(path)
    if _tree_recursively_discovers_files(tree):
        return [f"{path.name}: normal gallery must not recurse through figure directories"]
    return []


def scan_manifest_editor_capability_boundary(path: Path) -> list[str]:
    """Require manifest editor requests to trust the shared capability report."""

    path = Path(path)
    tree = _parse_python(path)
    function = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "resolve_chart_editor_entry"
        ),
        None,
    )
    manifest_branch = None
    if function is not None:
        for node in ast.walk(function):
            if not isinstance(node, ast.If):
                continue
            test_names = {item.id for item in ast.walk(node.test) if isinstance(item, ast.Name)}
            if {"manifest_document_path", "capability_report"} <= test_names:
                manifest_branch = node
                break

    forbidden_names = {
        "document",
        "document_mode",
        "document_figure_id",
        "entry_state",
        "entry_figure_id",
        "resolve_figure_capabilities",
        "_document_requires_static_fallback",
    }
    branch_names = (
        {
            node.id
            for statement in manifest_branch.body
            for node in ast.walk(statement)
            if isinstance(node, ast.Name)
        }
        if manifest_branch is not None
        else forbidden_names
    )
    has_return = bool(
        manifest_branch
        and any(
            isinstance(node, ast.Return)
            for statement in manifest_branch.body
            for node in ast.walk(statement)
        )
    )
    if manifest_branch is None or forbidden_names & branch_names or not has_return:
        return [f"{path.name}: manifest entries must trust the shared capability report"]
    return []


def _tree_calls_savefig(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "savefig":
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "savefig":
            return True
    return False


def _tree_imports_or_calls_legacy_writer(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(_is_legacy_writer_name(alias.name) for alias in node.names):
                return True
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if _is_legacy_writer_name(name):
            return True
    return False


def _is_legacy_writer_name(name: str) -> bool:
    return name in _LEGACY_FIGURE_WRITERS or name.startswith("fig_")


def _tree_uses_technique_output_selector(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _TECHNIQUE_OUTPUT_SELECTORS:
            return True
        if isinstance(node, ast.Attribute) and node.attr in _TECHNIQUE_OUTPUT_SELECTORS:
            return True
    return False


def _tree_recursively_discovers_files(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in {"rglob", "walk"}:
            return True
        if (
            name == "glob"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and "**" in node.args[0].value
        ):
            return True
    return False


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _tree_contains_publication_extension(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _PUBLICATION_EXTENSION.search(node.value)
        for node in ast.walk(tree)
    )


def default_commands(include_all_tests: bool = False) -> list[GateCommand]:
    commands = [
        GateCommand(
            "compile", ["python", "-m", "compileall", "scripts", "polynexus", "tests", "-q"]
        ),
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
                "tests/test_config.py",
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
    parser.add_argument(
        "--root", default=".", help="Repository root. Defaults to current directory."
    )
    parser.add_argument(
        "--all-tests", action="store_true", help="Include full pytest -q after focused tests."
    )
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
