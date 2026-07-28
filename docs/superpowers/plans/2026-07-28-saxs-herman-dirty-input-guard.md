# SAXS Herman dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `herman_orientation_factor()` fail closed on malformed sector
profiles without changing its numerical or physical semantics.

**Architecture:** Keep preparation at the core helper boundary. Reuse the
existing elementwise coercion utility, create detached finite angle/intensity
pairs, stable-sort only by the supplied/generated angle, then call the current
Herman body. No GUI or evidence DTO contract changes.

**Tech Stack:** Python, NumPy, SciPy, pytest, SAXS quality contracts,
repository verifier, and `scripts/auto_commit.py`.

---

### Task 1: RED regression tests

**Files:**

- Create: `tests/test_saxs_herman_dirty_input.py`
- Read: `polynexus/core/saxs_engine/saxs_strain.py`

- [x] **Step 1: Define clean and dirty angular profiles**

Use a 12-point meridional profile with finite positive intensities, reverse the
dirty pairs, replace one angle with a numeric-invalid string and one intensity
with `NaN`, and derive a clean survivor reference without adding a physical
expectation.

- [x] **Step 2: Add dirty/clean and safety regressions**

Assert the dirty result does not raise and its `f`/`f_sub` match the clean
survivor call. Assert a one-element mismatch remains safe, wholly invalid input
keeps the existing NaN dictionary shape, finite negative intensity is retained
as an input to the unchanged calculation, and caller object arrays are not
mutated.

- [x] **Step 3: Run RED**

```powershell
python -m pytest -q tests/test_saxs_herman_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_herman_dirty_red
```

Expected before production changes: the dirty profile raises at arithmetic on
the malformed intensity; no production code is changed until this failure is
observed.

### Task 2: Minimal core guard

**Files:**

- Modify: `polynexus/core/saxs_engine/saxs_strain.py`
- Test: `tests/test_saxs_herman_dirty_input.py`

- [x] **Step 1: Add a detached sector-pair preparer**

Use the existing elementwise numeric coercion helper, align to the shorter
axis, filter only non-finite pairs, and stable-sort by angle. Generate the
existing default angle grid when the caller omits `chi`; do not filter finite
negative intensities.

- [x] **Step 2: Route meridional and equatorial profiles through it**

Keep the existing `len > 5`, angular-window, trapezoid, and return logic. If
preparation yields too few points, leave the initialized NaN fields unchanged.

- [x] **Step 3: Run focused GREEN**

```powershell
python -m pytest -q tests/test_saxs_herman_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_herman_dirty_green
```

Expected: all focused regressions pass with no exception and no caller-array
mutation.

### Task 3: Verification and checkpoint

**Files:** task/spec/plan, acceptance, active memory, and the two source/test
files in the explicit allowlist.

- [x] **Step 1: Run exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_herman_dirty_matrix
```

- [x] **Step 2: Run task verifier and diff check**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_herman_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-herman-dirty-input-guard.md --changed --types
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

- [x] **Step 3: Record evidence and checkpoint**

Update the task card, acceptance note, plan, and `active-work.md` with exact
summaries and limitations, then run `scripts/auto_commit.py` with only the
explicit seven-path allowlist. Do not include `current-state.md` or scratch.
