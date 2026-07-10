from pathlib import Path

from scripts.quality_gate import (
    GateCommand,
    default_commands,
    run_commands,
    scan_figure_lifecycle_sources,
    scan_migrated_figure_provider,
)


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


def test_figure_provider_gate_rejects_direct_savefig(tmp_path):
    provider = tmp_path / "figure_provider.py"
    provider.write_text("figure.savefig('figure.pdf')\n", encoding="utf-8")

    failures = scan_migrated_figure_provider(provider)

    assert failures == [
        "figure_provider.py: migrated figure providers must not call savefig"
    ]


def test_figure_provider_gate_rejects_hard_coded_output_extensions(tmp_path):
    provider = tmp_path / "figure_provider.py"
    provider.write_text("path = 'result.svg'\n", encoding="utf-8")

    failures = scan_migrated_figure_provider(provider)

    assert failures == [
        "figure_provider.py: migrated figure providers must not choose output formats"
    ]


def test_real_ir_provider_passes_figure_provider_gate():
    failures = scan_migrated_figure_provider(
        Path("polynexus/core/ir_engine/figure_provider.py")
    )

    assert failures == []


def test_lifecycle_gate_scans_all_migrated_figure_providers(tmp_path):
    ir_provider = tmp_path / "polynexus/core/ir_engine/figure_provider.py"
    saxs_provider = tmp_path / "polynexus/core/saxs_engine/figure_provider.py"
    ir_provider.parent.mkdir(parents=True)
    saxs_provider.parent.mkdir(parents=True)
    ir_provider.write_text("DEFINITION = 1\n", encoding="utf-8")
    saxs_provider.write_text("figure.savefig('bad.pdf')\n", encoding="utf-8")

    failures = scan_figure_lifecycle_sources(tmp_path)

    assert failures == [
        "figure_provider.py: migrated figure providers must not call savefig"
    ]
