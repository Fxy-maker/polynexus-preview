# SAXS Scientific Acceptance Audit Lifecycle Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh existing SAXS scientific acceptance audits after final SAXS validation so cached evidence cannot retain a stale validation snapshot.

**Architecture:** Keep the audit builder and all existing analysis contracts
unchanged. Add one conditional nested-payload refresh in the SAXS validation
hook after the existing SAXS contract publisher has finalized validation.

**Tech Stack:** Python, NumPy, Pytest, SAXS `AnalysisResult` contracts, strict
JSON serialization, Ruff, and the repository verifier.

---

### Task 1: Establish the lifecycle RED regression

**Files:**
- Create: `tests/test_saxs_acceptance_audit_lifecycle.py`
- Modify: none

- [x] **Step 1: Write the failing test**

Create a temperature engine, construct its existing temperature parameters
while validation is still true, then add the existing `ERROR` quality flag and
call `_validate_results()`. Assert that the final result is false and the audit
inside `result.parameters` is also false:

```python
engine.result.parameters = engine.get_parameters()
engine.add_quality_flag("temperature/validation", "ERROR")
engine._validate_results()
assert engine.result.validation_passed is False
assert engine.result.parameters["scientific_acceptance_audit"][
    "automated_validation_passed"
] is False
```

- [x] **Step 2: Run RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_acceptance_audit_lifecycle.py -vv --basetemp C:\Temp\PolyNexus_saxs_audit_lifecycle_red
```

Expected: the test fails because the final validation hook currently leaves the
cached audit's `automated_validation_passed` as `True`.

### Task 2: Refresh only the existing audit in the SAXS validation hook

**Files:**
- Modify: `polynexus/core/saxs.py:298-302`
- Test: `tests/test_saxs_acceptance_audit_lifecycle.py`

- [x] **Step 1: Implement the minimal refresh**

After the existing `publish_saxs_result_contract(self)` call in
`SAXSEngine._validate_results()`, add only:

```python
parameters = getattr(self.result, "parameters", None)
if isinstance(parameters, dict) and "scientific_acceptance_audit" in parameters:
    parameters["scientific_acceptance_audit"] = build_saxs_scientific_acceptance_audit(
        getattr(self.result, "validation_passed", None),
        parameters,
    )
```

Return the existing `bool(base_valid and self.result.validation_passed)` value.
Do not call analysis code or alter other keys.

- [x] **Step 2: Run focused GREEN**

Run the RED command again. Expected: synthetic lifecycle and optional real PA6
tests pass, with strict JSON and existing reason codes intact.

### Task 3: Verify and checkpoint

**Files:**
- Modify: this task card, acceptance record, and
  `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the exact SAXS matrix**

Use the external basetemp command from the task card and record the readable
summary and existing warnings.

- [x] **Step 2: Run the structured verifier and diff check**

Run the task-scoped verifier and `git diff --check`; record exact exit status,
quality/preprocessing counts, Ruff, compile, type baseline, memory/task, and
whitespace evidence.

- [x] **Step 3: Create one explicit checkpoint**

Run `scripts/auto_commit.py` with exactly the task card allowlist. Never stage
`current-state.md`, real data, generated output, or scratch.
