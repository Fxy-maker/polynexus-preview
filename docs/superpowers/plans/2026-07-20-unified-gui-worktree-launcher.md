# Unified GUI Worktree Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the desktop GUI always imports PolyNexus from the canonical `D:\PolyNexus` worktree and visibly rejects stale or mismatched source resolution.

**Architecture:** A small repository-local Python launcher derives or receives an explicit worktree root, prepares a root-first `PYTHONPATH`, probes the imported package in a child interpreter, and only then starts `python -m polynexus --gui`. The desktop shortcut invokes this launcher with the bundled interpreter and canonical working directory; other worktrees remain explicit and are never guessed automatically.

**Tech Stack:** Python standard library, pytest, PowerShell Windows shortcut automation, existing `scripts/verify.py` workflow.

---

### Task 1: Add launcher contract tests first

**Files:**
- Create: `D:\PolyNexus\tests\test_launch_gui.py`
- Reference: `D:\PolyNexus\scripts\launch_gui.py` (created in Task 2)

- [ ] **Step 1: Write the failing tests**

Create a test module that loads the script with `importlib.util.spec_from_file_location` so tests do not require `scripts` to become a package. Cover the public behavior with this shape:

```python
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
```

- [ ] **Step 2: Run the focused tests and confirm the expected RED state**

Run:

```bash
pytest tests/test_launch_gui.py -q
```

Expected result before implementation: collection fails because
`D:\PolyNexus\scripts\launch_gui.py` does not exist. If the failure is caused by a test typo instead, fix the test before continuing.

### Task 2: Implement the root-first launcher

**Files:**
- Create: `D:\PolyNexus\scripts\launch_gui.py`

- [ ] **Step 1: Add the launcher data model and root validation**

Implement the standard-library-only module with these exact contracts:

```python
from dataclasses import dataclass
from pathlib import Path


class LaunchError(RuntimeError):
    """Raised when the GUI launch boundary cannot be verified."""


@dataclass(frozen=True)
class LaunchInfo:
    root: Path
    interpreter: Path
    package_path: Path
    branch: str
    commit: str


def resolve_worktree_root(
    *, launcher_path: Path | None = None, requested_root: str | None = None
) -> Path:
    """Resolve an explicit worktree or the repository containing this script."""
    candidate = (
        Path(requested_root).expanduser()
        if requested_root
        else (launcher_path or Path(__file__)).resolve().parent.parent
    ).resolve()
    if not (candidate / "pyproject.toml").is_file():
        raise LaunchError(f"missing pyproject.toml under resolved worktree: {candidate}")
    if not (candidate / "polynexus" / "__init__.py").is_file():
        raise LaunchError(f"missing polynexus package under resolved worktree: {candidate}")
    return candidate


def validate_package_path(root: Path, package_path: Path) -> Path:
    """Reject an import that resolves outside the selected worktree."""
    resolved_root = root.resolve()
    resolved_package = package_path.resolve()
    package_root = resolved_root / "polynexus"
    try:
        resolved_package.relative_to(package_root)
    except ValueError as exc:
        raise LaunchError(
            "imported polynexus package is outside resolved worktree: "
            f"{resolved_package} (root: {resolved_root})"
        ) from exc
    return resolved_package
```

- [ ] **Step 2: Add environment preparation and subprocess probes**

Preserve the caller environment, normalize duplicate `PYTHONPATH` entries, put the selected root first, and set `POLYNEXUS_SOURCE_ROOT`. Probe the package in a fresh child process using the same interpreter that will run the GUI:

```python
import os
import subprocess
import sys


def prepare_environment(root: Path, base_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    existing = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
    ordered = [str(root), *[entry for entry in existing if Path(entry).resolve() != root]]
    env["PYTHONPATH"] = os.pathsep.join(ordered)
    env["POLYNEXUS_SOURCE_ROOT"] = str(root)
    return env


def _run_text(command: list[str], *, root: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LaunchError(f"command failed ({completed.returncode}): {detail}")
    return completed.stdout.strip()


def _git_value(root: Path, *arguments: str) -> str:
    value = _run_text(["git", "-C", str(root), *arguments], root=root, env=prepare_environment(root))
    return value or "detached"


def collect_launch_info(
    root: Path,
    *,
    interpreter: Path | None = None,
    base_env: dict[str, str] | None = None,
) -> LaunchInfo:
    selected_interpreter = (interpreter or Path(sys.executable)).resolve()
    if not selected_interpreter.is_file():
        raise LaunchError(f"GUI interpreter does not exist: {selected_interpreter}")
    env = prepare_environment(root, base_env)
    probe = _run_text(
        [
            str(selected_interpreter),
            "-c",
            "from pathlib import Path; import polynexus; "
            "print(Path(polynexus.__file__).resolve())",
        ],
        root=root,
        env=env,
    )
    package_path = validate_package_path(root, Path(probe.splitlines()[-1]))
    return LaunchInfo(
        root=root,
        interpreter=selected_interpreter,
        package_path=package_path,
        branch=_git_value(root, "branch", "--show-current"),
        commit=_git_value(root, "rev-parse", "--short", "HEAD"),
    )
```

- [ ] **Step 3: Add diagnostics, command construction, and safe startup**

Format one `key=value` record per line so the command is easy to inspect and script:

