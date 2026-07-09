from scripts.quality_gate import GateCommand, default_commands, run_commands


def test_default_commands_include_fast_checks_only():
    commands = default_commands(include_all_tests=False)

    assert [command.label for command in commands] == [
        "compile",
        "focused-tests",
        "whitespace",
    ]
    assert commands[0].argv == ["python", "-m", "compileall", "scripts", "polynexus", "tests", "-q"]
    assert commands[1].argv == [
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
    ]
    assert commands[2].argv == ["git", "diff", "--check"]


def test_default_commands_can_include_all_tests():
    commands = default_commands(include_all_tests=True)

    assert [command.label for command in commands] == [
        "compile",
        "focused-tests",
        "all-tests",
        "whitespace",
    ]
    assert commands[2].argv == ["pytest", "-q"]


def test_run_commands_stops_on_first_failure():
    calls = []

    def fake_runner(command):
        calls.append(command.label)
        return 1 if command.label == "focused-tests" else 0

    result = run_commands(
        [
            GateCommand("compile", ["python", "-m", "compileall"]),
            GateCommand("focused-tests", ["pytest", "-q"]),
            GateCommand("whitespace", ["git", "diff", "--check"]),
        ],
        runner=fake_runner,
    )

    assert result == 1
    assert calls == ["compile", "focused-tests"]
