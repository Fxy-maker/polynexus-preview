# SAXS invalid temperature-axis fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Convert malformed temperature-axis elements to explicit unresolved
values so the corresponding SAXS frames remain analyzable and auditable.

**Architecture:** Preserve the existing list-length guard and use the existing
`_coerce_optional_float()` helper for elementwise conversion. Do not alter
sorting, frame analysis, sequence evidence, or non-invalid conditions.

**Tech Stack:** Python, NumPy, Pytest, SAXS sequence evidence DTOs, Ruff, and
the repository verifier.

---

### Task 1: Lock invalid-axis behavior with RED

**Files:**
- Create: `tests/test_saxs_temperature_invalid_axis_fail_closed.py`

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


def test_invalid_temperature_values_are_retained_as_unresolved_frames():
    q, intensity = _profile()
    result = analyze_temperature_series(
        ["170", "bad", None],
        [q, q, q],
        [intensity, intensity, intensity],
        cfg=SAXSConfig(),
    )

    assert len(result.temp_points) == 3
    assert result.temp_points[0].temperature_C == 170.0
    assert np.isnan(result.temp_points[1].temperature_C)
    assert np.isnan(result.temp_points[2].temperature_C)
    assert [point.source_index for point in result.temp_points] == [0, 1, 2]
    assert result.guinier_sequence_evidence["level"] == "Unusable"
    assert "guinier_sequence_temperature_axis_invalid" in result.guinier_sequence_evidence["reason_codes"]
    json.dumps(result.guinier_sequence_evidence, allow_nan=False)
```

- [x] **Step 2: Run RED**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_red'
python -m pytest -q tests/test_saxs_temperature_invalid_axis_fail_closed.py
```

Expected: FAIL with `ValueError: could not convert string to float: 'bad'`.

### Task 2: Implement elementwise fail-closed conversion

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py` at the existing
  `temps_arr` conversion.

- [x] **Step 1: Use the existing coercion helper**

Replace:

```python
temps_arr = np.array(temperatures, dtype=float)
```

with:

```python
temps_arr = np.asarray(
    [_coerce_optional_float(value) for value in temperatures],
    dtype=float,
)
```

Do not change the surrounding sort, source-index, or frame-analysis code.

- [x] **Step 2: Run focused GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_focus'
python -m pytest -q tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py
```

Expected: all focused tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Update: task/spec/plan and durable memory with actual evidence.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_matrix
```

- [x] **Step 2: Run task-scoped verification and diff check**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_invalid_axis_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md --changed --types
git diff --check
```

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): fail closed on invalid temperature axis" --files polynexus/core/saxs_engine/saxs_temperature.py tests/test_saxs_temperature_invalid_axis_fail_closed.py docs/agent/tasks/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-temperature-invalid-axis-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-temperature-invalid-axis-fail-closed.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

Keep all unrelated release, GUI/editor, scratch, and parallel task files out of
the checkpoint.

Evidence: RED `1 failed`; focused GREEN `23 passed`; exact SAXS matrix `416
passed, 6 warnings`. The separate mismatched-`times` boundary and
full/boundary verification are not claimed for this task.
