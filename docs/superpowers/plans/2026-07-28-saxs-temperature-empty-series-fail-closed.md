# SAXS empty temperature series fail-closed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return a strict, auditable empty `TempSeriesResult` instead of
indexing a missing temperature reference frame.

**Architecture:** Keep the existing input-length guard. Add one early branch for
`n_points == 0` that reuses the existing sequence and metric evidence builders,
initializes empty result tracks, and leaves every non-empty path unchanged.

**Tech Stack:** Python, NumPy, dataclasses, Pytest, strict JSON evidence DTOs,
Ruff, and the repository verifier.

---

### Task 1: Lock the empty-series contract with RED

**Files:**
- Create: `tests/test_saxs_temperature_empty_series_fail_closed.py`

- [x] **Step 1: Write the failing test**

```python
import json

import pytest

from polynexus.core.saxs_engine.config import SAXSConfig
from polynexus.core.saxs_engine.saxs_temperature import analyze_temperature_series


def test_empty_temperature_series_returns_unusable_structured_result():
    result = analyze_temperature_series([], [], [], cfg=SAXSConfig())

    assert result.temp_points == []
    assert result.temperatures.size == 0
    assert result.guinier_sequence_evidence["level"] == "Unusable"
    assert "guinier_sequence_no_valid_frames" in result.guinier_sequence_evidence["reason_codes"]
    assert set(result.metric_evidence) == {
        "guinier", "porod", "kratky", "invariant", "lamellar"
    }
    assert all(
        evidence["level"] == "Unusable"
        and evidence["reason_codes"] == ["series_no_frames"]
        for evidence in result.metric_evidence.values()
    )
    assert result.sequence_rescue_candidates == []
    json.dumps(result.guinier_sequence_evidence, allow_nan=False)
    json.dumps(result.metric_evidence, allow_nan=False)


def test_empty_temperature_series_keeps_length_mismatch_validation():
    with pytest.raises(ValueError, match="same length"):
        analyze_temperature_series([180.0], [], [], cfg=SAXSConfig())
```

- [x] **Step 2: Run RED and confirm the root cause**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_empty_series_red'
python -m pytest -q tests/test_saxs_temperature_empty_series_fail_closed.py
```

Expected: the empty-series test fails with `IndexError: list index out of
range`; the mismatch test continues to pass.

### Task 2: Add the minimal fail-closed branch

**Files:**
- Modify: `polynexus/core/saxs_engine/saxs_temperature.py` after the existing
  `n_points` length validation and before source alignment/sorting.

- [x] **Step 1: Initialize the empty result using existing builders**

```python
    if n_points == 0:
        empty = np.asarray([], dtype=float)
        result = TempSeriesResult(experiment_type=exp_type)
        result.temperatures = empty.copy()
        result.L_array = empty.copy()
        result.lc_array = empty.copy()
        result.lc_effective_array = empty.copy()
        result.Q_star_array = empty.copy()
        result.Xc_array = empty.copy()
        result.Rg_array = empty.copy()
        result.lc_candidate_selected_score_array = empty.copy()
        result.guinier_sequence_evidence = build_guinier_sequence_evidence(
            [], [], source_indices=[],
            source_ref="saxs_temperature.guinier_sequence",
        ).to_dict()
        result.metric_evidence = build_series_metric_evidence(
            [],
            metric_names=("guinier", "porod", "kratky", "invariant", "lamellar"),
            source_ref="saxs_temperature.metric_evidence",
            frame_source_indices=[],
            condition_name="temperature_C",
            condition_values=[],
        )
        return result

    source_ids_aligned = _aligned_source_values(source_ids, n_points)
```

Do not alter the existing non-empty sort, reference-frame, or frame-analysis
logic.

- [x] **Step 2: Run focused GREEN**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_empty_series_focus'
python -m pytest -q tests/test_saxs_temperature_empty_series_fail_closed.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py
```

Expected: all focused tests pass.

### Task 3: Verify and checkpoint

**Files:**
- Update: this task card, spec, plan, and durable memory with actual evidence.

- [x] **Step 1: Run the exact SAXS matrix**

```powershell
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_temperature_empty_series_matrix
```

- [x] **Step 2: Run the structured verifier and diff check**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_empty_series_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-empty-series-fail-closed.md --changed --types
git diff --check
```

- [x] **Step 3: Create one explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): fail closed on empty temperature series" --files polynexus/core/saxs_engine/saxs_temperature.py tests/test_saxs_temperature_empty_series_fail_closed.py docs/agent/tasks/2026-07-28-saxs-temperature-empty-series-fail-closed.md docs/superpowers/specs/2026-07-28-saxs-temperature-empty-series-fail-closed-design.md docs/superpowers/plans/2026-07-28-saxs-temperature-empty-series-fail-closed.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

The command must not include existing GUI/editor/release changes, scratch
directories, or unrelated task files.

Evidence: RED `1 failed, 1 passed`; focused GREEN `22 passed`; exact SAXS
matrix `415 passed, 6 warnings`. Full/boundary verification is intentionally
not claimed for this scoped task.
