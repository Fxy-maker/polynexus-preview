# SAXS temperature 1D Figure projection provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record deterministic q/I projection counts in temperature SAXS Figure recipes.

**Architecture:** Keep `_positive_curve()` and its existing filter unchanged. Add a temperature-local counter beside that filter, return its per-frame mapping from representative-profile and waterfall builders, and attach it to their existing recipes.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts, strict JSON recipes, and repository verification scripts.

---

### Task 1: Add RED regressions

**Files:**
- Modify: `tests/test_saxs_temperature_figure_panels.py`

- [x] **Step 1: Write the dirty temperature regression**

Use `_temperature_engine()`, set frame 0 q/I to
`q=[0.08, np.nan, 0.18, 0.25]` and `I=[8.0, 6.0, np.inf, 1.0]`, build the
temperature definitions, and assert both the evolution and waterfall recipes
contain frame `"0"` with `4` input, `2` retained, `2` non-finite,
`0` non-positive-intensity pairs, and `partial_invalid`. Serialize both
recipes with `json.dumps(..., allow_nan=False)`.

- [x] **Step 2: Write the clean temperature regression**

Use the unmodified `_temperature_engine()` and assert both recipes report
`4/4/0/0` and `complete` for frame `"0"`.

- [x] **Step 3: Run both tests and confirm RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_1d_provenance_red'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py -k temperature_profile -vv
```

Expected result: both tests fail with `KeyError: profile_projection_quality`.

### Task 2: Implement the smallest temperature recipe projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`

- [x] **Step 1: Add the local counter beside `_positive_curve()`**

For each aligned prefix, count finite pairs, retained pairs satisfying the
existing positive-intensity filter, and finite non-positive-intensity pairs.
Use Python `int` values and `complete`/`partial_invalid` status.

- [x] **Step 2: Thread detached mappings through evolution and waterfall**

Return the mapping from `_representative_profile_content()` and attach it under
`recipe["parameters"]["profile_projection_quality"]`; build the same mapping
inside `_build_waterfall()` and attach it to the waterfall recipe. Do not alter
heatmap, metric, sequence, or role logic.

- [x] **Step 3: Run GREEN and temperature regressions**

Run the two new tests plus
`tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py`;
expect all selected tests to pass and strict JSON serialization to succeed.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Modify: `tests/test_saxs_temperature_figure_panels.py`
- Add: this task card, spec, and plan.

- [x] **Step 1:** Run the task-scoped structured verifier and `git diff --check`.
- [x] **Step 2:** Run the fresh PowerShell-expanded SAXS matrix and record its
  final summary/exit code.
- [x] **Step 3:** Run storage report and clean dry-runs only for this task;
  record all `removed=false` results. Separate user-authorized storage
  maintenance is outside this checkpoint.
- [x] **Step 4:** Audit the explicit allowlist and create one
  `scripts/auto_commit.py` checkpoint without parallel files.

## Verification record

- RED: `2 failed, 4 deselected`, expected `KeyError: profile_projection_quality`.
- GREEN: `2 passed, 4 deselected`; temperature panel/provider slice `15 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`, with
  Ruff, compile, type baseline, and whitespace checks passing.
- Fresh SAXS matrix: `549 passed, 6 warnings in 204.99s`, exit code `0`.
- Task-scoped storage report/clean were dry-run only; `removed_count=0`.
  Separate user-authorized maintenance removed 35 D-drive legacy directories
  (`19,128,640,281` bytes), leaving permission-denied zero-byte entries.
