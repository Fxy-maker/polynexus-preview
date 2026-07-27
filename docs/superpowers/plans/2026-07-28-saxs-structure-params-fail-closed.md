# SAXS structure-parameter fail-closed guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent an uninitialized IDF artifact flag from aborting limited-q SAXS analysis.

**Architecture:** Preserve the existing `compute_structure_params()` decision tree and artifact heuristic. Add one explicit default initialization before the branch, then lock the public failure mode with a focused regression.

**Tech Stack:** Python, NumPy, Pytest, existing SAXS quality/evidence DTOs, Ruff, and the repository verifier.

---

### Task 1: Reproduce the limited-q failure

**Files:**
- Create: `tests/test_saxs_structure_params_fail_closed.py`

- [x] **Step 1: Write the failing regression**

```python
def test_limited_q_profile_returns_structured_result_instead_of_unbound_local():
    q = np.linspace(0.02, 0.6, 24)
    intensity = 120.0 * np.exp(-(q**2) * 4.0**2 / 3.0)

    result = analyze_single(q, intensity, SAXSConfig())

    assert result.structure is not None
    assert result.data_quality_report is not None
    assert result.guinier_evidence is not None
```

- [x] **Step 2: Run RED and verify the root cause**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_structure_fail_closed_red'
python -m pytest -q tests/test_saxs_structure_params_fail_closed.py
```

Expected: FAIL with `UnboundLocalError` for `idf_is_artifact` from
`compute_structure_params()`.

### Task 2: Apply the minimal root-cause fix

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`

- [x] **Step 1: Initialize the existing artifact flag before branching**

Immediately before the tangent decision, add:

```python
idf_is_artifact = False
```

Do not move or rewrite the existing peak-spacing heuristic.

- [x] **Step 2: Run GREEN and adjacent SAXS quality tests**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_structure_fail_closed_focus'
python -m pytest -q tests/test_saxs_structure_params_fail_closed.py tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py tests/test_saxs_1d_method_evidence.py
```

Expected: all tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task/spec/plan and durable memory after evidence is collected.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_structure_fail_closed_matrix
```

- [x] **Step 2: Run structured verification and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-structure-params-fail-closed.md --changed --types
git diff --check
```

- [x] **Step 3: Create one explicit allowlist checkpoint**

After fresh verification, run `scripts/auto_commit.py` with exactly the task
card allowlist. Leave all pre-existing scratch, GUI/editor, release, and
parallel files untouched.