```python
import argparse


def format_diagnostics(info: LaunchInfo) -> str:
    return "\n".join(
        [
            f"source_root={info.root}",
            f"python={info.interpreter}",
            f"branch={info.branch}",
            f"commit={info.commit}",
            f"package={info.package_path}",
        ]
    )


def build_gui_command(interpreter: Path, extra_args: list[str] | None = None) -> list[str]:
    return [str(interpreter), "-m", "polynexus", "--gui", *(extra_args or [])]


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch PolyNexus GUI from one verified worktree")
    parser.add_argument("--diagnose", action="store_true", help="print source identity and exit")
    parser.add_argument("--worktree", help="explicit worktree root; defaults to this script's repository")
    parser.add_argument("gui_args", nargs=argparse.REMAINDER)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        root = resolve_worktree_root(requested_root=args.worktree)
        info = collect_launch_info(root)
        if args.diagnose:
            print(format_diagnostics(info))
            return 0
        extra_args = list(args.gui_args)
        if extra_args[:1] == ["--"]:
            extra_args.pop(0)
        return subprocess.run(
            build_gui_command(info.interpreter, extra_args),
            cwd=root,
            env=prepare_environment(root),
            check=False,
        ).returncode
    except LaunchError as exc:
        message = f"PolyNexus GUI launch failed: {exc}"
        print(message, file=sys.stderr)
        if sys.platform == "win32" and Path(sys.executable).stem.lower() == "pythonw":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(None, message, "PolyNexus", 0x10)
            except Exception:
                pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

The implementation must not import `PySide6`, `polynexus.gui`, or any analysis module. It must preserve the bundled interpreter selected by the desktop shortcut and must not search for the “most recently modified” worktree.

- [ ] **Step 4: Run the focused tests and confirm GREEN**

Run:

```bash
pytest tests/test_launch_gui.py -q
```

Expected result: all launcher tests pass with no Qt startup. If a test fails, correct the launcher behavior while keeping the test assertion as the contract.

### Task 3: Document and record the launch boundary

**Files:**
- Modify: `D:\PolyNexus\README.md`
- Modify: `D:\PolyNexus\docs\agent\memory\current-state.md`
- Modify: `D:\PolyNexus\docs\agent\memory\active-work.md`

- [ ] **Step 1: Add the user-facing workflow to README**

Add a “Development GUI and worktrees” section after the normal GUI launch instructions. It must state that `D:\PolyNexus` is the desktop GUI runtime, that a branch switch requires closing and reopening the GUI, and provide these commands:

```powershell
Set-Location D:\PolyNexus
git switch -c codex/gui-launch-validation
& .\Python\pythoncore-3.14-64\python.exe .\scripts\launch_gui.py --diagnose
```

Explain that isolated worktrees are not selected automatically; a worktree can be inspected explicitly with its own `scripts\launch_gui.py --worktree <path> --diagnose` invocation.

- [ ] **Step 2: Update durable memory**

In `current-state.md`, add the verified launcher boundary, canonical root, and the fact that editable installations are intentionally bypassed for the desktop GUI. In `active-work.md`, add a dated completed entry linking the task card and listing the focused and repository verification commands.

### Task 4: Update the local shortcut and verify the complete boundary

**Files:**
- Machine-local: `C:\Users\Fan Xuyi\Desktop\PolyNexus.lnk`

- [ ] **Step 1: Configure the shortcut without changing repository files**

Use PowerShell COM automation to set:

```powershell
$shortcut.TargetPath = 'D:\PolyNexus\Python\pythoncore-3.14-64\pythonw.exe'
$shortcut.Arguments = '"D:\PolyNexus\scripts\launch_gui.py"'
$shortcut.WorkingDirectory = 'D:\PolyNexus'
$shortcut.IconLocation = 'D:\PolyNexus\Python\pythoncore-3.14-64\pythonw.exe,0'
$shortcut.Save()
```

The command must not close or restart an existing GUI process. After saving, read the shortcut back and assert the four values exactly.

- [ ] **Step 2: Run the launcher with both interpreters**

Run:

```bash
python scripts/launch_gui.py --diagnose
Python\pythoncore-3.14-64\python.exe scripts/launch_gui.py --diagnose
```

Both outputs must identify `D:\PolyNexus\polynexus\__init__.py`, the current branch, and the current commit.

- [ ] **Step 3: Run the task-scoped verifier**

Run:

```bash
python scripts/verify.py --task docs/agent/tasks/2026-07-20-unified-gui-worktree-launcher.md --changed --types
```

Expected result: memory checks, changed-file checks, focused quality gates, and whitespace checks all pass.

- [ ] **Step 4: Create the automatic checkpoint commit**

After the verification command passes, create exactly one implementation checkpoint with the explicit allowlist:

```bash
python scripts/auto_commit.py \
  --message "fix(dev): pin GUI launcher to canonical worktree" \
  --files scripts/launch_gui.py tests/test_launch_gui.py README.md \
  docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

The local shortcut is intentionally excluded because it is machine-local. Do not push or merge as part of this task.

## Self-review checklist

- Root resolution is derived from the launcher or an explicit `--worktree`, never from editable-install metadata.
- The root is placed first in `PYTHONPATH`, and an imported package outside the root aborts launch.
- Diagnostics run without Qt and expose enough identity to explain any stale window.
- The normal GUI command remains `python -m polynexus --gui`.
- The plan does not add automatic worktree guessing, hot reload, or unrelated GUI changes.
