# SAXS Temperature Scientific Acceptance Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach the existing audit-only scientific acceptance summary to SAXS temperature parameters without changing scientific behavior.

**Architecture:** Keep `build_saxs_scientific_acceptance_audit()` as the single
read-only audit contract. Add one payload attachment after the existing
temperature batch assembly and before return; no other branch or computation is
changed.

**Tech Stack:** Python, NumPy, Pytest, SAXS result DTOs, strict JSON contract,
Ruff, and the repository verifier.

---

### Task 1: Define the temperature RED contract

**Files:**
- Create: `tests/test_saxs_temperature_acceptance_audit.py`
- Modify: none

- [x] **Step 1: Write the failing test**

Build a `SAXSEngine` with an existing failed validation state and a
`TempSeriesResult` containing `Unusable` raw evidence and the existing
`guinier_sequence_no_valid_frames` reason. Assert that the returned temperature
parameters contain a diagnostic-only audit, preserve that sequence evidence,
keep `publication_decision_changed=False`, and serialize with
`json.dumps(..., allow_nan=False)`.

- [x] **Step 2: Run the RED test**

Run:

```powershell
python -m pytest -q tests/test_saxs_temperature_acceptance_audit.py -vv --basetemp C:\Temp\PolyNexus_saxs_temperature_acceptance_red
```

Expected result: the test fails with `KeyError: 'scientific_acceptance_audit'`
because the temperature branch does not yet attach the existing audit.

### Task 2: Attach the existing builder at the temperature boundary

**Files:**
- Modify: `polynexus/core/saxs.py` at the temperature `get_parameters()` return
- Test: `tests/test_saxs_temperature_acceptance_audit.py`

- [x] **Step 1: Add the minimal implementation**

Replace only the temperature branch's direct return with a local `payload`,
then assign:

```python
payload["scientific_acceptance_audit"] = build_saxs_scientific_acceptance_audit(
    getattr(getattr(self, "result", None), "validation_passed", None),
    payload,
)
```

Return the payload. Do not alter the existing metric, evidence, source-index,
or publication fields.

- [x] **Step 2: Run the focused GREEN test**

Run the RED command again and expect the synthetic contract test to pass.

- [x] **Step 3: Run the optional real-temperature regression**

When `D:\PolyNexus\测试数据\saxs\pa6变温` exists, run the real test and assert
`validation_passed is False`, audit status `diagnostic_only`, existing Guinier
sequence status/reason unchanged, and strict JSON serialization.

### Task 3: Verify and record the atomic checkpoint

**Files:**
- Modify: this task card, the acceptance record, and
  `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the exact SAXS matrix with external basetemp**

Record its readable pytest summary and warnings; do not count timeout or no
output as a pass.

- [x] **Step 2: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-acceptance-audit.md --changed --types
```

Record quality/preprocessing, Ruff, compile, type baseline, memory/task, and
whitespace results exactly.

- [x] **Step 3: Write acceptance evidence and create the checkpoint**

Record the real result and known scientific limitations, then run
`scripts/auto_commit.py` with exactly the task-card allowlist. Do not stage
parallel `current-state.md`, generated output, or scratch files.
