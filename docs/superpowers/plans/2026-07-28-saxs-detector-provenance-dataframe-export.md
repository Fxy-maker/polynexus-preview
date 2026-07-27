# SAXS Detector Provenance DataFrame and CSV Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Project existing raw-detector provenance into stable temperature/strain DataFrame rows and static parameter CSV fields.

**Architecture:** A shared flat projection helper reads only a detector report mapping. Existing result-specific DataFrame builders and static parameter export merge its fixed keys without changing the nested report or analysis logic.

**Tech Stack:** Python, pandas, dataclasses, pytest, repository verifier.

---

### Task 1: Add failing DataFrame/CSV contract tests

**Files:**
- Create: `tests/test_saxs_detector_provenance_dataframe.py`

- [x] **Step 1: Test populated temperature and strain rows.**

Construct real `TemperaturePointResult` and `StrainPointResult` objects with a
raw report containing level, reasons, geometry source/field sources/validity,
and mask source/configured/shape/validity. Assert the existing physical columns
remain and all ten flat provenance keys have deterministic values.

- [x] **Step 2: Test missing report behavior.**

Construct a point without a raw report and assert the same provenance columns
exist with `None`/missing cells; assert row count and source index remain
unchanged.

- [x] **Step 3: Test static parameter CSV projection.**

Construct a minimal static result object with `raw_detector_quality_report`,
call `_result_to_params_dict`, and assert the same keys and literal
`not_assessed` values are present.

- [x] **Step 4: Run RED.**

```powershell
python -m pytest -q tests/test_saxs_detector_provenance_dataframe.py tests/test_saxs_output_helpers.py tests/test_saxs_mode_evidence_propagation.py --basetemp C:\Temp\PolyNexus_saxs_detector_dataframe_red
```

Expected: new provenance assertions fail while existing output/helper tests
continue to pass.

### Task 2: Implement shared flat projection

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_output_helpers.py`

- [x] **Step 1: Add `_detector_provenance_csv_fields`.**

Return the fixed ten keys, handle absent/non-mapping input, preserve literal
level/reason/validity values, sort field-source keys, and format only a valid
two-item shape as `heightxwidth`.

- [x] **Step 2: Merge it into static `_result_to_params_dict`.**

Use the result's existing `raw_detector_quality_report` mapping and merge the
flat fields after normal parameter construction. Do not flatten or rewrite the
nested report.

### Task 3: Reuse the helper in series DataFrames

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py`
- Modify: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Add the helper import.**

Import `_detector_provenance_csv_fields` from `saxs_output_helpers` alongside
existing module-level imports without creating a reverse import.

- [x] **Step 2: Merge fields into each existing row.**

After constructing each row, call the helper with the point's raw report and
`row.update(...)`. Preserve existing frame order, source index, missing rows,
and all existing columns.

- [x] **Step 3: Run GREEN.**

Run the focused test command and confirm all new and existing tests pass.

### Task 4: Verify and checkpoint

**Files:**
- Modify: task card and durable memory files.

- [x] **Step 1: Run focused, exact SAXS, task verifier, and diff checks.**

Record actual counts and warnings with isolated basetemps; do not treat an
unfinished full/boundary process as a pass.

- [x] **Step 2: Review explicit allowlist.**

Confirm only listed files changed and no parallel GUI/scratch paths are staged.

- [x] **Step 3: Create the checkpoint.**

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): export detector provenance columns" `
  --files docs/agent/tasks/2026-07-28-saxs-detector-provenance-dataframe-export.md docs/superpowers/specs/2026-07-28-saxs-detector-provenance-dataframe-export-design.md docs/superpowers/plans/2026-07-28-saxs-detector-provenance-dataframe-export.md polynexus/core/saxs_engine/saxs_output_helpers.py polynexus/core/saxs_engine/saxs_temperature.py polynexus/core/saxs_engine/saxs_strain.py tests/test_saxs_detector_provenance_dataframe.py docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```

Checkpoint: `4d09085` (created with the explicit allowlist; no push).
