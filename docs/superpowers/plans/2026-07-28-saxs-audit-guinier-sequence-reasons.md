# SAXS Acceptance Audit Guinier Sequence Reasons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Include existing Guinier sequence levels and reasons in the detached SAXS acceptance audit.

**Architecture:** Extend the existing recursive audit traversal with one
sequence-evidence reader. Reuse existing quality normalization, reason
deduplication, and JSON detachment helpers; do not introduce a second Guinier
contract.

**Tech Stack:** Python mappings, NumPy-backed SAXS payloads, Pytest, strict JSON,
Ruff, and the repository verifier.

---

### Task 1: Establish the RED contract

**Files:**
- Create: `tests/test_saxs_audit_guinier_sequence_reasons.py`
- Modify: none

- [x] **Step 1: Write the failing tests**

Add a pure mapping test with an existing `guinier_sequence_evidence` payload and
an optional real PA6 test. Assert the audit contains:

```python
assert audit["evidence_levels"]["guinier_sequence_evidence"] == ["Unusable"]
assert "guinier_sequence_no_valid_frames" in audit["reason_codes"]
```

Also assert strict JSON and unchanged source parameters.

- [x] **Step 2: Run RED**

```powershell
python -m pytest -q tests/test_saxs_audit_guinier_sequence_reasons.py -vv --basetemp C:\Temp\PolyNexus_saxs_audit_guinier_red
```

Expected: the new level key/reason assertions fail because the current audit
builder does not inspect `guinier_sequence_evidence`.

### Task 2: Extend the existing audit traversal minimally

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py` in
  `build_saxs_scientific_acceptance_audit()`
- Test: `tests/test_saxs_audit_guinier_sequence_reasons.py`

- [x] **Step 1: Add the minimal sequence reader**

Inside the existing `_audit_mapping_tree(source)` loop, after the existing
report readers, add:

```python
sequence = node.get("guinier_sequence_evidence")
if isinstance(sequence, Mapping):
    level = _quality_level(sequence.get("level"))
    if sequence.get("level") is not None:
        levels = evidence_levels.setdefault("guinier_sequence_evidence", [])
        append_unique(levels, level.value)
    for reason in sequence.get("reason_codes", ()) or ():
        append_unique(existing_reasons, reason)
```

Do not alter the existing status rules or input mapping.

- [x] **Step 2: Run focused GREEN**

Run the RED command again; expect pure and real PA6 tests to pass.

### Task 3: Verify and checkpoint

**Files:**
- Modify: this task card, acceptance record, and `active-work.md`

- [x] **Step 1: Run the exact SAXS matrix**

Use the external-basetemp matrix in the task card and record its exact summary
and warnings.

- [x] **Step 2: Run verifier and diff check**

Record task/memory, Ruff, compile, type baseline, quality, preprocessing, and
whitespace results exactly.

- [x] **Step 3: Create the checkpoint**

Use `scripts/auto_commit.py` with exactly the task-card allowlist. Do not stage
parallel files, real data, generated output, or scratch.
