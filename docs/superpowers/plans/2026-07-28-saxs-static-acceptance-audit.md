# SAXS Static Scientific Acceptance Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing scientific acceptance audit for Static SAXS without changing Static publication eligibility.

**Architecture:** Add one private payload attachment helper in `SAXSEngine`.
Use it only immediately before existing Static parameter returns; the audit
builder and validation refresh remain shared contracts.

**Tech Stack:** Python, SAXS result DTOs, NumPy, Pytest, strict JSON, Ruff, and
the repository verifier.

---

### Task 1: Establish Static RED coverage

**Files:**
- Create: `tests/test_saxs_static_acceptance_audit.py`
- Modify: none

- [x] **Step 1: Write the failing tests**

Construct a Static `SAXSResult` with existing Diagnostic metric evidence and an
aligned batch with one missing frame. Assert both `get_parameters()` payloads
contain `scientific_acceptance_audit`, with publication flags `None`, and strict
JSON serialization.

- [x] **Step 2: Run RED**

```powershell
python -m pytest -q tests/test_saxs_static_acceptance_audit.py -vv --basetemp C:\Temp\PolyNexus_saxs_static_audit_red
```

Expected: the tests fail with the missing `scientific_acceptance_audit` key.

### Task 2: Attach the existing audit to Static return paths

**Files:**
- Modify: `polynexus/core/saxs.py` Static `get_parameters()` paths
- Test: `tests/test_saxs_static_acceptance_audit.py`

- [x] **Step 1: Add the minimal helper**

Add:

```python
def _attach_scientific_acceptance_audit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
    payload["scientific_acceptance_audit"] = build_saxs_scientific_acceptance_audit(
        getattr(self.result, "validation_passed", None),
        payload,
    )
    return payload
```

Use it only for Static batch and single/profile returns. Do not synthesize
`paper_*` flags or modify temperature/strain branches.

- [x] **Step 2: Run focused GREEN**

Run the RED command again. Expected: synthetic and optional real Static tests
pass and existing aligned rows remain unchanged.

### Task 3: Verify and checkpoint

**Files:**
- Modify: this task card, acceptance record, and `active-work.md`

- [x] **Step 1: Run exact SAXS matrix**

Record the exact summary and existing warnings using external basetemp.

- [x] **Step 2: Run verifier and diff check**

Record task/memory, Ruff, compile, type baseline, quality, preprocessing, and
whitespace results.

- [x] **Step 3: Create one explicit checkpoint**

Use `scripts/auto_commit.py` with exactly the task-card allowlist.
