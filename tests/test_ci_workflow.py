from pathlib import Path


WORKFLOW_PATH = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def _workflow_text() -> str:
    assert WORKFLOW_PATH.is_file(), f"missing CI workflow: {WORKFLOW_PATH}"
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_windows_ci_targets_main_with_read_only_permissions():
    workflow = _workflow_text()

    assert workflow.startswith("name: PolyNexus CI\n")
    assert (
        "on:\n"
        "  pull_request:\n"
        "    branches: [main]\n"
        "  push:\n"
        "    branches: [main]\n"
    ) in workflow
    assert "permissions:\n  contents: read\n" in workflow
    assert "cancel-in-progress: true" in workflow


def test_windows_ci_uses_the_supported_headless_python_environment():
    workflow = _workflow_text()

    assert "name: CI / windows-quality-gate" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "timeout-minutes: 45" in workflow
    assert "QT_QPA_PLATFORM: offscreen" in workflow
    assert "MPLBACKEND: Agg" in workflow
    assert 'PYTHONUTF8: "1"' in workflow
    assert "uses: actions/checkout@v7" in workflow
    assert "uses: actions/setup-python@v6" in workflow
    assert 'python-version: "3.11"' in workflow
    assert "cache: pip" in workflow
    assert "cache-dependency-path: pyproject.toml" in workflow


def test_windows_ci_installs_declared_dev_dependencies_and_runs_the_full_gate():
    workflow = _workflow_text()

    assert "python -m pip install --upgrade pip" in workflow
    assert 'python -m pip install -e ".[dev]"' in workflow
    assert "python scripts/quality_gate.py --all-tests" in workflow
    assert "continue-on-error" not in workflow
    assert "secrets." not in workflow
