# SAXS temperature auxiliary 1D Figure provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add projection counts to existing temperature Avrami and selected Correlation/IDF Figure recipes.

**Architecture:** Count aligned finite pairs beside each existing projection boundary. Attach detached maps to the recipe only when the corresponding source is emitted; do not modify engine arrays or analysis payloads.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts, and repository verification scripts.

---

### Task 1: Add RED regressions

**Files:**
- Modify: `tests/test_saxs_temperature_figure_panels.py`

- [x] **Step 1: Write dirty Avrami and trace tests**

Use the existing `_temperature_engine()` fixture. Make one condition and one
Xc value malformed, and make selected Correlation/IDF x/y arrays contain
malformed tokens. Assert the expected `partial_nonfinite` counts and strict
JSON serialization; verify source filtering remains unchanged.

- [x] **Step 2: Write clean assertions**

Use the fixture's clean data and assert `complete` counts for Avrami,
Correlation, and IDF.

- [x] **Step 3: Verify RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_auxiliary_red'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py -k auxiliary_provenance -vv
```

Expected result: the selected tests fail because the new recipe fields are not
present.

### Task 2: Implement the smallest provenance maps

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`

- [x] **Step 1: Count Avrami aligned pairs**

Count finite condition/Xc pairs from the same frames used by `_build_avrami`
and attach one detached `avrami_projection_quality` mapping when the recipe
is emitted.

- [x] **Step 2: Count selected Correlation/IDF pairs**

Add a local trace counter using the same coercion and aligned-prefix boundary
as `_mapping_curve`; attach entries only for emitted Correlation/IDF sources.

- [x] **Step 3: Verify GREEN and related temperature Figures**

Run the new tests plus the complete temperature Figure panel/provider slice.

### Task 3: Verify and checkpoint

**Files:**
- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_temperature_figure_panels.py`
- this task card, spec, and plan

- [x] **Step 1:** Run task-scoped `verify.py --changed --types` and `git diff --check`.
- [x] **Step 2:** Run the PowerShell-expanded `tests/test_saxs_*.py` matrix with an external neutral basetemp; require a final summary and exit code `0`.
- [x] **Step 3:** Run storage report and dry-run clean only; never use `--apply`.
- [x] **Step 4:** Mark evidence complete and create one explicit-allowlist `auto_commit.py` checkpoint.

## Verification record

- RED: `2 failed, 6 deselected` for missing provenance fields.
- GREEN: `2 passed, 6 deselected`; related slice `17 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`, with
  task/memory, Ruff, compile, type baseline, and whitespace checks passing.
- SAXS matrix: `558 passed, 6 warnings` in `241.26s`, exit code `0`.
- Storage: report/clean dry-run only, `14` artifacts, `6` eligible entries,
  `0` eligible bytes, no apply/removal.
