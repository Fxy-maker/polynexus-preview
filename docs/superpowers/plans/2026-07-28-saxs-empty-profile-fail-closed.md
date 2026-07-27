# SAXS empty-profile fail-closed boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return an auditable Unusable SAXS result for an empty sanitized profile instead of entering methods that require q points.

**Architecture:** Add a single guard at `analyze_single()`'s sanitized-profile boundary. Reuse `build_data_quality_report()` and `build_guinier_evidence()` and return existing numeric DTO defaults; leave all non-empty paths unchanged.

**Tech Stack:** Python, NumPy, dataclasses, Pytest, strict JSON DTOs, Ruff, and the repository verifier.

---

### Task 1: Lock the empty-profile contract with RED

**Files:**
- Create: `tests/test_saxs_empty_profile_fail_closed.py`

- [x] **Step 1: Write the failing regression**

```python
def test_empty_profile_returns_unusable_structured_result():
    result = analyze_single([], [], SAXSConfig())

    assert result.long_period is not None
    assert result.structure is not None
    assert result.data_quality_report["level"] == "Unusable"
    assert result.guinier_evidence["level"] == "Unusable"
```

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_empty_profile_red'
python -m pytest -q tests/test_saxs_empty_profile_fail_closed.py
```

Expected: FAIL with the existing `IndexError` from `lorentz_fit_long_period`.

### Task 2: Add the minimal fail-closed branch

**Files:**
- Modify: `polynexus/core/saxs_engine/core.py`

- [x] **Step 1: Build existing quality/evidence DTOs and return defaults**

Immediately after `sanitized` is assigned and before smoothing:

```python
if sanitized.q.size == 0:
    quality_report = build_data_quality_report(
        original_q,
        original_I,
        source_id=source_id,
        raw_data_ref=raw_data_ref,
        processed_data_ref="saxs_result:I_smooth",
        processing_config_ref="SAXSConfig",
        actions=sanitized.actions,
    )
    condition_context = getattr(cfg, "condition_context", {}) or {}
    applicability = condition_context.get("guinier_applicability", "unknown") if isinstance(condition_context, dict) else "unknown"
    result = SAXSResult(
        q=sanitized.q,
        I=sanitized.intensity,
        I_smooth=sanitized.intensity,
        long_period=LongPeriodResult(),
        structure=StructureParams(),
        metric_evidence={},
    )
    result.data_quality_report = quality_report.to_dict()
    result.guinier_evidence = build_guinier_evidence(
        np.array([], dtype=float),
        np.array([], dtype=float),
        rg_nm=np.nan,
        i0=np.nan,
        quality_report=quality_report,
        applicability=str(applicability or "unknown"),
        source_ref="saxs_engine.guinier_analysis",
    ).to_dict()
    return result
```

Do not add a new threshold or modify any non-empty path.

- [x] **Step 2: Run focused GREEN tests**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_empty_profile_focus'
python -m pytest -q tests/test_saxs_empty_profile_fail_closed.py tests/test_saxs_structure_params_fail_closed.py tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py
```

Expected: all focused tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: task/spec/plan and durable memory after evidence is collected.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_empty_profile_matrix
```

- [x] **Step 2: Run structured verification and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-empty-profile-fail-closed.md --changed --types
git diff --check
```

- [x] **Step 3: Create one explicit allowlist checkpoint**

After fresh verification, run `scripts/auto_commit.py` with exactly the task
card allowlist. Do not include pre-existing scratch, GUI/editor, or release
files.

Evidence: RED `1 failed`; focused GREEN `17 passed`; exact SAXS matrix `413
passed, 6 warnings`; structured verifier quality `283` and preprocessing `106`
passed; `git diff --check` passed. Full/boundary verification was not run for
this scoped task.
