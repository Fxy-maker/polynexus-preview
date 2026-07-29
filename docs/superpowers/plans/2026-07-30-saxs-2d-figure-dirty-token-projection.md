# SAXS 2D Figure Dirty-Token Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover malformed detector and azimuthal Figure tokens elementwise without changing SAXS analysis or publication decisions.

**Architecture:** Reuse the existing detached `_coerce_numeric_array()` helper at the Figure projection boundary. The shared detector provider and strain provider will continue to sample/aligned-prefix exactly as before, then apply their existing finite filters and provenance counters to the projected arrays.

**Tech Stack:** Python, NumPy, pytest, existing SAXS Figure contracts and verifier scripts.

---

### Task 1: Add malformed-token regression tests

**Files:**
- Modify: `tests/test_saxs_detector_figure_modes.py` near the existing static detector projection tests.
- Modify: `tests/test_saxs_figure_evidence_binding.py` near the existing detector/azimuthal provenance tests.

- [x] **Step 1: Write the failing detector test**

Add a static detector test that supplies an object image with one malformed
token and asserts the finite pixels survive with the existing coordinates and
partial provenance:

```python
def test_static_detector_figure_projects_malformed_pixel_elementwise(monkeypatch):
    engine = _static_engine(["static-0.edf"])
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (
            np.asarray([[1.0, "bad-pixel"], [4.0, 16.0]], dtype=object),
            {},
        ),
    )

    definition = next(
        item
        for item in build_static_saxs_figure_definitions(engine)
        if item.figure_id == "saxs.static.detector.2d"
    )
    source = definition.data_sources[0]

    assert source.values["pixel_x"] == (0, 0, 1)
    assert source.values["pixel_y"] == (0, 1, 1)
    assert definition.recipe["parameters"]["detector_projection_quality"]["0"][
        "nonfinite_pixel_count"
    ] == 1
```

- [x] **Step 2: Write the failing strain detector and azimuthal tests**

Add one malformed detector test and one malformed azimuthal test beside the
existing provenance regressions. The detector test uses an object array with
`"bad-pixel"`; the azimuthal test uses `"bad-chi"` and `"bad-intensity"` in
separate aligned positions and expects two non-finite pairs, one retained
pair, and `partial_nonfinite`.

- [x] **Step 3: Run the focused tests to verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_2d_dirty_token_red'
python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_evidence_binding.py -k "malformed or dirty_detector or dirty_azimuthal"
```

Expected: the new tests fail at the whole-array `dtype=float` conversion
boundary; existing tests in the selector remain green.

### Task 2: Implement elementwise Figure projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_detector.py:61-86`.
- Modify: `polynexus/core/saxs_engine/figure_strain.py:692-729`.
- Modify: `polynexus/core/saxs_engine/figure_strain.py:1435-1470`.

- [x] **Step 1: Replace detector whole-array conversion**

In both detector helpers, convert the source to an object-safe shape first and
project it through `_coerce_numeric_array()` without changing the 2D shape:

```python
source = np.asarray(image, dtype=object)
if source.ndim != 2 or source.size == 0:
    return None
array = _coerce_numeric_array(source).reshape(source.shape)
```

Keep the existing sampling, finite filtering, coordinate generation, log
transform, counts, and all-invalid return path unchanged.

- [x] **Step 2: Replace azimuthal whole-array conversions**

Project `azimuthal_chi` and `azimuthal_I` separately through
`_coerce_numeric_array()` and retain the existing aligned-prefix and finite
pair filter:

```python
chi = _coerce_numeric_array(getattr(anisotropy, "azimuthal_chi", ()))
intensity = _coerce_numeric_array(getattr(anisotropy, "azimuthal_I", ()))
```

Do not change the source order, pair count, role, or omission of empty/all-
invalid traces.

- [x] **Step 3: Run GREEN focused tests**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_2d_dirty_token_green'
python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_evidence_binding.py
```

Expected: a fresh pytest summary with zero failures.

### Task 3: Verify and checkpoint

**Files:**
- Use only the seven files in the task card allowlist.

- [x] **Step 1: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-2d-figure-dirty-token-projection.md --changed --types
```

Record the actual quality/preprocessing, Ruff, compile, type, task, and
whitespace outcomes; do not infer results from an interrupted command.

- [x] **Step 2: Run the fresh SAXS matrix**

Run the repository's SAXS test matrix with an external basetemp. Count it only
when pytest prints its final summary and exits `0`; a timeout is recorded as a
timeout and is not a pass.

- [x] **Step 3: Run storage and diff audits**

```powershell
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
git status --short
```

Do not run `test_storage.py --apply`, remove directories, or stage unrelated
files.

- [ ] **Step 4: Create the explicit checkpoint**

```powershell
python scripts/auto_commit.py `
  --message "fix(saxs): recover dirty 2d figure tokens" `
  --files polynexus/core/saxs_engine/figure_detector.py `
          polynexus/core/saxs_engine/figure_strain.py `
          tests/test_saxs_detector_figure_modes.py `
          tests/test_saxs_figure_evidence_binding.py `
          docs/agent/tasks/2026-07-30-saxs-2d-figure-dirty-token-projection.md `
          docs/superpowers/specs/2026-07-30-saxs-2d-figure-dirty-token-projection-design.md `
          docs/superpowers/plans/2026-07-30-saxs-2d-figure-dirty-token-projection.md
```

Confirm the resulting commit hash and keep all pre-existing changes outside the
allowlist untouched.

## Plan self-review

- The design's detector, azimuthal, non-goal, and verification requirements
  are covered by Tasks 1-3.
- No placeholder steps or unspecified scientific thresholds are used.
- The helper signatures and existing provenance field names remain consistent
  across all tasks.
