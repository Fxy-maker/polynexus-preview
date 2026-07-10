# Windows CI Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add and remotely verify one Windows GitHub Actions quality gate for PR #4 that installs PolyNexus, runs the complete repository quality gate, and preserves the unified figure lifecycle boundary scan.

**Architecture:** A single `windows-latest` job delegates repository policy to `scripts/quality_gate.py --all-tests` instead of duplicating checks in YAML. A small pytest contract locks the workflow's triggers, permissions, environment, runner, dependency installation, timeout, and exact verification command. GitHub's run for the pushed PR head is the authoritative remote validation.

**Tech Stack:** GitHub Actions YAML, Windows Server runner, Python 3.11, pytest, existing PolyNexus quality-gate script, GitHub REST API.

---

### Task 1: Record design approval and define the failing workflow contract

**Files:**
- Modify: `docs/superpowers/specs/2026-07-10-windows-ci-quality-gate-design.md`
- Create: `tests/test_ci_workflow.py`

- [ ] **Step 1: Mark the reviewed design approved**

Change the design status line to:

```markdown
**Status:** Approved for implementation
```

- [ ] **Step 2: Write the workflow contract test before the workflow exists**

Create `tests/test_ci_workflow.py`:

```python
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
    assert "uses: actions/checkout@v4" in workflow
    assert "uses: actions/setup-python@v5" in workflow
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
```

- [ ] **Step 3: Run the new test and verify the expected red state**

Run:

```powershell
pytest tests/test_ci_workflow.py -q
```

Expected: three failures whose first cause is
`missing CI workflow: ...\.github\workflows\ci.yml`.

- [ ] **Step 4: Commit the red contract**

```powershell
git add -- docs/superpowers/specs/2026-07-10-windows-ci-quality-gate-design.md tests/test_ci_workflow.py
git commit -m "test: define Windows CI workflow contract"
```

### Task 2: Add the minimal Windows workflow

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tests/test_ci_workflow.py`

- [ ] **Step 1: Implement the workflow contract**

Create `.github/workflows/ci.yml`:

```yaml
name: PolyNexus CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  windows-quality-gate:
    name: CI / windows-quality-gate
    runs-on: windows-latest
    timeout-minutes: 45
    env:
      QT_QPA_PLATFORM: offscreen
      MPLBACKEND: Agg
      PYTHONUTF8: "1"
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: pyproject.toml

      - name: Install package
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e ".[dev]"

      - name: Run complete quality gate
        shell: pwsh
        run: python scripts/quality_gate.py --all-tests
```

- [ ] **Step 2: Run the contract test and verify green**

Run:

```powershell
pytest tests/test_ci_workflow.py -q
```

Expected: `3 passed`.

- [ ] **Step 3: Run the existing quality-gate unit tests**

Run:

```powershell
pytest tests/test_quality_gate.py tests/test_ci_workflow.py -q
```

Expected: all selected tests pass and the real lifecycle source boundary assertion remains green.

- [ ] **Step 4: Commit the workflow**

```powershell
git add -- .github/workflows/ci.yml
git commit -m "ci: add Windows quality gate"
```

### Task 3: Verify the final local content

**Files:**
- Verify: `.github/workflows/ci.yml`
- Verify: `tests/test_ci_workflow.py`
- Verify: `scripts/quality_gate.py`

- [ ] **Step 1: Run the exact production CI command locally**

Run:

```powershell
python scripts/quality_gate.py --all-tests
```

Expected:

- lifecycle scan produces no failures
- focused tests report at least the established `260 passed` baseline plus the new CI tests when
  selected by the full suite
- complete suite exits 0 with only the explicit external IR/NMR fixture skips
- whitespace check passes

- [ ] **Step 2: Remove only test-generated untracked scratch data**

If `tests/_tmp_phase3/` exists after pytest, resolve it and verify it is exactly under the current
worktree before deleting it. Do not remove any unrelated untracked file.

- [ ] **Step 3: Verify repository state and commit contents**

```powershell
git diff --check
git status --short
git log -3 --oneline
git show --stat --oneline HEAD
```

Expected: no uncommitted files; the latest implementation commit contains only
`.github/workflows/ci.yml`, and the preceding contract commit contains only the approved spec status
and `tests/test_ci_workflow.py`.

### Task 4: Push and verify PR #4 metadata

**Files:**
- Remote branch: `codex/unified-figure-lifecycle-foundation`
- Pull request: `https://github.com/Fxy-maker/polynexus/pull/4`

- [ ] **Step 1: Push without force**

```powershell
git push origin codex/unified-figure-lifecycle-foundation
```

Expected: the remote branch advances to the local CI commit.

- [ ] **Step 2: Read back the pull request**

Use the authenticated GitHub API and verify:

- PR number is 4
- base is `main`
- head is `codex/unified-figure-lifecycle-foundation`
- head SHA equals local `git rev-parse HEAD`
- state is `open`

- [ ] **Step 3: Update the PR body with CI semantics**

Append a short CI section stating that `CI / windows-quality-gate` is the green process gate and
that technical branch-protection enforcement is unavailable for this private repository on the
current plan. Preserve the existing summary and test plan.

### Task 5: Monitor and validate the GitHub Actions run

**Files:**
- GitHub Actions workflow: `PolyNexus CI`
- Required process check: `CI / windows-quality-gate`

- [ ] **Step 1: Find the run for the pushed head SHA**

Query GitHub Actions workflow runs for PR #4 until a run appears with:

- `head_sha` equal to local HEAD
- event `pull_request`
- workflow name `PolyNexus CI`

- [ ] **Step 2: Monitor without modifying the branch**

Poll the run and its jobs at intervals no shorter than 20 seconds. Report meaningful state changes
and wait until the run reaches `completed`.

- [ ] **Step 3: Diagnose and fix any failure using evidence**

If the conclusion is not `success`, download the failed-job logs, identify the first causal error,
write or adjust a local contract/regression test where applicable, make the minimal fix, rerun the
complete local quality gate, commit, push, and monitor the new head SHA. Never weaken the gate or
add `continue-on-error` to obtain green status.

- [ ] **Step 4: Complete the acceptance audit**

Verify every acceptance criterion from the design against current files, local command output,
commit history, PR metadata, and the final GitHub workflow/job result. Record the workflow run URL,
job name, head SHA, conclusion, and branch-protection limitation in the handoff.
