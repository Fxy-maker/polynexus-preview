from pathlib import Path
import json
import subprocess
import sys

from scripts.maintenance_audit import (
    ScratchRule,
    find_scratch_paths,
    format_report,
    parse_git_ls_files,
)


def test_find_scratch_paths_matches_expected_patterns(tmp_path):
    (tmp_path / ".pytest_tmp_example").mkdir()
    (tmp_path / ".tmp_pytest_run").mkdir()
    (tmp_path / "test_output").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "polynexus.log").write_text("log", encoding="utf-8")
    (tmp_path / "_debug_case.py").write_text("print('x')\n", encoding="utf-8")
    (tmp_path / "polynexus").mkdir()

    rules = [
        ScratchRule(".pytest_tmp*", "pytest temp directory"),
        ScratchRule(".tmp_pytest*", "pytest temp directory"),
        ScratchRule("test_output", "generated test output"),
        ScratchRule("results", "generated analysis output"),
        ScratchRule("polynexus.log", "runtime log"),
        ScratchRule("_*.py", "root-level diagnostic script"),
    ]

    found = find_scratch_paths(tmp_path, rules)
    names = [path.name for path, _rule in found]

    assert names == [
        ".pytest_tmp_example",
        ".tmp_pytest_run",
        "_debug_case.py",
        "polynexus.log",
        "results",
        "test_output",
    ]


def test_parse_git_ls_files_ignores_empty_lines():
    output = "\n.pytest_tmp_old/file.txt\npolynexus.log\n\n"

    assert parse_git_ls_files(output) == [
        Path(".pytest_tmp_old/file.txt"),
        Path("polynexus.log"),
    ]


def test_format_report_limits_scratch_output_by_default(tmp_path):
    for index in range(3):
        (tmp_path / f".pytest_tmp_{index}").mkdir()

    report = format_report(
        tmp_path,
        rules=[ScratchRule(".pytest_tmp*", "pytest temp directory")],
        max_items=2,
    )

    assert "Scratch artifacts: 3 found" in report
    assert "- .pytest_tmp_0 [dir] - pytest temp directory" in report
    assert "- .pytest_tmp_1 [dir] - pytest temp directory" in report
    assert "- .pytest_tmp_2 [dir] - pytest temp directory" not in report
    assert "- ... 1 more. Re-run with --all to list every artifact." in report


def test_format_report_points_to_quality_gate(tmp_path):
    report = format_report(tmp_path, rules=[])

    assert "- python scripts/quality_gate.py --root ." in report
    assert "- python scripts/quality_gate.py --root . --all-tests" in report


def test_maintenance_audit_script_can_emit_json(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "maintenance_audit.py"
    (tmp_path / ".pytest_tmp_example").mkdir()

    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["scratch_artifacts"][0]["name"] == ".pytest_tmp_example"
