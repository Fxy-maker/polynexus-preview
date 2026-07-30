# SAXS Scientific Acceptance Physical Gate Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing SAXS metric physical checks and method-gate states into the read-only scientific acceptance audit.

**Architecture:** Extend the existing recursive audit inspection in `saxs_quality_contracts.py`. The builder copies only supplied `physical_checks`, preserves repeated evidence order, and derives audit reasons only from explicit gate values or an applicable metric with an unknown gate. No metric algorithm or consumer changes are needed.

**Tech Stack:** Python dataclasses/mappings, existing strict JSON contract helpers, pytest, repository verifier.

---

### Task 1: Add the failing audit projection contract tests

**Files:**
- Create: `tests/test_saxs_audit_physical_gate_projection.py`

- [x] **Step 1: Write the failing tests**

Add tests that call `build_saxs_scientific_acceptance_audit(True, parameters)` with these payloads:

```python
def test_audit_projects_existing_physical_checks_and_passing_method_gate():
    parameters = {"metric_evidence": {"guinier": {
        "level": "Trend",
        "applicable": True,
        "physical_checks": {
            "qrg_gate": True,
            "method_gate_passed": True,
        },
    }}}
    audit = build_saxs_scientific_acceptance_audit(True, parameters)
    assert audit["physical_gate_evidence"]["metric:guinier"] == [{
        "qrg_gate": True,
        "method_gate_passed": True,
    }]
    assert audit["method_gate_status"]["metric:guinier"] == [True]
    assert "method_gate_failed" not in audit["reason_codes"]


def test_audit_records_failed_gate_without_mutating_metric_payload():
    parameters = {"metric_evidence": {"porod": {
        "level": "Diagnostic",
        "applicable": False,
        "physical_checks": {"method_gate_passed": False, "slope_supported": False},
    }}}
    before = copy.deepcopy(parameters)
    audit = build_saxs_scientific_acceptance_audit(True, parameters)
    assert audit["method_gate_status"]["metric:porod"] == [False]
    assert "method_gate_failed" in audit["reason_codes"]
    assert parameters == before


def test_applicable_metric_without_gate_is_not_treated_as_passed():
    audit = build_saxs_scientific_acceptance_audit(True, {"metric_evidence": {
        "kratky": {"level": "Trend", "applicable": True, "physical_checks": {}}
    }})
    assert audit["method_gate_status"]["metric:kratky"] == [None]
    assert "method_gate_not_assessed" in audit["reason_codes"]
    assert audit["status"] == "review_required"


def test_physical_gate_projection_is_strict_json_safe():
    audit = build_saxs_scientific_acceptance_audit(True, {"metric_evidence": {
        "invariant": {"level": "Trend", "physical_checks": {"finite": True}}
    }})
    json.dumps(audit, allow_nan=False)
```

- [x] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_audit_physical_gate_projection.py -vv --basetemp D:\PolyNexus_saxs_physical_gate_projection_red
```

Expected: collection succeeds and the tests fail with missing
`physical_gate_evidence`/`method_gate_status` keys. No production file is
changed before this RED result.

### Task 2: Implement the smallest audit projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py:2193-2335`

- [x] **Step 1: Add projection accumulators beside existing evidence maps**

Initialize `physical_gate_evidence` and `method_gate_status` as dictionaries
next to `evidence_levels`, `provenance_validity`, and `existing_reasons`.

- [x] **Step 2: Extend `inspect_report()`**

When `physical_checks` is a mapping, append `_jsonable(dict(checks))` under the
current label. If `method_gate_passed` is present, accept only an actual bool,
append it to the status list, and add `method_gate_failed` for `False`. If the
metric mapping has `applicable is True` and no explicit boolean gate, append
`None` and `method_gate_not_assessed`. Do not mutate `report` or `checks`.

- [x] **Step 3: Include the new fields in the returned contract**

Return the two maps as `physical_gate_evidence` and `method_gate_status` next
to `evidence_levels` and `provenance_validity`. Keep the existing `has_evidence`
calculation and status ordering, except that the new explicit gate reasons are
handled by the existing `if reason_codes: status = "diagnostic_only"` branch.

### Task 3: Verify green and compatibility

**Files:**
- Test: `tests/test_saxs_audit_physical_gate_projection.py`
- Existing regression suites: audit lifecycle, audit surfaces, metric evidence,
  real acceptance, static acceptance, temperature acceptance, and strain tests.

- [x] **Step 1: Run focused GREEN**

Run the RED command again with a fresh basetemp. Expected: all new tests pass.

- [x] **Step 2: Run the exact SAXS matrix**

Run:

```powershell
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp D:\PolyNexus_saxs_physical_gate_projection_saxs_matrix
```

Expected: pytest exits zero with a complete summary. Any timeout or no-summary
process is recorded as a limitation, not a pass.

- [x] **Step 3: Run structured verification and diff check**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md --changed --types
git diff --check
```

Record exact counts and warnings in the acceptance note.

### Task 4: Record evidence and create the allowlist checkpoint

**Files:**
- Create: `docs/acceptance/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md`
- Modify only by checkpoint: the task/spec/plan, implementation, and test files
  named in the task card allowlist.

- [x] **Step 1: Write the acceptance record**

Record the RED result, GREEN result, SAXS matrix result, structured verifier
result, `git diff --check`, unchanged scientific boundaries, and any known
limitations. Do not copy raw logs or mention unrelated worktree paths as task
changes.

- [x] **Step 2: Inspect the exact diff and allowlist**

Run `git diff --stat`, `git diff --check`, and `git status --short` and confirm
that only the explicit allowlist is staged by the checkpoint helper.

- [x] **Step 3: Create the checkpoint**

Run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): expose physical gate evidence in audit" --files polynexus/core/saxs_engine/saxs_quality_contracts.py tests/test_saxs_audit_physical_gate_projection.py docs/agent/tasks/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md docs/superpowers/specs/2026-07-30-saxs-scientific-acceptance-physical-gate-projection-design.md docs/superpowers/plans/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md docs/acceptance/2026-07-30-saxs-scientific-acceptance-physical-gate-projection.md
```

Expected: one local commit containing exactly the six allowlisted files. Do not
push, merge, delete data, or run `test_storage.py --apply`.
