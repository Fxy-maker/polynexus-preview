# SAXS Series Metric Position Evidence Implementation Plan

> **For agentic workers:** Use TDD. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic frame-position and optional source-index provenance to existing SAXS series metric summaries.

**Architecture:** Extend the existing immutable `MetricEvidenceSummary` and its builder. The builder classifies only the supplied metric mappings and never receives q/I arrays or performs analysis. Temperature passes its existing sorted source-index list; other modes keep positional evidence without fabricated source IDs.

**Tech Stack:** Python dataclasses, existing SAXS quality contracts, pytest, repository verifier.

---

### Task 1: Write the failing position-contract tests

**Files:**
- Modify: `tests/test_saxs_series_metric_evidence.py`
- Modify: `tests/test_saxs_temperature_guinier_evidence.py`

- [x] **Step 1: Add position and source-mapping assertions**

Add tests that call the existing builder with four positions and
`frame_source_indices=[7, 2, 5, 9]`. Assert the metric payload reports
`evidence_frame_indices == [0, 2, 3]`, `missing_frame_indices == [1]`,
`diagnostic_frame_indices == [2]`, `unusable_frame_indices == [3]`, and the
same complete source mapping. Add an invalid-level case and assert position
`0` occurs in both `invalid_level_indices` and `unusable_frame_indices`.

Add a source-length mismatch case and assert the source list is empty and
`series_metric_source_index_mismatch` is present. Strictly serialize the
summary and restore it with `MetricEvidenceSummary.from_dict()`.

Add to the existing sorted temperature test:

```python
assert result.metric_evidence["guinier"]["frame_source_indices"] == [1, 0]
```

- [x] **Step 2: Run the focused tests and observe RED**

Run:

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_temperature_guinier_evidence.py -q
```

Expected: the new assertions fail because the summary has no positional
fields and temperature does not pass a source-index mapping.

### Task 2: Extend the immutable summary contract

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Add JSON-safe positional fields**

Add tuple fields to `MetricEvidenceSummary`:

```python
evidence_frame_indices: tuple[int, ...] = ()
missing_frame_indices: tuple[int, ...] = ()
diagnostic_frame_indices: tuple[int, ...] = ()
unusable_frame_indices: tuple[int, ...] = ()
invalid_level_indices: tuple[int, ...] = ()
frame_source_indices: tuple[int, ...] = ()
```

Normalize them with `_int_tuple` in `__post_init__` and in `from_dict()`.
Keep the existing exported contract names unchanged and do not add a new
public analysis interface.

- [x] **Step 2: Run contract tests before builder changes**

Run the new focused file. It should still fail on the missing builder output,
which confirms the test is exercising the intended behavior.

### Task 3: Record positions in the existing builder

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Test: `tests/test_saxs_series_metric_evidence.py`
- Test: `tests/test_saxs_temperature_guinier_evidence.py`

- [x] **Step 1: Add the optional mapping argument**

Extend the builder signature with
`frame_source_indices: Iterable[Any] | None = None`. Convert a supplied list
to integers only when its length equals `len(frames)`; otherwise use an empty
mapping and append `series_metric_source_index_mismatch` to each summary.

- [x] **Step 2: Classify positions without changing existing counts**

During the current metric loop, append the frame position to exactly the
existing evidence/missing/diagnostic/unusable classifications. Invalid levels
remain `Unusable`, retain all existing reason codes, and additionally append
the invalid position. Pass all positional tuples and the valid source mapping
to `MetricEvidenceSummary`.

- [x] **Step 3: Pass temperature source indices**

Change only the existing temperature summary call to pass:

```python
frame_source_indices=[point.source_index for point in result.temp_points]
```

The list is already in the analysis order and is not sorted, filtered, or
repaired by this task.

- [x] **Step 4: Run the GREEN focused matrix**

Run:

```powershell
python -m pytest tests/test_saxs_series_metric_evidence.py tests/test_saxs_temperature_guinier_evidence.py -q
```

Expected: all position and temperature alignment assertions pass.

### Task 4: Verify consumers and create the checkpoint

**Files:**
- Modify: this plan, task card, and durable memory only after verification.

- [x] **Step 1: Run the focused consumer matrix**

Run the position/temperature tests plus existing mode, Workbench, and Export
tests. Confirm strict JSON and existing DataFrame shape remain green.

- [x] **Step 2: Run structured verification and diff checks**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-series-metric-position-evidence.md --changed --types
git diff --check
```

Use an isolated basetemp if the repository's pre-existing temp directories
are locked, and report the exact result rather than treating a timeout as a
pass.

- [x] **Step 3: Create one explicit-allowlist checkpoint**

After all checks pass, run `scripts/auto_commit.py` with exactly the changed
  files listed in the task card. Do not stage or clean unrelated workspace
  files.

## Execution status

- RED: `4 failed, 10 passed` for the new contract and temperature assertions.
- GREEN: focused consumer matrix `38 passed, 2 warnings`.
- Isolated SAXS matrix: `353 passed, 6 warnings`.
- Direct quality/preprocessing equivalents: `282 passed` and `106 passed`.
- Allowlist Ruff, `py_compile`, and `git diff --check` passed.
- Structured `--changed --types` is blocked by pre-existing Ruff findings in
  unrelated modified files; the task does not change or repair those files.
- Allowlist checkpoint created as `bd7c3fd`; no push, merge, or deploy.

## Plan self-review

- The plan changes only evidence representation and temperature source mapping.
- Existing counts, levels, numerical values, and consumer contracts remain
  compatible.
- Every failure class is represented by a deterministic position list.
- No scientific threshold, interpolation, rescue, or publication behavior is
  introduced.
