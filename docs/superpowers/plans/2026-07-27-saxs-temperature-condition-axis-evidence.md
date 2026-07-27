# SAXS Temperature Condition-Axis Evidence Implementation Plan

> **For agentic workers:** Use TDD. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attach deterministic temperature-axis diagnostics to existing SAXS per-metric series evidence.

**Architecture:** Add an optional frozen `condition_axis` mapping to
`MetricEvidenceSummary`. The existing builder performs only finite conversion
and position bookkeeping; `analyze_temperature_series()` supplies its existing
sorted temperature array and source-index order. No metric calculation or
level policy is changed.

**Tech Stack:** Python dataclasses, NumPy finite checks, pytest, existing SAXS verifier.

---

### Task 1: Write condition-axis RED tests

**Files:**
- Modify: `tests/test_saxs_series_metric_evidence.py`
- Modify: `tests/test_saxs_temperature_guinier_evidence.py`

- [x] **Step 1: Add complete-axis assertions**

Call `build_series_metric_evidence()` with three metric frames and
`condition_name="temperature_C", condition_values=[170.0, 180.0, 190.0]`.
Assert the nested block has the same values, `status == "ordered"`, and no
invalid/duplicate/non-monotonic positions.

- [x] **Step 2: Add defect and mismatch assertions**

Use `[170.0, 170.0, 160.0, float("nan")]` and assert duplicate positions
`[0, 1]`, non-monotonic position `[2]`, invalid position `[3]`, `status` is
`diagnostic`, and the existing metric level/counts are unchanged. Use a
short condition list to assert empty values plus the stable mismatch reason.
Round-trip the result through `MetricEvidenceSummary.from_dict()` and
`json.dumps(..., allow_nan=False)`.

- [x] **Step 3: Add temperature propagation assertion**

Extend the existing sorted temperature test with:

```python
axis = result.metric_evidence["guinier"]["condition_axis"]
assert axis["condition_name"] == "temperature_C"
assert axis["condition_values"] == [170.0, 180.0]
assert axis["status"] == "ordered"
```

- [x] **Step 4: Run RED**

Run:

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_temperature_guinier_evidence.py -q
```

Expected: new assertions fail because the builder has no condition-axis
argument/block and temperature does not pass condition values.

### Task 2: Implement the frozen condition-axis contract

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Freeze and restore the nested mapping**

Add `condition_axis: Mapping[str, Any] = field(default_factory=dict)` to
`MetricEvidenceSummary`, freeze it in `__post_init__`, and normalize mapping
input in `from_dict()`. Do not alter existing positional fields.

- [x] **Step 2: Add builder arguments and deterministic conversion**

Extend the builder with `condition_name: str = ""` and
`condition_values: Iterable[Any] | None = None`. For matching input length,
convert finite numeric values to floats and invalid values to `None`; detect
duplicates and non-monotonic adjacent positions using the existing Guinier
axis convention. For a mismatch, return no partial values and add the stable
reason code.

- [x] **Step 3: Preserve existing level policy**

Attach the block to each requested metric summary, but leave all existing
counts, `level`, `applicable`, frame evidence, and source mapping unchanged.
Use `status="empty"` for a zero-frame supplied axis, `ordered` for a clean
axis, and `diagnostic` for any defect.

### Task 3: Connect the existing temperature axis

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Test: `tests/test_saxs_temperature_guinier_evidence.py`

- [x] **Step 1: Pass existing values only**

Pass `condition_name="temperature_C"` and
`condition_values=result.temperatures` to the existing
`build_series_metric_evidence()` call. Do not sort, filter, or reconstruct the
array at this boundary.

- [x] **Step 2: Run GREEN focused tests**

Run the two focused test files and confirm the existing source-index, frame,
and sequence assertions remain green.

### Task 4: Verify and checkpoint

**Files:**
- Modify: this plan, task card, and durable memory after verification.

- [x] **Step 1: Run the consumer and full SAXS matrices**

Run the condition/temperature tests, existing mode/Workbench/Export matrix,
and the isolated full SAXS file matrix. Record exact counts and warnings.

- [x] **Step 2: Run structured verification and diff checks**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-condition-axis-evidence.md --changed --types
git diff --check
```

Do not claim a structured pass if shared-worktree Ruff or Windows temp
permissions stop it; record the exact limitation and run scoped equivalents.

- [x] **Step 3: Create one explicit-allowlist checkpoint**

Use `scripts/auto_commit.py` with exactly the task-card allowlist. Do not
include the parallel auto-orientation task or generated temporary outputs.

## Plan self-review

- This task adds only source-axis diagnostics and leaves metric levels and
  scientific calculations unchanged.
- Invalid axis values are represented positionally as `null`, never dropped
  or shifted.
- All code changes have a focused RED/GREEN test path.
