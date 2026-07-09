from pathlib import Path
import ast
import json
import subprocess
import sys

from scripts.boundary_audit import (
    FileMetric,
    collect_file_metrics,
    count_broad_exceptions,
    count_lines,
    format_boundary_report,
    to_report_dict,
)


def test_count_lines_handles_empty_and_trailing_newline():
    assert count_lines("") == 0
    assert count_lines("one") == 1
    assert count_lines("one\n") == 1
    assert count_lines("one\ntwo\n") == 2


def test_count_broad_exceptions_counts_exception_handlers():
    text = """
try:
    work()
except Exception:
    recover()
except ValueError:
    recover_specific()
except Exception as exc:
    log(exc)
"""

    assert count_broad_exceptions(text) == 2


def test_collect_file_metrics_filters_and_sorts_python_files(tmp_path):
    package_dir = tmp_path / "polynexus"
    package_dir.mkdir()
    (package_dir / "small.py").write_text("one\n", encoding="utf-8")
    (package_dir / "large.py").write_text("one\ntwo\nexcept Exception:\n    pass\n", encoding="utf-8")
    (package_dir / "notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
    cache_dir = package_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "ignored.py").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    metrics = collect_file_metrics(tmp_path, include_dirs=["polynexus"], min_lines=2)

    assert metrics == [FileMetric(Path("polynexus/large.py"), 4, 1)]


def test_format_boundary_report_includes_hotspots():
    report = format_boundary_report(
        [
            FileMetric(Path("polynexus/gui/main_window.py"), 10505, 61),
            FileMetric(Path("polynexus/core/analysis_evidence.py"), 6354, 0),
        ],
        top=1,
        min_lines=1000,
    )

    assert "Large Python files: top 1 above 1000 lines" in report
    assert "- polynexus/gui/main_window.py: 10505 lines, broad exceptions=61" in report
    assert "Broad exception hotspots: top 1" in report


def test_to_report_dict_returns_machine_readable_sections():
    report = to_report_dict(
        [
            FileMetric(Path("polynexus/gui/main_window.py"), 10505, 61),
            FileMetric(Path("polynexus/core/analysis_evidence.py"), 6354, 0),
        ],
        top=1,
        min_lines=1000,
    )

    assert report == {
        "min_lines": 1000,
        "top": 1,
        "large_files": [
            {
                "path": "polynexus/gui/main_window.py",
                "line_count": 10505,
                "broad_exception_count": 61,
            }
        ],
        "broad_exception_hotspots": [
            {
                "path": "polynexus/gui/main_window.py",
                "line_count": 10505,
                "broad_exception_count": 61,
            }
        ],
    }


def test_boundary_audit_script_runs_directly(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "boundary_audit.py"
    package_dir = tmp_path / "polynexus"
    package_dir.mkdir()
    (package_dir / "large.py").write_text("one\ntwo\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--min-lines", "2", "--top", "1"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0
    assert "PolyNexus boundary audit" in completed.stdout
    assert "polynexus/large.py: 2 lines" in completed.stdout


def test_boundary_audit_script_can_emit_json(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "boundary_audit.py"
    package_dir = tmp_path / "polynexus"
    package_dir.mkdir()
    (package_dir / "large.py").write_text("one\ntwo\nexcept Exception:\n    pass\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--min-lines", "2", "--top", "1", "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["large_files"] == [
        {
            "path": "polynexus/large.py",
            "line_count": 4,
            "broad_exception_count": 1,
        }
    ]


def test_main_window_has_no_duplicate_method_definitions():
    source_path = Path(__file__).resolve().parents[1] / "polynexus" / "gui" / "main_window.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
    main_window_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )

    seen = {}
    duplicates = {}
    for node in main_window_class.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name in seen:
            duplicates.setdefault(node.name, [seen[node.name]]).append(node.lineno)
        else:
            seen[node.name] = node.lineno

    assert duplicates == {}


def test_main_window_does_not_keep_pure_service_wrapper_methods():
    source_path = Path(__file__).resolve().parents[1] / "polynexus" / "gui" / "main_window.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8-sig"))
    main_window_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    method_names = {
        node.name
        for node in main_window_class.body
        if isinstance(node, ast.FunctionDef)
    }

    assert not {
        "_export_bundle_dirs",
        "_task_type_label",
        "_format_r2_value",
        "_format_history_timestamp",
        "_extract_result_r2",
        "_history_run_r2",
        "_history_has_available_source",
        "_find_analysis_evidence",
        "_history_record_analysis_evidence",
        "_flatten_params",
    } & method_names
