# SAXS Data-Quality DataFrame and CSV Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing q/I data-quality reports into stable temperature/strain DataFrame rows and static parameter CSV fields.

**Architecture:** A shared flat projection helper reads only a report mapping. Existing export consumers merge its fixed fields after their current row/parameter construction; nested evidence and analysis code remain unchanged.

**Tech Stack:** Python, pandas, dataclasses, pytest, Ruff, repository verifier.

---

### Task 1: Write failing report-projection tests

**Files:**
- Create: `tests/test_saxs_data_quality_dataframe.py`

- [x] **Step 1: Test populated temperature and strain rows.**

Construct real `TemperaturePointResult` and `StrainPointResult` objects with a
report containing ordered reasons/actions, counts, source refs, level, and
boolean flags. Assert all fixed fields and the existing physical columns.

- [x] **Step 2: Test missing report alignment.**

Construct one populated and one report-less point in each series. Assert both
rows remain, source/condition order remains unchanged, and the fixed fields are
missing on the report-less row.

- [x] **Step 3: Test static parameter projection.**

Construct a minimal static result with `data_quality_report`, call
`_result_to_params_dict`, and assert the fixed fields are present without
replacing the existing `final_parameters` values.

- [x] **Step 4: Run RED.**

```powershell
python -m pytest -q tests/test_saxs_data_quality_dataframe.py tests/test_saxs_output_helpers.py tests/test_saxs_mode_evidence_propagation.py --basetemp C:\Temp\PolyNexus_saxs_data_quality_red
```

Expected: the new flat-field assertions fail while existing helper and mode
evidence tests continue to pass.

### Task 2: Implement the shared flat projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_output_helpers.py`

- [x] **Step 1: Add `_data_quality_csv_fields`.**

Return a fixed dictionary initialized with `None`; return it unchanged for
non-mapping input. Copy the four references, level, flags, and numeric count
keys directly from the report. Convert only `level.value` and join list/tuple
reason/action values in their original order.

```python
def _data_quality_csv_fields(report: Any) -> dict[str, Any]:
    fields = {key: None for key in _DATA_QUALITY_CSV_KEYS}
    if not isinstance(report, Mapping):
        return fields
    for output_key, report_key in _DATA_QUALITY_SCALAR_FIELDS:
        value = report.get(report_key)
        fields[output_key] = getattr(value, "value", value)
    for output_key, report_key in _DATA_QUALITY_LIST_FIELDS:
        value = report.get(report_key)
        if isinstance(value, str):
            fields[output_key] = value
        elif isinstance(value, (list, tuple)):
            fields[output_key] = "|".join(str(item) for item in value)
    return fields
```

Use module-level tuples for the fixed key mapping so field names cannot drift
between consumers. Do not normalize counts or infer a level from them.

- [x] **Step 2: Merge static fields.**

Call `_data_quality_csv_fields(getattr(result, "data_quality_report", None))`
in both return branches of `_result_to_params_dict()` after existing parameter
construction, beside the detector provenance projection.

### Task 3: Merge fields into series DataFrames

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Import the private helper beside the detector helper.**

- [x] **Step 2: Update each existing row with the point's report.**

After the current row dictionary is constructed, call
`row.update(_data_quality_csv_fields(point.data_quality_report))` and append
the row. Do not access neighboring points or series summaries.

- [x] **Step 3: Run GREEN.**

```powershell
python -m pytest -q tests/test_saxs_data_quality_dataframe.py tests/test_saxs_output_helpers.py tests/test_saxs_mode_evidence_propagation.py --basetemp C:\Temp\PolyNexus_saxs_data_quality_green
```

Expected: all new and existing tests pass.

### Task 4: Verify and checkpoint

**Files:** task card, durable memory, and the implementation files above.

- [x] **Step 1: Run the exact focused, SAXS, task verifier, and diff commands**
  from the task card with external basetemps. Record actual counts and warnings;
  do not count incomplete tool output as a pass.
- [x] **Step 2: Confirm only the nine-file allowlist is staged.**
- [x] **Step 3: Run `scripts/auto_commit.py` with message
  `feat(saxs): export data quality provenance` and the explicit allowlist.**

Checkpoint: `b0c63d7` (created with the explicit allowlist; no push).
