from pathlib import Path
import subprocess
import sys

from scripts.task_check import validate_task_text
from scripts.verify import changed_python_paths, command_for, type_check_targets


COMPLETE_TASK = """# Agent Task

## Goal

Restore the repository verification tooling.

## Non-goals

- Do not change product behavior.

## Context

- Related modules: scripts

## Acceptance criteria

- [ ] The verifier is available from the documented path.

## Affected boundaries

- [x] Documentation/tooling

## Implementation plan

1. Restore the workflow scripts.
2. Add focused regression tests.

## Verification

```bash
python scripts/verify.py --changed --types
```

## Risks and compatibility

- User-visible risk: none.

## Memory impact

- [x] No durable project memory change.
"""


def test_validate_task_text_accepts_a_complete_task_card():
    assert validate_task_text(COMPLETE_TASK) == []


def test_validate_task_text_reports_missing_acceptance_and_verification():
    errors = validate_task_text(
        """# Agent Task

## Goal

Implement something.

## Acceptance criteria

- [ ]

## Verification

Run tests later.
"""
    )

    assert any("Acceptance criteria" in error for error in errors)
    assert any("scripts/verify.py" in error for error in errors)


def test_changed_python_paths_filters_to_project_python_files():
    assert changed_python_paths(
        [
            "README.md",
            "polynexus/core/engine.py",
            "scripts/task_check.py",
            "tests/test_agent_workflow_tools.py",
            "docs/notes.py",
            "dist/generated.py",
        ]
    ) == [
        "polynexus/core/engine.py",
        "scripts/task_check.py",
        "tests/test_agent_workflow_tools.py",
    ]


def test_command_for_does_not_run_external_executables_through_python():
    assert command_for("ruff.EXE", "check", "scripts/task_check.py") == [
        "ruff.EXE",
        "check",
        "scripts/task_check.py",
    ]
    assert command_for("scripts/task_check.py", "--task", "task.md")[0].endswith(
        "python.exe"
    )


def test_type_check_targets_start_with_the_agent_tooling_baseline():
    assert type_check_targets(["scripts/verify.py", "polynexus/core/engine.py"]) == [
        "scripts/verify.py"
    ]
    assert type_check_targets([], include_all=True) == [
        "scripts/agent_memory.py",
        "scripts/task_check.py",
        "scripts/verify.py",
    ]


def test_verification_assets_are_present():
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts" / "agent_memory.py").is_file()
    assert (root / "scripts" / "task_check.py").is_file()
    assert (root / "scripts" / "verify.py").is_file()
    assert (root / "pyrightconfig.json").is_file()


def test_repository_memory_check_passes():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "agent_memory.py"
    completed = subprocess.run(
        [sys.executable, str(script), "check", "--root", str(root)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
