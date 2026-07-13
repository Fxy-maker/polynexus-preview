import importlib
from pathlib import Path

import pytest

import scripts.quality_gate as quality_gate
from scripts.quality_gate import (
    GateCommand,
    default_commands,
    run_commands,
    scan_figure_lifecycle_sources,
    scan_migrated_figure_provider,
    scan_migrated_figure_wrapper,
    scan_recursive_figure_discovery,
)


def test_default_commands_include_fast_checks_only():
    commands = default_commands(include_all_tests=False)

    assert [command.label for command in commands] == [
        "compile",
        "focused-tests",
        "preprocess_optimization",
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
    ]
    assert commands[2].argv[-1] == "-q"
    assert commands[3].argv == ["git", "diff", "--check"]


def test_default_commands_can_include_all_tests():
    commands = default_commands(include_all_tests=True)

    assert [command.label for command in commands] == [
        "compile",
        "focused-tests",
        "preprocess_optimization",
        "all-tests",
        "whitespace",
    ]
    assert commands[3].argv == ["pytest", "-q"]


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

    assert failures == ["figure_provider.py: migrated figure providers must not call savefig"]


def test_figure_provider_gate_rejects_hard_coded_output_extensions(tmp_path):
    provider = tmp_path / "figure_provider.py"
    provider.write_text("path = 'result.svg'\n", encoding="utf-8")

    failures = scan_migrated_figure_provider(provider)

    assert failures == [
        "figure_provider.py: migrated figure providers must not choose output formats"
    ]


def test_real_ir_provider_passes_figure_provider_gate():
    failures = scan_migrated_figure_provider(Path("polynexus/core/ir_engine/figure_provider.py"))

    assert failures == []


def test_lifecycle_gate_scans_all_migrated_figure_providers(tmp_path):
    ir_provider = tmp_path / "polynexus/core/ir_engine/figure_provider.py"
    saxs_provider = tmp_path / "polynexus/core/saxs_engine/figure_provider.py"
    ir_provider.parent.mkdir(parents=True)
    saxs_provider.parent.mkdir(parents=True)
    ir_provider.write_text("DEFINITION = 1\n", encoding="utf-8")
    saxs_provider.write_text("figure.savefig('bad.pdf')\n", encoding="utf-8")

    failures = scan_figure_lifecycle_sources(tmp_path)

    assert failures == ["figure_provider.py: migrated figure providers must not call savefig"]


def test_lifecycle_gate_allows_legacy_recovery_to_recognize_existing_formats(
    tmp_path,
):
    recovery = tmp_path / "polynexus/core/figures/legacy_recovery.py"
    recovery.parent.mkdir(parents=True)
    recovery.write_text(
        "LEGACY_EXTENSIONS = {'.svg', '.png', '.pdf'}\n",
        encoding="utf-8",
    )

    assert scan_figure_lifecycle_sources(tmp_path) == []


def test_normal_gallery_gate_rejects_recursive_file_discovery(tmp_path):
    mixin = tmp_path / "main_window_figure_mixin.py"
    mixin.write_text(
        "def populate(root):\n    return list(root.rglob('*.png'))\n",
        encoding="utf-8",
    )

    failures = quality_gate.scan_normal_gallery_discovery(mixin)

    assert failures == [
        "main_window_figure_mixin.py: normal gallery must not recurse through figure directories"
    ]


def test_manifest_editor_gate_rejects_local_capability_recomputation(tmp_path):
    service = tmp_path / "figure_window_service.py"
    service.write_text(
        """
def resolve_chart_editor_entry(entry):
    manifest_document_path = entry.document_path
    capability_report = entry.capability_report
    if manifest_document_path and capability_report is not None:
        document = load_figure_document(manifest_document_path)
        if _document_requires_static_fallback(document):
            return True
        return False
""".strip(),
        encoding="utf-8",
    )

    failures = quality_gate.scan_manifest_editor_capability_boundary(service)

    assert failures == [
        "figure_window_service.py: manifest entries must trust the shared capability report"
    ]


def test_real_gallery_and_editor_pass_manifest_boundaries():
    assert (
        quality_gate.scan_normal_gallery_discovery(
            Path("polynexus/gui/main_window_figure_mixin.py")
        )
        == []
    )
    assert (
        quality_gate.scan_manifest_editor_capability_boundary(
            Path("polynexus/gui/figure_window_service.py")
        )
        == []
    )


