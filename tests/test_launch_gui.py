from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "launch_gui.py"


def load_launcher():
    spec = importlib.util.spec_from_file_location("polynexus_launch_gui", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_worktree_root_uses_launcher_location():
    launcher = load_launcher()

    assert launcher.resolve_worktree_root(launcher_path=SCRIPT) == ROOT


def test_prepare_environment_places_root_before_existing_pythonpath(tmp_path):
    launcher = load_launcher()
    outside = tmp_path / "older-worktree"
    base_env = {**os.environ, "PYTHONPATH": str(outside)}

    prepared = launcher.prepare_environment(ROOT, base_env)
    entries = prepared["PYTHONPATH"].split(os.pathsep)

    assert entries[0] == str(ROOT)
    assert entries.count(str(ROOT)) == 1
    assert prepared["POLYNEXUS_SOURCE_ROOT"] == str(ROOT)


def test_validate_package_path_rejects_package_outside_root(tmp_path):
    launcher = load_launcher()
    outside_package = tmp_path / "polynexus" / "__init__.py"
    outside_package.parent.mkdir()
    outside_package.write_text("", encoding="utf-8")

    with pytest.raises(launcher.LaunchError, match="outside resolved worktree"):
        launcher.validate_package_path(ROOT, outside_package)


def test_collect_launch_info_reports_real_source_and_git_metadata():
    launcher = load_launcher()
    info = launcher.collect_launch_info(
        ROOT,
        interpreter=Path(sys.executable),
        base_env={**os.environ, "PYTHONPATH": str(ROOT / "older-worktree")},
    )

    assert info.root == ROOT
    assert info.package_path == ROOT / "polynexus" / "__init__.py"
    assert info.branch
    assert info.commit


def test_diagnose_command_prints_source_identity():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--diagnose"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert f"source_root={ROOT}" in completed.stdout
    assert f"package={ROOT / 'polynexus' / '__init__.py'}" in completed.stdout
    assert "branch=" in completed.stdout
    assert "commit=" in completed.stdout


def test_build_gui_command_keeps_gui_entrypoint_and_extra_arguments():
    launcher = load_launcher()

    command = launcher.build_gui_command(Path(sys.executable), ["--startup-probe"])

    assert command == [
        str(Path(sys.executable)),
        "-m",
        "polynexus",
        "--gui",
        "--startup-probe",
    ]
