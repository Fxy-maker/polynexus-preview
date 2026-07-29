# SAXS strain 1D Figure projection provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record deterministic q/I projection counts in strain 1D Figure recipes.

**Architecture:** Keep `_profile_values()` and its existing filter unchanged. Add a
strain-local counter using the same aligned prefix and predicate, collect maps
only for emitted 1D sources, and attach them to the main and sequence recipes.
The detector-capable and q-strain heatmap paths remain unchanged.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts, strict JSON recipes, and repository verification scripts.

---

### Task 1: Add RED regressions

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the dirty strain recipe regression**

Use `_strain_engine()`, replace frame 0 with q values
`[0.1, 0.0, np.nan, 0.4]` and intensities `[2.0, 3.0, 4.0, -1.0]`, build
strain definitions, and assert both `saxs.strain.evolution.1d` and
`saxs.strain.sequence.1d` expose frame `"0"` with
`4` input, `1` retained, `1` non-finite, `2` non-positive, and
`partial_invalid`. Serialize both recipes with `json.dumps(..., allow_nan=False)`.

- [x] **Step 2: Write the clean strain recipe regression**

Use the unmodified `_strain_engine()` and assert both 1D recipes report
`3/3/0/0` and `complete` for frame `"0"`, with strict JSON serialization.

- [x] **Step 3: Run both tests and confirm RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_strain_1d_provenance_red'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k strain_profile_provenance -vv
```

Expected result: both new tests fail with `KeyError: profile_projection_quality`.

### Task 2: Implement the smallest strain 1D recipe projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Add the local counter beside `_profile_values()`**

Coerce q and intensity through `_coerce_numeric_array()`, truncate to their
aligned prefix, and calculate:

```python
finite = np.isfinite(q) & np.isfinite(values)
retained = finite & (q > 0.0) & (values > 0.0)
finite_count = int(np.count_nonzero(finite))
retained_count = int(np.count_nonzero(retained))
nonfinite_count = int(count - finite_count)
nonpositive_count = int(finite_count - retained_count)
```

Return Python `int` values and `complete`/`partial_invalid`; return `None` only
when the existing coercion boundary cannot produce aligned arrays.

- [x] **Step 2: Attach provenance to the main 1D recipe**

Collect the counter for each frame whose `_profile_source()` is emitted in the
non-detector branch of `_main_definition()`. Pass the detached map to
`_main_recipe()` and add it only when `detector_capable` is false under
`recipe["parameters"]["profile_projection_quality"]`.

- [x] **Step 3: Attach provenance to ordinary and diagnostic 1D sequences**

Collect the same map beside the existing sequence sources and add it only for
the non-detector sequence recipe. Do not change source values, object order,
eligibility, detector fields, or roles.

- [x] **Step 4: Run GREEN and related strain regressions**

Run the two new tests plus:

```powershell
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_strain_evidence_filtering.py
```

Expect the complete command to pass and both recipes to remain strict
JSON-serializable.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Add: this task card, spec, and plan.

- [x] **Step 1:** Run the task-scoped structured verifier and `git diff --check`.
- [x] **Step 2:** Run the fresh PowerShell-expanded SAXS matrix with a neutral
  external basetemp and record its final summary and exit code.
- [x] **Step 3:** Run storage report and clean dry-runs only; record
  `removed=false` and never use `--apply`.
- [x] **Step 4:** Audit the explicit allowlist and create one
  `scripts/auto_commit.py` checkpoint without parallel files.

## Verification record

- RED: `2 failed, 20 deselected`, expected `KeyError: profile_projection_quality`.
- GREEN: `2 passed, 20 deselected`; related strain slice `23 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`, with
  task/memory, Ruff, compile, type baseline, and whitespace checks passing.
- Fresh SAXS matrix: `551 passed, 6 warnings in 192.12s`, exit code `0`.
- Storage report/clean: dry-run only, `301 artifacts`, `29 eligible`, `272
  younger than retention`, `499046` eligible bytes, no apply/removal.
