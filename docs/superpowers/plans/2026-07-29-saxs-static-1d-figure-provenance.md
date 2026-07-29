# SAXS static 1D Figure projection provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record deterministic q/I projection counts in static SAXS Figure recipes.

**Architecture:** Keep `_profile_pairs()` and its existing filters unchanged. Add a small static-only counter beside the existing projection, return its per-frame mapping from `_append_profile_objects()`, and merge it into the existing `_definition()` recipe parameters for sample/comparison Figures.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts, strict JSON recipes, and repository verification scripts.

---

### Task 1: Add RED regressions

**Files:**
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Write the mixed-invalid static regression**

Use `_static_engine()`, replace frame 0 q/I with
`q=[0.1, np.nan, 0.3, 0.4]` and `I=[2.0, 4.0, np.inf, 5.0]`, build the
`saxs.static.comparison` definition, and assert frame `"0"` reports
`input_pair_count=4`, `retained_pair_count=2`, `nonfinite_pair_count=2`,
`nonpositive_pair_count=0`, and `status="partial_invalid"`. Also call
`json.dumps(definition.recipe, allow_nan=False)`.

- [x] **Step 2: Write the clean static regression**

Use finite positive q/I arrays for frame 0 and assert the same recipe mapping
reports `3/3/0/0` and `status="complete"`.

- [x] **Step 3: Run both tests and confirm RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_1d_provenance_red'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py -k static_profile -vv
```

Expected result: both tests fail with `KeyError: profile_projection_quality`
because the current static recipes do not contain this parameter.

### Task 2: Implement the smallest static recipe projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`

- [x] **Step 1: Add the counter beside the existing static filter**

For the aligned prefix, calculate `finite`, then `retained = finite & (q > 0)
& (intensity > 0)`. Emit JSON-native `int` values and set `status` from the
number of discarded pairs. Do not replace `_profile_pairs()` thresholds.

- [x] **Step 2: Thread the detached mapping through static sample/comparison**

Return the mapping from `_append_profile_objects()`, add an optional recipe
parameter mapping to `_definition()`, and attach
`profile_projection_quality` only to the static sample/comparison recipes.

- [x] **Step 3: Run GREEN and static regressions**

Run the two new tests plus
`tests/test_saxs_figure_evidence_binding.py tests/test_saxs_static_publication_gate.py`;
expect all selected tests to pass and strict JSON serialization to succeed.

### Task 3: Verify and checkpoint

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`
- Add: this task card, spec, and plan.

- [x] **Step 1:** Run the task-scoped structured verifier and `git diff --check`.
- [x] **Step 2:** Run the fresh PowerShell-expanded SAXS matrix and record its
  final summary/exit code.
- [x] **Step 3:** Run storage report and clean dry-runs only; record all
  `removed=false` results and never use `--apply`.
- [x] **Step 4:** Audit the explicit allowlist and create one
  `scripts/auto_commit.py` checkpoint without parallel files.

### Verification record

- RED: two expected `KeyError` failures after the selector was corrected.
- GREEN/static matrix: `2 passed` provenance regressions; `24 passed` static
  Figure/publication regressions.
- Structured: quality `287`, preprocessing `106`; fresh SAXS `547 passed, 6
  warnings` in `202.93s`.
- Storage: dry-run only, `350` artifacts, `57` eligible, `9` referenced,
  `284` young, `removed_count=0`.
