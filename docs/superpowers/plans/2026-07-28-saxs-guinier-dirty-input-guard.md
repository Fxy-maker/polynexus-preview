# SAXS Guinier dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the existing deterministic q/I sanitizer at the public SAXS
Guinier helper boundary without changing the Guinier fit or physical gates.

**Architecture:** `polynexus.core.saxs_engine.guinier_analysis` already points
to `saxs_physical_helpers.guinier_analysis`. The helper will consume only the
detached `Sanitized1DProfile` survivors, then run its existing low-q selection
and polynomial fit. The existing result/evidence and consumer contracts stay
unchanged.

**Tech Stack:** Python, NumPy, pytest, SAXS quality contracts, repository
verifier, and `scripts/auto_commit.py`.

---

### Task 1: Add the failing regression tests

**Files:**

- Create: `tests/test_saxs_guinier_dirty_input.py`
- Read: `polynexus/core/saxs_engine/saxs_quality_contracts.py`

- [x] **Step 1: Write a dirty-profile regression**

Use the public export and a clean reference profile. The dirty profile must
contain string, NaN, negative, and unsorted observations, while retaining at
least ten valid q/I pairs. Compare the dirty result with the clean reference:

```python
def test_guinier_discards_dirty_pairs_and_fits_sorted_survivors():
    clean_q = np.arange(0.1, 1.3, 0.1)
    clean_i = 100.0 * np.exp(-(clean_q**2) * 4.0 / 3.0)
    dirty_q = np.array(
        [0.5, "bad-q", 0.1, 0.9, -0.2, 1.2, 0.3, np.nan,
         0.8, 0.4, 0.7, 1.0, 0.2, 0.6, 1.1], dtype=object,
    )
    dirty_i = np.array(
        [clean_i[4], clean_i[0], clean_i[8], clean_i[2], clean_i[3],
         clean_i[11], clean_i[2], clean_i[7], clean_i[7], clean_i[3],
         clean_i[6], clean_i[9], clean_i[1], clean_i[5], clean_i[10]],
        dtype=object,
    )
    rg, i0, q_fit, ln_i = guinier_analysis(dirty_q, dirty_i)
    clean_rg, clean_i0, clean_q_fit, clean_ln_i = guinier_analysis(clean_q, clean_i)
    assert np.isfinite(rg) and np.isfinite(i0)
    assert np.all(np.isfinite(q_fit)) and np.all(q_fit > 0)
    assert np.all(np.diff(q_fit) >= 0)
    np.testing.assert_allclose((rg, i0), (clean_rg, clean_i0))
    np.testing.assert_allclose(q_fit, clean_q_fit)
    np.testing.assert_allclose(ln_i, clean_ln_i)
```

- [x] **Step 2: Add empty and immutability regressions**

The empty/invalid case must retain `(nan, nan, empty, empty)`. A separate test
must copy caller-owned q and intensity arrays, call the helper, and assert both
arrays are unchanged with `np.testing.assert_array_equal`.

- [x] **Step 3: Run RED and confirm the raw NumPy boundary failure**

Run:

```powershell
python -m pytest -q tests/test_saxs_guinier_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_guinier_dirty_red
```

Expected before production changes: the dirty-input test fails or errors at
the raw NumPy operation; no implementation code is written until that failure
is observed.

### Task 2: Apply the minimal sanitizer at the Guinier helper boundary

**Files:**

- Modify: `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- Test: `tests/test_saxs_guinier_dirty_input.py`

- [x] **Step 1: Replace raw q/I use with detached survivors**

At the start of `guinier_analysis`, add only:

```python
sanitized = sanitize_1d_profile(q, I)
q = sanitized.q
I = sanitized.intensity
```

Leave the existing q-minimum filtering, ten-point gate, low-q window,
positive-intensity filter, polynomial fit, and return tuple unchanged.

- [x] **Step 2: Run focused GREEN**

```powershell
python -m pytest -q tests/test_saxs_guinier_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_guinier_dirty_green
```

Expected result: all focused tests pass with no repository-local test output.

### Task 3: Verify the atomic task and record evidence

**Files:**

- Modify: the task card, plan, acceptance note, and
  `docs/agent/memory/active-work.md`.
- Do not modify: `docs/agent/memory/current-state.md` or any pre-existing
  scratch/output directory.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_guinier_dirty_matrix
```

Record the actual pytest summary and exit code. A timeout or missing summary is
a limitation, not a pass.

- [x] **Step 2: Run structured verification and diff check**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_guinier_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-guinier-dirty-input-guard.md --changed --types
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

Record exact quality/preprocessing/Ruff/compile/type/memory/task/whitespace
results without attributing unrelated changed or untracked files.

- [x] **Step 3: Create the acceptance record**

Record RED/GREEN evidence, the exact SAXS matrix, verifier output, and the
unchanged scientific limitations. State explicitly that no new threshold,
rescue, interpolation, publication, or AI behavior was introduced.

- [x] **Step 4: Review the allowlist and checkpoint**

Inspect `git diff --stat`, the allowlisted paths, and `git diff --check`, then
run:

```powershell
python scripts/auto_commit.py --message "fix(saxs): guard guinier helper dirty input" --files polynexus/core/saxs_engine/saxs_physical_helpers.py tests/test_saxs_guinier_dirty_input.py docs/agent/tasks/2026-07-28-saxs-guinier-dirty-input-guard.md docs/superpowers/specs/2026-07-28-saxs-guinier-dirty-input-guard.md docs/superpowers/plans/2026-07-28-saxs-guinier-dirty-input-guard.md docs/acceptance/2026-07-28-saxs-guinier-dirty-input-guard.md docs/agent/memory/active-work.md
```

The checkpoint must not include the pre-existing `current-state.md`, GUI/editor
scratch, `.superpowers/`, real data, or test-output directories.
