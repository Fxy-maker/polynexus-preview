from pathlib import Path
import json
import subprocess
import sys

from scripts.maintenance_audit import ScratchRule
from scripts.maintenance_cleanup import CleanupCandidate, apply_cleanup, build_cleanup_plan


def test_build_cleanup_plan_excludes_tracked_paths(tmp_path):
    (tmp_path / ".pytest_tmp_keep").mkdir()
    (tmp_path / ".pytest_tmp_remove").mkdir()

    plan = build_cleanup_plan(
        tmp_path,
        rules=[ScratchRule(".pytest_tmp*", "pytest temp directory")],
        tracked_paths=[Path(".pytest_tmp_keep")],
    )

    assert [candidate.path.name for candidate in plan.removable] == [".pytest_tmp_remove"]
    assert [(candidate.path.name, candidate.reason) for candidate in plan.skipped] == [
        (".pytest_tmp_keep", "tracked by git")
    ]


def test_build_cleanup_plan_excludes_directory_with_tracked_child(tmp_path):
    tracked_dir = tmp_path / ".pytest_tmp_keep"
    tracked_dir.mkdir()
    (tracked_dir / "tracked.txt").write_text("keep", encoding="utf-8")

    plan = build_cleanup_plan(
        tmp_path,
        rules=[ScratchRule(".pytest_tmp*", "pytest temp directory")],
        tracked_paths=[Path(".pytest_tmp_keep/tracked.txt")],
    )

    assert plan.removable == []
    assert [(candidate.path.name, candidate.reason) for candidate in plan.skipped] == [
        (".pytest_tmp_keep", "tracked by git")
    ]


def test_build_cleanup_plan_excludes_protected_paths(tmp_path):
    protected = tmp_path / "docs" / "baselines"
    protected.mkdir(parents=True)
    (protected / ".pytest_tmp_inside").mkdir()

    plan = build_cleanup_plan(
        tmp_path,
        rules=[ScratchRule("docs/baselines/.pytest_tmp*", "pytest temp directory")],
        protected_prefixes=["docs/baselines/"],
    )

    assert plan.removable == []
    assert [(candidate.path.relative_to(tmp_path).as_posix(), candidate.reason) for candidate in plan.skipped] == [
        ("docs/baselines/.pytest_tmp_inside", "protected path")
    ]


def test_apply_cleanup_dry_run_does_not_delete(tmp_path):
    scratch = tmp_path / ".pytest_tmp_remove"
    scratch.mkdir()

    removed = apply_cleanup([CleanupCandidate(scratch, "pytest temp directory")], apply=False)

    assert removed == []
    assert scratch.exists()


def test_apply_cleanup_requires_apply_to_delete(tmp_path):
    scratch = tmp_path / ".pytest_tmp_remove"
    scratch.mkdir()

    removed = apply_cleanup([CleanupCandidate(scratch, "pytest temp directory")], apply=True)

    assert removed == [scratch]
    assert not scratch.exists()


def test_cleanup_script_runs_directly(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "maintenance_cleanup.py"
    (tmp_path / ".pytest_tmp_remove").mkdir()

    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--max-items", "2"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0
    assert "Mode: dry-run" in completed.stdout
    assert "Removable scratch artifacts: 1 found" in completed.stdout


def test_cleanup_script_can_emit_json(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "maintenance_cleanup.py"
    (tmp_path / ".pytest_tmp_remove").mkdir()

    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["removable"][0]["path"].endswith(".pytest_tmp_remove")
