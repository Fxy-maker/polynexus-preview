# SAXS Series Metric Source-Index Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make non-Guinier SAXS series metric evidence fail closed on invalid frame identity mappings while preserving valid reordered observations.

**Architecture:** Keep all behavior in `saxs_quality_contracts.build_series_metric_evidence()`. Add source-index facts to the existing immutable `MetricEvidenceSummary`; do not introduce a second sequence contract or touch metric algorithms and consumers.

**Tech Stack:** Python 3.14, dataclasses, NumPy numeric coercion, pytest, existing PolyNexus verification scripts.

---

### Task 1: Add source-index contract regression coverage

**Files:**
- Create: `tests/test_saxs_series_metric_source_integrity.py`
- Reference: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Write tests for the desired contract**

Add tests that call the public `build_series_metric_evidence()` function with
two usable `porod` frames and assert:

```python
def test_valid_reordered_mapping_is_recorded_without_downgrade():
    summary = build_series_metric_evidence(
        [{"porod": {"level": "Trend"}}] * 2,
        metric_names=("porod",),
        frame_source_indices=[1, 0],
    )["porod"]
    assert summary["source_index_order_reordered"] is True
    assert summary["duplicate_source_index_indices"] == []
    assert summary["invalid_source_index_indices"] == []
    assert summary["level"] == "Trend"
```

Add separate tests for duplicate `[0, 0]`, invalid `[-1, 1]`, non-integral
`[0, 1.5]`, boolean `[0, True]`, and length mismatch `[0]`. Each must retain
the supplied frame count, return an empty trusted `frame_source_indices`,
include the corresponding reason code, and return `Diagnostic` for usable
frames. Add a JSON round-trip assertion through `MetricEvidenceSummary` and a
test proving omitted `frame_source_indices` stays Trend with no new reason.

- [x] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
python -m pytest -q tests/test_saxs_series_metric_source_integrity.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_source_integrity_red
```

Expected: the new fields are absent or the invalid mappings remain Trend, so
the new assertions fail for the intended contract reason.

### Task 2: Implement the minimal immutable source-index validation

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Test: `tests/test_saxs_series_metric_source_integrity.py`

- [x] **Step 1: Add summary fields and round-trip normalization**

Extend `MetricEvidenceSummary` with:

```python
duplicate_source_index_indices: tuple[int, ...] = ()
invalid_source_index_indices: tuple[int, ...] = ()
source_index_order_reordered: bool = False
```

Normalize the two index fields with `_int_tuple()` and the boolean with
`bool()` in `__post_init__()`. Include the fields in `from_dict()` conversion.

- [x] **Step 2: Validate supplied indices at the existing aggregation boundary**

Normalize the raw iterable without coercing invalid values into trusted
indices. Detect length mismatch from the raw supplied item count. Detect an
invalid item when it is boolean, non-finite, negative, non-integral, or cannot
be converted to a finite integer. Detect duplicate positions only when the
mapping has the expected length and no invalid item. Set
`source_index_order_reordered` only for a complete valid mapping with any
descending adjacent pair.

Add these reasons when applicable:

```text
series_metric_source_index_mismatch
series_metric_source_index_invalid
series_metric_source_index_duplicate
```

When any source mapping defect exists, use an empty `frame_source_indices` in
the trusted summary and cap a usable metric summary at `Diagnostic`. Keep the
existing missing/diagnostic/unusable logic and condition-axis behavior intact.

- [x] **Step 3: Run the focused tests to verify GREEN**

Run:

```powershell
python -m pytest -q tests/test_saxs_series_metric_source_integrity.py tests/test_saxs_series_metric_evidence.py -o addopts= --basetemp=D:\PolyNexus_saxs_series_metric_source_integrity_green
```

Expected: all new and existing series metric tests pass with strict JSON
serialization.

### Task 3: Verify consumers and checkpoint the atomic task

**Files:**
- Modify: `docs/agent/tasks/2026-07-30-saxs-series-metric-source-index-integrity.md`
- Modify: `docs/acceptance/2026-07-30-saxs-series-metric-source-index-integrity.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the task-scoped verification and SAXS matrix**

Run the exact commands recorded in the task card, requiring a final pytest
summary and exit code `0` for the SAXS matrix. Record any full/boundary timeout
or Qt abort as a limitation, never as a pass.

- [x] **Step 2: Run storage inspection without deletion**

Run `python scripts/test_storage.py report --json` and
`python scripts/test_storage.py clean --older-than-hours 24`. Do not run
`test_storage.py --apply` and do not delete or migrate test directories.

- [ ] **Step 3: Inspect the explicit allowlist and create one checkpoint**

Run `git diff --check`, ensure no pre-existing staged file is present, and use
`scripts/auto_commit.py` with only the source, new test, task/spec/plan,
acceptance, and `active-work.md` paths.
