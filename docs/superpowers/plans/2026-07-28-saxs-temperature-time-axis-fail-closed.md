# SAXS mismatched temperature time axis fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Preserve temperature-frame analysis and explicitly disable Avrami
when a supplied time axis cannot be aligned to the frames.

**Architecture:** Validate only the optional time-axis length at the series
boundary. A mismatch receives an all-NaN internal alignment array and a
JSON-safe Avrami failure reason; no synthetic time values enter analysis.

**Tech Stack:** Python, NumPy, Pytest, SAXS temperature result DTOs, Ruff, and
the repository verifier.

---

### Task 1: Lock the mismatch contract with RED

**Files:**
- Create: `tests/test_saxs_temperature_time_axis_fail_closed.py`

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


def test_mismatched_times_preserves_frames_and_disables_avrami():
    q, intensity = _profile()
    result = analyze_temperature_series(
        [180.0, 170.0],
        [q, q],
        [intensity, intensity],
        times=[0.0],
        cfg=SAXSConfig(),
        exp_type="cooling",
    )

    assert len(result.temp_points) == 2
    assert [point.source_index for point in result.temp_points] == [1, 0]
    assert result.avrami == {
        "valid": False,
        "reason": "temperature_time_axis_length_mismatch",
    }
    json.dumps(result.avrami, allow_nan=False)
```

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_time_axis_red'
python -m pytest -q tests/test_saxs_temperature_time_axis_fail_closed.py
```

Expected: FAIL with `IndexError` from indexing `times` by the two-frame sort
index.

### Task 2: Add the minimal mismatch guard

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py` around the
  `times_arr` construction and Avrami post-analysis block.

- [x] **Step 1: Guard alignment and record the limitation**

```python
    time_axis_length_mismatch = times is not None and len(times) != n_points
    if times is not None:
        if time_axis_length_mismatch:
            times_arr = np.full(n_points, np.nan, dtype=float)
        else:
            times_arr = np.array(times, dtype=float)[sort_idx]
    else:
        times_arr = np.arange(n_points, dtype=float)
```

After `result = TempSeriesResult(experiment_type=exp_type)`:

```python
    if time_axis_length_mismatch:
        result.avrami = {
            "valid": False,
            "reason": "temperature_time_axis_length_mismatch",
        }
```

Replace the final Avrami condition with:

```python
    if (
        not time_axis_length_mismatch
        and exp_type in ("cooling", "isothermal")
        and len(times_arr) > 5
    ):
        result.avrami = avrami_kinetics(times_arr, result.Xc_array)
```

Do not change the absent or correctly-sized `times` behavior.

- [x] **Step 2: Run focused GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_time_axis_focus'
python -m pytest -q tests/test_saxs_temperature_time_axis_fail_closed.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py
```

Expected: all focused tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Update: task/spec/plan and durable memory with actual evidence.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_time_axis_matrix
```

- [x] **Step 2: Run task-scoped verification and diff check**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_time_axis_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-time-axis-fail-closed.md --changed --types
git diff --check
```

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): fail closed on mismatched temperature times" --files polynexus/core/saxs_engine/saxs_temperature.py tests/test_saxs_temperature_time_axis_fail_closed.py docs/agent/tasks/2026-07-28-saxs-temperature-time-axis-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-temperature-time-axis-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-temperature-time-axis-fail-closed.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

Keep unrelated release, GUI/editor, scratch, and parallel task files outside
the checkpoint.

Evidence: RED `1 failed`; focused GREEN `24 passed`; exact SAXS matrix `417
passed, 6 warnings`. Invalid time elements and full/boundary verification are
not claimed for this task.
