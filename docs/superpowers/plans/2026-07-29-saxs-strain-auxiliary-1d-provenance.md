# SAXS strain auxiliary 1D Figure provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record deterministic projection counts for strain low-q, Correlation, and IDF Figure recipes.

**Architecture:** Keep `_profile_values()` and `_analysis_trace()` output unchanged. Add local counters beside their existing coercion/filter boundaries, collect maps only for emitted sources, and attach the maps to the corresponding recipes.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts, strict JSON recipes, and repository verification scripts.

---

### Task 1: Add RED regressions

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write dirty auxiliary provenance regression**

Use `_strain_engine()`. For frame 0 set q/I to
`q=[0.1, 0.2, 0.3, np.nan]` and `I=[2.0, 4.0, 3.0, 5.0]`, and set both
Correlation and IDF x/y payloads to four aligned values with malformed entries.
Assert `saxs.strain.low-q.diagnostic` reports `4/3/1/0/partial_invalid`, while
the Correlation and IDF recipes report their finite-pair counts with
`partial_nonfinite`. Serialize every recipe with `json.dumps(..., allow_nan=False)`.

- [x] **Step 2: Write clean auxiliary provenance regression**

Use clean four-point q/I and clean three-point Correlation/IDF payloads. Assert
all three recipes report complete counts and strict JSON serialization.

- [x] **Step 3: Run the selected tests and confirm RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\SaxsAuxiliaryProvenanceRed'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k strain_auxiliary_provenance -vv
```

Expected result: the new tests fail with missing `profile_projection_quality`
or `trace_projection_quality` recipe fields.

### Task 2: Implement the smallest auxiliary recipe provenance

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`

- [x] **Step 1: Count low-q profile projection pairs**

Reuse the existing strain profile counter for each frame whose `_low_q_definition`
source is emitted, then attach a detached map under
`recipe["parameters"]["profile_projection_quality"]`.

- [x] **Step 2: Count finite Correlation/IDF trace pairs**

Add a local helper that aligns the coerced x/y arrays, counts finite pairs before
filtering, and returns Python integers with `complete` or `partial_nonfinite`.
Collect its map only after `_analysis_trace()` emits a source, then attach it
under `recipe["parameters"]["trace_projection_quality"]`.

- [x] **Step 3: Run GREEN and related strain regressions**

Run the two new tests plus:

```powershell
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_strain_evidence_filtering.py
```

Expect all selected tests to pass and recipes to remain strict JSON-safe.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Add: this task card, spec, and plan.

- [x] **Step 1:** Run the task-scoped structured verifier and `git diff --check`.
- [x] **Step 2:** Run the fresh PowerShell-expanded SAXS matrix with a neutral
  external basetemp and record its final summary and exit code.
- [x] **Step 3:** Run storage report and clean dry-runs only; record no removal
  and never use `--apply`.
- [x] **Step 4:** Audit the explicit allowlist and create one
  `scripts/auto_commit.py` checkpoint without parallel files.

## Verification record

- RED: `2 failed, 22 deselected`, expected missing provenance fields.
- GREEN: `2 passed, 22 deselected`; related strain slice `25 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`, with
  task/memory, Ruff, compile, type baseline, and whitespace checks passing.
- Fresh SAXS matrix: `553 passed, 6 warnings in 208.60s`, exit code `0`.
- Storage report/clean: dry-run only, `278 artifacts`, `6 eligible`, `272
  younger than retention`, `0` eligible bytes, no apply/removal.
