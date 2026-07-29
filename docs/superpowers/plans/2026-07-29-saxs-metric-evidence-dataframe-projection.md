# SAXS metric-evidence DataFrame projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose existing Porod/Kratky/invariant/lamellar frame evidence as stable temperature and strain DataFrame columns.

**Architecture:** Add one defensive formatter beside the existing SAXS quality contracts. Temperature and strain reuse it at their existing DataFrame row boundaries; no analysis result or nested evidence is mutated.

**Tech Stack:** Python, NumPy, pandas, pytest, existing SAXS quality contracts, and repository verification scripts.

---

### Task 1: Add RED DataFrame regressions

**Files:**
- Create: `tests/test_saxs_metric_evidence_dataframe.py`

- [x] **Step 1: Write temperature projection regression**

Create a `TempSeriesResult` with one `TemperaturePointResult` containing a
diagnostic Porod payload (`level`, `coverage_fraction`, and one reason code), a
complete Kratky payload, and no invariant/lamellar payload. Assert the three
Porod/Kratky fields are present and missing fields are empty; keep a deep copy
of the nested payload and assert it is unchanged.

- [x] **Step 2: Write strain projection regression**

Create a `StrainSeriesResult` with one `StrainPointResult` containing an
unusable invariant payload and a complete lamellar payload. Assert both rows'
fields and the existing `Metric_evidence_levels` column remain available.

- [x] **Step 3: Verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_metric_dataframe_red'
python -m pytest -q tests/test_saxs_metric_evidence_dataframe.py -vv
```

Expected result: the new `<Metric>_level` columns are absent because the
projection has not been implemented.

### Task 2: Implement the smallest shared projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Add defensive formatter**

Add `metric_evidence_dataframe_fields(payload)` to the quality-contract module.
For the four fixed method keys, copy only `level`, finite
`coverage_fraction`, and pipe-delimited `reason_codes`; return `None` for a
missing/non-mapping payload or malformed coverage. Export the helper through
the module's existing public export list.

- [x] **Step 2: Attach fields at existing row boundaries**

Import the helper in the temperature and strain modules and call it with each
point's existing `metric_evidence` mapping while constructing the existing
DataFrame row. Keep `Metric_evidence_levels` and all current row calculations.

- [x] **Step 3: Verify GREEN and compatibility**

Run the new file and the existing temperature/strain evidence slices. Expected
result: all new assertions pass and existing row counts remain unchanged.

### Task 3: Verify and checkpoint

**Files:**
- The five implementation/test files above plus this task card, spec, and plan.

- [x] **Step 1:** Run the task-scoped structured verifier and `git diff --check`.
- [x] **Step 2:** Run the PowerShell-expanded `tests/test_saxs_*.py` matrix with an external neutral basetemp; count a pass only with a summary and exit code `0`.
- [x] **Step 3:** Run storage `report` and dry-run `clean` only; never use `--apply` in this task.
- [x] **Step 4:** Mark the task evidence complete and create one `scripts/auto_commit.py` checkpoint using only the explicit allowlist.

## Verification record

- RED: `3 failed` for missing projection fields.
- GREEN: `3 passed`; compatibility slice `23 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`, with
  task/memory, Ruff, compile, type baseline, and whitespace checks passing.
- SAXS matrix: `556 passed, 6 warnings` in `204.02s`, exit code `0`.
- Storage: report/clean dry-run only, `14` artifacts, `6` eligible entries,
  `0` eligible bytes, no apply/removal.
