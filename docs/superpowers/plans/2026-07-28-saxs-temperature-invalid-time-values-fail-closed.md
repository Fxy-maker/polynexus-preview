# SAXS invalid temperature-time values fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Convert invalid values in a correctly-sized optional time axis to
explicit unavailable time evidence without aborting temperature-frame SAXS.

**Architecture:** Reuse `_coerce_optional_float()` elementwise, detect
non-finite converted values before sorting, preserve frame/source alignment, and
skip Avrami with an explicit reason. The prior length-mismatch branch remains
the higher-priority failure reason.

**Tech Stack:** Python, NumPy, Pytest, SAXS temperature result DTOs, Ruff, and
the repository verifier.

---

### Task 1: Lock invalid-time behavior with RED

**Files:**
- Create: `tests/test_saxs_temperature_invalid_time_values_fail_closed.py`

- [x] **Step 1: Write the failing regression**

```python
import json

import numpy as np

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def _profile() -> tuple[np.ndarray, np.ndarray]:
    q = np.linspace(0.02, 1.8, 80)
    intensity = 180.0 * np.exp(-(q**2) * 2.2) + 8.0
    return q, intensity


def test_invalid_times_preserve_frames_and_disable_avrami():
    q, intensity = _profile()
    result = analyze_temperature_series(
        [180.0, 170.0],
        [q, q],
        [intensity, intensity],
        times=["0.0", "bad"],
        cfg=SAXSConfig(),
        exp_type="cooling",
    )

    assert len(result.temp_points) == 2
    assert [point.source_index for point in result.temp_points] == [1, 0]
    assert result.avrami == {
        "valid": False,
        "reason": "temperature_time_axis_invalid_values",
    }
    json.dumps(result.avrami, allow_nan=False)
```

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_red'
python -m pytest -q tests/test_saxs_temperature_invalid_time_values_fail_closed.py
```

Expected: FAIL with the existing bulk-cast `ValueError`.

### Task 2: Add elementwise time coercion

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py` in the existing
  correctly-sized `times` branch and Avrami condition.

- [x] **Step 1: Convert and record invalid values**

```python
    time_axis_invalid_values = False
    if times is not None:
        if time_axis_length_mismatch:
            times_arr = np.full(n_points, np.nan, dtype=float)
        else:
            time_values = np.asarray(
                [_coerce_optional_float(value) for value in times],
                dtype=float,
            )
            time_axis_invalid_values = bool(np.any(~np.isfinite(time_values)))
            times_arr = time_values[sort_idx]
    else:
        times_arr = np.arange(n_points, dtype=float)
```

After result initialization, only when the length mismatch is false:

```python
    if time_axis_invalid_values:
        result.avrami = {
            "valid": False,
            "reason": "temperature_time_axis_invalid_values",
        }
```

Skip fitting when either time-axis limitation is active:

```python
    if (
        not time_axis_length_mismatch
        and not time_axis_invalid_values
        and exp_type in ("cooling", "isothermal")
        and len(times_arr) > 5
    ):
        result.avrami = avrami_kinetics(times_arr, result.Xc_array)
```

- [x] **Step 2: Run focused GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_focus'
python -m pytest -q tests/test_saxs_temperature_invalid_time_values_fail_closed.py tests/test_saxs_temperature_time_axis_fail_closed.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py
```

Evidence: `25 passed`.

### Task 3: Verify and checkpoint

**Files:**
- Update: task/spec/plan and durable memory with actual evidence.

- [x] **Step 1: Run exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_matrix
```

- [x] **Step 2: Run task verifier and diff check**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_time_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md --changed --types
git diff --check
```

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): fail closed on invalid temperature times" --files polynexus/core/saxs_engine/saxs_temperature.py tests/test_saxs_temperature_invalid_time_values_fail_closed.py docs/agent/tasks/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-temperature-invalid-time-values-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-temperature-invalid-time-values-fail-closed.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

Keep unrelated release, GUI/editor, scratch, and parallel task files outside
the checkpoint.
