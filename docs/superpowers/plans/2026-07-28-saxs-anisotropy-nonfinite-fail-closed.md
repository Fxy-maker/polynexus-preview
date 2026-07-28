# SAXS anisotropy non-finite input fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make non-finite SAXS anisotropy inputs fail closed with explicit, JSON-safe unusable evidence.

**Architecture:** Extend the existing normalization guard in `saxs_anisotropy.py` to validate finiteness after numeric conversion. On failure, reuse the existing empty result and orientation evidence builder; valid inputs remain on the current analysis path.

**Tech Stack:** Python, NumPy, pytest, existing SAXS quality contracts, repository verification scripts.

---

### Task 1: Add the non-finite anisotropy regression

**Files:**
- Modify: `tests/test_saxs_2d_detector_orientation_evidence.py`

- [x] **Step 1: Write the failing tests**

Add one parameterized test that places a non-finite value in each required
input and asserts the intended public contract:

```python
@pytest.mark.parametrize("input_index", range(5))
@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_anisotropy_nonfinite_required_input_fails_closed(input_index, bad_value):
    payload = list(_synthetic_azimuthal_input(37.0))
    payload[input_index] = np.array(payload[input_index], copy=True)
    payload[input_index].flat[0] = bad_value

    result = analyze_anisotropy(*payload)

    assert result.confidence == 0.0
    assert not np.isfinite(result.f_herman)
    assert result.orientation_evidence["level"] == QualityLevel.UNUSABLE.value
    assert "orientation_input_nonfinite" in result.orientation_evidence["reason_codes"]
    json.dumps(result.detector_quality_report, allow_nan=False)
    json.dumps(result.orientation_evidence, allow_nan=False)
```

Import `pytest` with the existing test imports.

- [x] **Step 2: Run the regression to verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_anisotropy_nonfinite_red'
python -m pytest -q tests/test_saxs_2d_detector_orientation_evidence.py -k nonfinite
```

Expected before implementation: the test fails because non-finite inputs are
accepted by normalization and the valid synthetic path does not emit
`orientation_input_nonfinite` or `Unusable` evidence.

### Task 2: Implement the minimal finite-input guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`

- [x] **Step 1: Add the guard after existing shape checks**

In `_normalize_anisotropy_inputs()`, after the existing dimensionality,
emptiness, and length checks and before returning normalized inputs, add:

```python
    if any(not np.all(np.isfinite(array)) for array in (
        image, q_axis, chi_axis, q_1d_axis, intensity_1d
    )):
        return None, "orientation_input_nonfinite"
```

Do not alter the existing `analyze_anisotropy()` invalid-result path or the
evidence builder.

- [x] **Step 2: Run the focused regression to verify GREEN**

Run the same command from Task 1. Expected: all 15 parameterized cases pass.

- [x] **Step 3: Run the existing 2D suite**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_anisotropy_nonfinite_focus'
python -m pytest -q tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_strain_sector_fail_closed.py tests/test_saxs_strain_axis_fail_closed.py tests/test_saxs_batch_parameters.py
```

Expected: pytest exits `0`; report the exact count and warnings.

### Task 3: Verify, record, and checkpoint the atomic change

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_anisotropy.py`
- Modify: `tests/test_saxs_2d_detector_orientation_evidence.py`
- Add: `docs/agent/tasks/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md`
- Add: `docs/superpowers/specs/2026-07-28-saxs-anisotropy-nonfinite-fail-closed-design.md`
- Add: `docs/superpowers/plans/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run the structured verifier and repository hygiene checks**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The storage report is a dry run and must not delete or move any data. Record
the verifier gates, diff result, and artifact counts in the task card.

- [x] **Step 2: Run the exact SAXS matrix with an external basetemp**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_anisotropy_nonfinite_saxs_matrix'
python -m pytest -q tests/test_saxs_*.py
```

Record a fresh pytest summary if the command completes. If the bounded tool
execution times out or produces no pytest summary, record that limitation and
do not call the matrix passed.

- [x] **Step 3: Update durable active-work memory**

Add a concise dated entry to `docs/agent/memory/active-work.md` containing the
task link, the fail-closed semantic boundary, exact fresh verification results,
and any full-matrix limitation. Do not edit `current-state.md`.

- [ ] **Step 4: Create the explicit allowlist checkpoint**

After all checks, run:

```powershell
python scripts/auto_commit.py --message "fix(saxs): fail closed on nonfinite anisotropy inputs" --files polynexus/core/saxs_engine/saxs_anisotropy.py tests/test_saxs_2d_detector_orientation_evidence.py docs/agent/tasks/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-anisotropy-nonfinite-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-anisotropy-nonfinite-fail-closed.md docs/agent/memory/active-work.md
```

Expected: one local commit containing only the listed changed files; do not
stage or commit the pre-existing `current-state.md`, scratch directories, or
parallel task files.
