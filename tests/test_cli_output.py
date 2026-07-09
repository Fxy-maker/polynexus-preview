from polynexus.cli.output import (
    format_batch_progress_line,
    format_batch_summary_lines,
    format_technique_result_lines,
)


def test_cli_output_formats_technique_result_block():
    lines = format_technique_result_lines("saxs", "out_dir", {"r_squared": 0.98, "source": "cli"})

    assert lines[0] == ""
    assert lines[2] == "SAXS Results:"
    assert "  r_squared: 0.98" in lines
    assert lines[-1] == "Output: out_dir"


def test_cli_output_formats_batch_progress_and_summary():
    progress = format_batch_progress_line({"file": "a.dat", "status": "OK", "elapsed": 1.23})
    assert progress == "  [OK] a.dat  1.23s"

    summary = format_batch_summary_lines(
        [
            {"file": "a.dat", "technique": "saxs", "status": "OK", "r2": 0.98, "elapsed": 1.23},
            {"file": "b.dat", "technique": "saxs", "status": "FAIL: boom", "r2": None, "elapsed": 2.5},
        ]
    )

    assert "File" in summary[1]
    assert any("Completed: 1 succeeded, 1 failed, 2 total." == line for line in summary)
    assert any("  b.dat -> FAIL: boom" == line for line in summary)
