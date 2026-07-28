# SAXS long-period helper dirty-input guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse the existing deterministic q/I sanitizer at the Bragg,
Lorentz, and correlation helper boundaries without changing their numerical or
physical semantics.

**Architecture:** Keep `sanitize_1d_profile()` as the sole q/I preparation
policy. Each core helper receives detached survivors and then executes its
existing body; only the two helpers that index `q[-1]` gain an empty-profile
return before that index. No GUI or result DTO contract changes.

**Tech Stack:** Python, NumPy, SciPy, pytest, SAXS quality contracts,
repository verifier, and `scripts/auto_commit.py`.

---

### Task 1: Write and run RED tests

**Files:**

- Create: `tests/test_saxs_long_period_dirty_input.py`
- Read: `polynexus/core/saxs_engine/core.py`

- [x] **Step 1: Build one deterministic clean/dirty profile fixture**

Use a positive synthetic profile with at least 40 q points and a peak in the
existing Bragg window. Build a dirty object profile by inserting a string q,
NaN q, negative intensity, and reversing a valid subset. Keep a clean profile
containing exactly the valid observations so the helper outputs can be
compared without adding scientific expectations.

- [x] **Step 2: Add helper contract tests**

Call the public core functions and assert the dirty calls do not raise,
`bragg_long_period()` returns the same finite peak as the clean call,
`lorentz_fit_long_period()` returns a tuple with a numeric diagnostic result,
and `correlation_function()` returns finite q/r arrays where its existing
calculation is applicable. Assert q arrays are sorted and caller-owned arrays
are unchanged.

- [x] **Step 3: Add the empty fail-closed test**

Call all three helpers with `['bad', np.nan, -1]` and `[0, -1, np.nan]`.
Assert Bragg returns NaN values, Lorentz returns `(nan, 0.0, info)`, and
correlation returns empty `r`/`gamma` arrays with no exception.

- [x] **Step 4: Run RED**

```powershell
python -m pytest -q tests/test_saxs_long_period_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_long_period_dirty_red
```

Expected before production changes: dirty Bragg/Lorentz/correlation calls
raise at raw q comparisons, and empty Lorentz/correlation calls can raise at
`q[-1]`.

### Task 2: Implement the minimal guards

**Files:**

- Modify: `polynexus/core/saxs_engine/core.py`
- Test: `tests/test_saxs_long_period_dirty_input.py`

- [x] **Step 1: Sanitize Bragg input**

At the start of `bragg_long_period()`, before constructing `mask`, add:

```python
sanitized = sanitize_1d_profile(q, I)
q = sanitized.q
I = sanitized.intensity
```

Leave all peak selection and scoring unchanged.

- [x] **Step 2: Sanitize Lorentz input and guard empty q**

After computing `q_corr_min`, sanitize q/I. If `q.size == 0`, return the
existing NaN/zero/info contract with configured `q_corr_min` and
`q_corr_max`. For non-empty q, calculate the existing `q_corr_max` and leave
the lmfit/scipy body unchanged.

- [x] **Step 3: Sanitize correlation input and guard empty q**

After resolving q bounds, sanitize q/I. If `q.size == 0`, return the existing
empty correlation payload with `Q_invariant=np.nan` and configured q bounds.
For non-empty q, retain the existing background, extrapolation, transform,
and peak-search body unchanged.

- [x] **Step 4: Run GREEN**

```powershell
python -m pytest -q tests/test_saxs_long_period_dirty_input.py -vv --basetemp=D:\PolyNexus_saxs_long_period_dirty_green
```

Expected: all focused regressions pass.

### Task 3: Verify, document, and checkpoint

**Files:**

- Modify: task card, implementation plan, acceptance note, and active memory.
- Do not modify: current-state or pre-existing diagnostics.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_long_period_dirty_matrix
```

Record the actual summary and warnings; no timeout or historical process is
counted as a pass.

- [x] **Step 2: Run structured verification and diff check**

```powershell
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_long_period_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-long-period-dirty-input-guard.md --changed --types
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
git diff --check
```

- [x] **Step 3: Record acceptance and review the allowlist**

Document RED/GREEN, exact SAXS and verifier evidence, the no-new-threshold
boundary, and pre-existing workspace files left untouched.

- [x] **Step 4: Create the checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): guard long-period helpers dirty input" --files polynexus/core/saxs_engine/core.py tests/test_saxs_long_period_dirty_input.py docs/agent/tasks/2026-07-28-saxs-long-period-dirty-input-guard.md docs/superpowers/specs/2026-07-28-saxs-long-period-dirty-input-guard-design.md docs/superpowers/plans/2026-07-28-saxs-long-period-dirty-input-guard.md docs/acceptance/2026-07-28-saxs-long-period-dirty-input-guard.md docs/agent/memory/active-work.md
```