def test_migrated_wrapper_gate_rejects_legacy_writer_imports_and_calls(
    tmp_path,
):
    wrapper = tmp_path / "saxs.py"
    wrapper.write_text(
        "from .saxs_engine import generate_all_figures\n"
        "def plot(results):\n"
        "    return generate_all_figures(results, 'output')\n",
        encoding="utf-8",
    )

    assert scan_migrated_figure_wrapper(wrapper) == [
        "saxs.py: migrated wrappers must not import or call legacy figure writers"
    ]


def test_migrated_wrapper_gate_rejects_direct_savefig(tmp_path):
    wrapper = tmp_path / "saxs.py"
    wrapper.write_text("figure.savefig(path)\n", encoding="utf-8")

    assert scan_migrated_figure_wrapper(wrapper) == [
        "saxs.py: migrated wrappers must not call savefig"
    ]


def test_migrated_wrapper_gate_rejects_hard_coded_output_extensions(tmp_path):
    wrapper = tmp_path / "saxs.py"
    wrapper.write_text("path = 'result.pdf'\n", encoding="utf-8")

    assert scan_migrated_figure_wrapper(wrapper) == [
        "saxs.py: migrated wrappers/providers must not choose output formats"
    ]


@pytest.mark.parametrize(
    "source",
    (
        "value = config.figure_format\n",
        "value = config.fig_format\n",
        "value = config.figure_dpi\n",
        "value = config.fig_dpi\n",
        "value = profile.publication_png_dpi\n",
    ),
)
def test_migrated_wrapper_gate_rejects_technique_output_selection(
    tmp_path,
    source,
):
    wrapper = tmp_path / "ir.py"
    wrapper.write_text(source, encoding="utf-8")

    assert scan_migrated_figure_wrapper(wrapper) == [
        "ir.py: migrated wrappers/providers must not choose figure formats or publication DPI"
    ]


def test_figure_provider_gate_rejects_technique_output_selection(tmp_path):
    provider = tmp_path / "figure_provider.py"
    provider.write_text("value = config.fig_dpi\n", encoding="utf-8")

    assert scan_migrated_figure_provider(provider) == [
        "figure_provider.py: migrated wrappers/providers must not choose "
        "figure formats or publication DPI"
    ]


@pytest.mark.parametrize(
    "source",
    (
        "paths = root.rglob('*.png')\n",
        "paths = root.glob('**/*.svg')\n",
        "paths = os.walk(root)\n",
    ),
)
def test_recursive_figure_discovery_gate_reserves_recursion_for_recovery(
    tmp_path,
    source,
):
    source_file = tmp_path / "gallery.py"
    source_file.write_text(source, encoding="utf-8")

    assert scan_recursive_figure_discovery(source_file) == [
        "gallery.py: recursive figure discovery is reserved for legacy_recovery.py"
    ]


def test_recursive_figure_discovery_gate_parses_utf8_bom(tmp_path):
    source_file = tmp_path / "gallery.py"
    source_file.write_text(
        "paths = root.rglob('*.png')\n",
        encoding="utf-8-sig",
    )

    assert scan_recursive_figure_discovery(source_file) == [
        "gallery.py: recursive figure discovery is reserved for legacy_recovery.py"
    ]


@pytest.mark.parametrize(
    ("module_name", "forbidden_names"),
    (
        (
            "polynexus.core.saxs_engine",
            ("generate_all_figures", "fig_u1_scattering_profile"),
        ),
        (
            "polynexus.core.waxs_engine",
            (
                "generate_all_figures",
                "generate_temperature_figures",
                "generate_strain_figures",
                "fig_w1_profile",
            ),
        ),
        (
            "polynexus.core.dsc_engine",
            ("generate_all_figures", "fig_d1_full_curve"),
        ),
        (
            "polynexus.core.ir_engine",
            (
                "generate_all_figures",
                "generate_temperature_2d_figures",
                "fig_ir1_spectrum",
            ),
        ),
        (
            "polynexus.core.nmr_engine",
            ("generate_all_figures", "fig_nmr1_spectrum"),
        ),
    ),
)
def test_engine_packages_do_not_export_legacy_figure_writers(
    module_name,
    forbidden_names,
):
    module = importlib.import_module(module_name)

    assert not (set(forbidden_names) & set(vars(module)))


def test_real_figure_lifecycle_sources_pass_all_boundaries():
    assert scan_figure_lifecycle_sources(Path(".")) == []
