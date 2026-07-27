# SAXS deterministic 1D profile sanitization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SAXS 1D methods one deterministic, auditable finite positive q/I analysis profile while preserving raw input and existing scientific gates.

**Architecture:** Add a pure sanitization helper to the existing SAXS quality-contract module. `analyze_single()` invokes it once before all numerical methods and passes its action codes into the existing `DataQualityReport`; no GUI or consumer contract is changed.

**Tech Stack:** Python, NumPy, dataclasses, Pytest, strict JSON DTOs, Ruff, and the repository verifier.

---

### Task 1: Lock the sanitization contract with RED tests

**Files:**
- Create: `tests/test_saxs_dirty_profile_sanitization.py`
- Modify: `tests/test_saxs_quality_contracts.py`

- [x] **Step 1: Write failing tests**

Add tests that import the planned helper and assert:

```python
def test_sanitizer_drops_invalid_pairs_and_stably_sorts_without_mutating_inputs():
    q = np.array([0.03, np.nan, 0.01, 0.02, 0.02])
    intensity = np.array([3.0, 4.0, -1.0, 2.0, 5.0])
    q_before, i_before = q.copy(), intensity.copy()

    sanitized = sanitize_1d_profile(q, intensity)

    assert sanitized.q.tolist() == [0.02, 0.02, 0.03]
    assert sanitized.intensity.tolist() == [2.0, 5.0, 3.0]
    assert sanitized.actions == (
        "invalid_pairs_dropped", "q_sorted", "duplicate_q_retained"
    )
    assert np.array_equal(q, q_before, equal_nan=True)
    assert np.array_equal(intensity, i_before, equal_nan=True)

def test_sanitizer_aligns_length_mismatch_without_padding():
    sanitized = sanitize_1d_profile([0.02, 0.03, 0.04], [1.0, 2.0])
    assert sanitized.q.tolist() == [0.02, 0.03]
    assert sanitized.intensity.tolist() == [1.0, 2.0]
    assert sanitized.actions == ("axis_length_aligned",)
```

Add a regression assertion that `build_data_quality_report(..., actions=...)`
preserves the supplied ordered action tuple in strict JSON.

- [x] **Step 2: Run the focused RED command**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=C:\Temp\PolyNexus_saxs_dirty_profile_red'
python -m pytest -q tests/test_saxs_dirty_profile_sanitization.py tests/test_saxs_quality_contracts.py
```

Expected: collection succeeds and fails because `sanitize_1d_profile` and its
return contract do not yet exist.

### Task 2: Implement the pure sanitizer and quality action transport

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- Modify: `polynexus/core/saxs_engine/core.py`

- [x] **Step 1: Add the minimal frozen return DTO and helper**

Implement `Sanitized1DProfile` with detached NumPy `q` and `intensity` arrays,
`original_point_count`, `aligned_point_count`, `usable_point_count`, and an
ordered tuple of string actions. Convert scalar/non-numeric inputs to empty
arrays, align by the minimum length, filter finite positive pairs, stable-sort
by q, and retain duplicates. Set arrays read-only after construction.

- [x] **Step 2: Extend `build_data_quality_report()` only additively**

Keep its existing defect counts and level rules. Normalize and retain caller
actions as an ordered, de-duplicated tuple; do not make the helper infer new
quality levels.

- [x] **Step 3: Wire `analyze_single()` at the boundary**

Capture the original q/I, call `sanitize_1d_profile()`, use the returned arrays
for every existing calculation, and pass its actions to
`build_data_quality_report(original_q, original_I, actions=...)`. Preserve the
legacy clean-input output shape and do not modify caller-owned arrays.

- [x] **Step 4: Run GREEN tests**

Run the RED command again. Expected: all focused sanitizer/quality tests pass.

### Task 3: Validate consumers and repository boundaries

**Files:**
- Modify: `tests/test_saxs_dirty_profile_sanitization.py`
- Modify: `docs/agent/tasks/2026-07-28-saxs-deterministic-1d-profile-sanitization.md`
- Modify: `docs/agent/memory/current-state.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Add analysis-boundary regression**

Run `analyze_single()` with a dirty synthetic profile and assert its result q/I
are finite and positive, its quality report contains the sanitizer actions,
and the input arrays are unchanged. Assert a too-short sanitized profile stays
`Unusable` and does not acquire quantitative Guinier evidence.

- [x] **Step 2: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=C:\Temp\PolyNexus_saxs_dirty_profile_matrix
```

Expected: zero failures; existing warnings may remain and must be reported.

- [x] **Step 3: Run the task verifier and diff check**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-deterministic-1d-profile-sanitization.md --changed --types
git diff --check
```

- [x] **Step 4: Create the explicit checkpoint**

After the verifier exits successfully, run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): sanitize dirty 1d profiles" --files polynexus/core/saxs_engine/saxs_quality_contracts.py polynexus/core/saxs_engine/core.py tests/test_saxs_quality_contracts.py tests/test_saxs_dirty_profile_sanitization.py docs/agent/tasks/2026-07-28-saxs-deterministic-1d-profile-sanitization.md docs/superpowers/specs/2026-07-28-saxs-deterministic-1d-profile-sanitization-design.md docs/superpowers/plans/2026-07-28-saxs-deterministic-1d-profile-sanitization.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

The command must not stage or include any pre-existing GUI/editor/release
drafts, scratch directories, or unrelated files.
