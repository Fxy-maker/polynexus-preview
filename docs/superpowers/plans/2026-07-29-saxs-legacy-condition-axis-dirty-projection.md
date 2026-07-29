# SAXS Legacy Condition-Axis Dirty Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make legacy SAXS condition-axis Figure labels degrade safely on malformed individual values.

**Architecture:** Reuse the existing detached numeric projection helper in the legacy provider's condition-axis boundary. Keep source selection, length fallback, frame order, and label fallback unchanged.

**Tech Stack:** Python, NumPy, pytest, repository verifier, explicit-allowlist auto-commit.

---

### Task 1: Add and verify the failing regression

**Files:**
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [x] **Step 1: Add the RED test**

```python
def test_legacy_condition_axis_dirty_values_keep_frame_order():
    conditions = ["0", "bad-strain", "25"]
    state = _saxs_provider_state(
        _strain_result=SimpleNamespace(strains=None),
        _q_list=[np.asarray([0.1, 0.2])] * 3,
        _I_list=[np.asarray([10.0, 5.0])] * 3,
        _conditions=conditions,
    )

    definitions = build_saxs_figure_definitions(state)

    assert [item.figure_id for item in definitions] == [
        "saxs.frame.strain.scattering.001",
        "saxs.frame.strain.scattering.002",
        "saxs.frame.strain.scattering.003",
        "saxs.series.strain.waterfall",
    ]
    assert [item.title for item in definitions[:3]] == [
        "SAXS Scattering - 0% strain",
        "SAXS Scattering - Frame 2",
        "SAXS Scattering - 25% strain",
    ]
    assert conditions == ["0", "bad-strain", "25"]
```

- [x] **Step 2: Run the RED test**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_condition_red'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k condition_axis
```

Expected before implementation: one failure with `ValueError` from the
whole-array condition conversion.

### Task 2: Use the detached condition projection

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py`

- [x] **Step 1: Replace only `_frame_condition_values()` conversion**

Change the array conversion to `_coerce_numeric_array(values)`. Retain the
existing size check and `tuple(float(value) for value in array)` return so
downstream label formatting and all-`NaN` length fallback remain unchanged.

- [x] **Step 2: Run GREEN and full provider coverage**

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_condition_green'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k condition_axis
python -m pytest -q tests/test_saxs_temperature_figure_provider.py
```

Expected: the new test and the complete provider file pass.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md`
- Create: `docs/acceptance/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md`

- [x] **Step 1: Run structured and exact SAXS verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
```

- [x] **Step 2: Run diff and storage dry-runs**

```powershell
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

- [x] **Step 3: Create the explicit allowlist checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): degrade legacy condition-axis labels" --files polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_temperature_figure_provider.py docs/agent/tasks/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md docs/superpowers/specs/2026-07-29-saxs-legacy-condition-axis-dirty-projection-design.md docs/superpowers/plans/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md docs/acceptance/2026-07-29-saxs-legacy-condition-axis-dirty-projection.md
```

Do not include parallel files, memory, scratch, generated output, or test
storage directories.

## Actual evidence

- RED: `1 failed, 11 deselected`.
- GREEN: `1 passed, 11 deselected`; complete provider `12 passed`.
- Structured verifier: exit `0`, quality `287`, preprocessing `106`.
- Exact SAXS matrix: `575 passed, 6 warnings`, exit `0`.
- Storage report/clean: dry-run `30` artifacts, `0` eligible bytes, `0`
  removed; `--apply` was not run.
