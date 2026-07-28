# SAXS Real 2D Scientific Acceptance Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an audit-only, strict JSON-safe summary that exposes existing SAXS 2D scientific and publication boundaries without changing analysis decisions.

**Architecture:** A pure builder in `saxs_quality_contracts.py` scans detached existing evidence mappings and derives only categorical audit status. The SAXS strain parameter boundary attaches the detached payload after existing parameter assembly; no frame or publication contract is rewritten.

**Tech Stack:** Python dataclasses/mappings, NumPy-safe contract serialization, pytest, repository verifier.

---

### Task 1: Define the audit RED contract

**Files:**
- Create: `tests/test_saxs_real_2d_scientific_acceptance.py`
- Modify: none

- [ ] **Step 1: Write failing tests**

Add tests that import `build_saxs_scientific_acceptance_audit` and assert:

```python
def test_diagnostic_existing_evidence_is_not_publication_acceptance():
    parameters = {
        "paper_figure_candidate": False,
        "paper_conclusion_candidate": False,
        "paper_conclusion_ready": False,
        "strain_reliability_status": "diagnostic_only",
        "strain_reliability_reason": "low_q_void_dominant|phase_ambiguous",
        "raw_detector_quality_report": {
            "level": "Unusable",
            "source_kinds": ["raw_detector"],
            "reason_codes": ["nonpositive_pixels"],
        },
        "_batch_data": [{
            "raw_detector_quality_report": {
                "geometry_provenance": {"validity": "not_assessed"},
                "mask_provenance": {"validity": "not_assessed"},
            },
        }],
    }
    audit = build_saxs_scientific_acceptance_audit(True, parameters)
    assert audit["status"] == "diagnostic_only"
    assert audit["automated_validation_passed"] is True
    assert audit["publication_decision_changed"] is False
    assert "existing_publication_gate_not_ready" in audit["reason_codes"]
```

Also cover absent evidence as `not_assessed`, an unblocked payload as
`review_required`, strict `json.dumps(..., allow_nan=False)`, and unchanged
input mappings.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp C:\Temp\PolyNexus_saxs_real_2d_acceptance_red
```

Expected: collection/import failure because the new builder is not yet
available.

### Task 2: Implement the pure audit builder

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/__init__.py`
- Test: `tests/test_saxs_real_2d_scientific_acceptance.py`

- [ ] **Step 1: Add the minimal builder**

Implement `build_saxs_scientific_acceptance_audit(validation_passed, parameters)`
with these deterministic rules:

```python
paper_flags = {
    name: parameters.get(name)
    for name in (
        "paper_figure_candidate",
        "paper_conclusion_candidate",
        "paper_conclusion_ready",
    )
}
if not any(value is not None for value in paper_flags.values()):
    status = "not_assessed"
elif (
    any(value is False for value in paper_flags.values())
    or any(level in {"Diagnostic", "Unusable"} for level in evidence_levels.values())
    or any(value == "not_assessed" for value in provenance_validity.values())
    or str(parameters.get("strain_reliability_status", "")).lower() not in {"", "usable"}
    or validation_passed is False
):
    status = "diagnostic_only"
else:
    status = "review_required"
```

The implementation must recursively inspect only mappings/lists already
supplied in `parameters`, preserve existing reason strings, detach all nested
values through the existing JSON contract helper, and set
`publication_decision_changed=False`.

- [ ] **Step 2: Run focused GREEN**

Run the RED command again. Expected: all focused contract tests pass.

- [ ] **Step 3: Export the public helper**

Add the function to the existing `saxs_engine` import/export list and run Ruff
on the changed module and focused test.

### Task 3: Attach the audit to strain parameters

**Files:**
- Modify: `polynexus/core/saxs.py`
- Test: `tests/test_saxs_real_2d_scientific_acceptance.py`

- [ ] **Step 1: Add the parameter-boundary regression**

Run the real PAD8 strain engine and assert:

```python
assert result.validation_passed is True
audit = result.parameters["scientific_acceptance_audit"]
assert audit["status"] == "diagnostic_only"
assert audit["automated_validation_passed"] is True
assert audit["existing_publication_gate"]["paper_conclusion_ready"] is False
json.dumps(audit, allow_nan=False)
```

- [ ] **Step 2: Attach without changing old fields**

Wrap only the existing strain `get_parameters()` return payload with the audit
builder. Do not alter the calculations that populate `paper_*`, reliability,
detector, orientation, metric, or frame fields.

- [ ] **Step 3: Run focused real GREEN**

Run the focused file with external basetemp. Expected: pure contract tests and
the real PAD8 assertion pass; the run remains diagnostic-only.

### Task 4: Full scoped verification and acceptance record

**Files:**
- Modify: `docs/agent/tasks/2026-07-28-saxs-real-2d-scientific-acceptance.md`
- Create: `docs/acceptance/2026-07-28-saxs-real-2d-scientific-acceptance.md`
- Modify: `docs/agent/memory/active-work.md`

- [ ] **Step 1: Run the exact SAXS matrix**

Run the PowerShell-expanded `tests/test_saxs_*.py` matrix with an external
basetemp and record the exact summary and warnings.

- [ ] **Step 2: Run the structured verifier**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-real-2d-scientific-acceptance.md --changed --types
```

Record the actual quality/preprocessing/Ruff/compile/type/memory/task/
whitespace results. Do not count a timeout or an old full run as a pass.

- [ ] **Step 3: Write the acceptance record**

Record the real PAD8 evidence, the test commands, the fact that no numeric
scientific threshold was added, and the separate human review limitations.

- [ ] **Step 4: Create the explicit checkpoint**

Run `scripts/auto_commit.py` with exactly the allowlist in the task card. Do
not include `current-state.md`, generated output, real data, or scratch.
