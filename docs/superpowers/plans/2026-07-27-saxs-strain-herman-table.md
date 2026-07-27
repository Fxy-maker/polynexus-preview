# SAXS Strain Herman Orientation Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the existing SAXS strain data path so finite Herman orientation factors calculated from 2D sector data appear in each result-table row, while unavailable frames remain unavailable.

**Architecture:** Retain one optional `sector_data` object per loaded frame in `SAXSEngine`, pass the aligned list through the existing `analyze_strain_series(sector_data_list=...)` contract, and copy each `StrainPointResult.f_herman` into the existing `_batch_params` row. The GUI already declares and renders `f_Herman`; its tests will verify the payload-to-table contract without adding GUI-side scientific logic.

**Tech Stack:** Python, NumPy, PySide6 result-table presentation contracts, pytest, repository `scripts/verify.py`.

---

## File map

- Modify: `polynexus/core/saxs.py`
  - Add `_sector_data_list` engine state.
  - Keep list alignment in both directory-loading paths and reset it with the
    other frame arrays.
  - Pass the list to both strain entry points.
  - Publish `f_Herman` in each strain `_batch_params` row.
- Modify: `tests/test_saxs_batch_parameters.py`
  - Add a core regression for finite and unavailable per-frame factors and
    series aggregation.
- Modify: `tests/test_saxs_results_table_service.py`
  - Assert that the existing strain table consumes a numeric `f_Herman` and
    preserves the unavailable display for `None`.
- Modify: `docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md`
  - Check off acceptance criteria and record verification evidence.
- Modify: `docs/superpowers/plans/2026-07-27-saxs-strain-herman-table.md`
  - Track completed implementation steps.
- The parallel release-audit memory files are intentionally excluded from this
  task checkpoint.

## Task 1: Add the failing core transport regression

**Files:**
- Modify: `tests/test_saxs_batch_parameters.py`

- [x] **Step 1: Add a test for finite and missing Herman values in a strain payload.**

Use the existing `get_engine("saxs")` fixture pattern and construct a
`StrainSeriesResult` whose points contain one finite `f_herman` and one NaN.
Set `_batch_params` to two aligned rows, call `engine.get_parameters()`, and
assert that the finite row contains the published factor while the missing row
is `None` and the aggregate contains only the finite value:

```python
def test_saxs_strain_payload_publishes_per_frame_herman_factor() -> None:
    engine = get_engine("saxs")
    assert engine is not None
    from polynexus.core.saxs_engine.saxs_strain import (
        StrainPhase,
        StrainPointResult,
        StrainSeriesResult,
    )

    engine._conditions = [0.0, 10.0]  # type: ignore[attr-defined]
    engine._condition_confidences = [0.9, 0.9]  # type: ignore[attr-defined]
    engine._batch_params = [  # type: ignore[attr-defined]
        {"file": "frame_001.edf", "strain_pct": 0.0, "phase_name": "elastic"},
        {"file": "frame_002.edf", "strain_pct": 10.0, "phase_name": "elastic"},
    ]
    engine._strain_result = StrainSeriesResult(  # type: ignore[attr-defined]
        strain_points=[
            StrainPointResult(strain_pct=0.0, phase=StrainPhase.ELASTIC, f_herman=0.42),
            StrainPointResult(strain_pct=10.0, phase=StrainPhase.ELASTIC, f_herman=np.nan),
        ],
        strains=np.asarray([0.0, 10.0]),
        L_array=np.asarray([12.0, 12.1]),
        Q_star_array=np.asarray([10.0, 10.1]),
        Q_star_rel_array=np.asarray([1.0, 1.01]),
        f_herman_array=np.asarray([0.42, np.nan]),
        phi_void_array=np.asarray([np.nan, np.nan]),
    )

    params = engine.get_parameters()

    assert params["_batch_data"][0]["f_Herman"] == 0.42
    assert params["_batch_data"][1]["f_Herman"] is None
    assert params["f_Herman_mean"] == 0.42
    assert params["f_Herman_span"] == 0.0
    assert params["f_Herman_range"] == "0.4200-0.4200"
```

The test must assert the desired public payload rather than private helper
implementation details. If the current `StrainPointResult` constructor
requires additional defaults, use the existing defaults shown in
`tests/test_saxs_batch_parameters.py`; do not weaken the assertions.

- [x] **Step 2: Run the new test and confirm the expected RED failure.**

Run:

```powershell
python -m pytest tests/test_saxs_batch_parameters.py::test_saxs_strain_payload_publishes_per_frame_herman_factor -q
```

Expected result before production changes: failure because the `_batch_data`
rows do not contain `f_Herman`.

## Task 2: Add the minimal core sector-data lifecycle

**Files:**
- Modify: `polynexus/core/saxs.py:187-193`
- Modify: `polynexus/core/saxs.py:394-455`
- Modify: `polynexus/core/saxs.py:480-525`

- [x] **Step 1: Initialize the aligned sector-data list.**

Add this field beside `_I_merid_list` and `_I_equat_list`:

```python
self._sector_data_list: List[Dict[str, Any] | None] = []
```

- [x] **Step 2: Reset the list at every directory-load reset point.**

In `_load_directory`, reset `_sector_data_list` beside `_I_equat_list` both at
the initial setup and in the EDF fallback reload branch. This prevents stale
frames from a prior load from being passed into a new strain sequence.

- [x] **Step 3: Append one aligned sector entry per loaded file.**

For image input, append `pp.get("sector_data")`; for 1D input, append `None`.
The append must occur in the same successful-file path and in the same order as
`_q_list`, `_I_list`, and `_file_list`:

```python
sector_data = pp.get("sector_data") if img is not None else None
self._sector_data_list.append(sector_data)
```

In the fallback EDF loop, append the equivalent value in both the image and
1D branches. Do not serialize, deep-copy, or reinterpret the sector map here;
the existing strain calculation consumes the in-memory object.

## Task 3: Pass sector data through both strain entry points

**Files:**
- Modify: `polynexus/core/saxs.py:1336-1341`
- Modify: `polynexus/core/saxs.py:1692-1697`

- [x] **Step 1: Pass the aligned list in `_run_strain_pipeline()`.**

Extend the existing call without changing the calculation defaults:

```python
self._strain_result = analyze_strain_series(
    strains=list(self._conditions),
    q_list=self._q_list,
    I_list=I_use,
    sector_data_list=self._sector_data_list,
    cfg=replace(strain_cfg),
)
```

- [x] **Step 2: Pass the aligned list in `analyze_strain()`.**

Use the same existing list in the direct API entry point:

```python
result = analyze_strain_series(
    strains=strains,
    q_list=self._q_list,
    I_list=self._I_list,
    sector_data_list=self._sector_data_list,
    cfg=self.cfg,
)
```

An empty list remains safe because `analyze_strain_series` already treats its
optional input as absent when no entries are available.

## Task 4: Publish the per-frame factor into the existing table payload

**Files:**
- Modify: `polynexus/core/saxs.py:1435-1462`
- Modify: `polynexus/core/saxs.py:1464-1502`

- [x] **Step 1: Read the aligned point factor once.**

After `strain_point` is selected, derive a finite-safe value:

```python
f_herman = _first_finite(getattr(strain_point, "f_herman", np.nan))
```

Keep `f_herman` separate from `orientation_evidence`. Do not alter the existing
phase-support score or reliability thresholds in this task.

- [x] **Step 2: Add the table field with an unavailable fallback.**

Add the row entry beside the existing strain metrics:

```python
"f_Herman": round(float(f_herman), 4) if np.isfinite(f_herman) else None,
```

This produces a JSON-safe scalar or `None`, and the existing table formatter
will render `None` as an em dash/unavailable value according to its current
contract.

- [x] **Step 3: Run the core regression and the existing strain parameter tests.**

Run:

```powershell
python -m pytest tests/test_saxs_batch_parameters.py::test_saxs_strain_payload_publishes_per_frame_herman_factor tests/test_saxs_batch_parameters.py -q
```

Expected result: the new regression and the existing batch-parameter tests
pass, with no changes to unrelated summary fields.

## Task 5: Verify the GUI presentation contract without GUI production changes

**Files:**
- Modify: `tests/test_saxs_results_table_service.py`

- [x] **Step 1: Add a numeric and unavailable cell assertion.**

Extend the existing strain presentation test with two rows, one with
`f_Herman=0.42` and one with `f_Herman=None`, then assert:

```python
assert _cell(presentation.primary, 0, "f_Herman").raw == 0.42
assert _cell(presentation.primary, 0, "f_Herman").display == "0.4200"
assert _cell(presentation.primary, 1, "f_Herman").raw is None
assert _cell(presentation.primary, 1, "f_Herman").display == "—"
```

Keep the existing primary-column order unchanged. This test proves that the
GUI-side field already present in `result_table_templates.py` consumes the core
payload directly.

- [x] **Step 2: Run the focused presentation tests.**

Run:

```powershell
python -m pytest tests/test_saxs_results_table_service.py -q
```

Expected result: all existing and new table tests pass.

## Task 6: Run repository verification and finish the atomic task

**Files:**
- Modify: `docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md`
- Modify: `docs/superpowers/plans/2026-07-27-saxs-strain-herman-table.md`
- Do not modify the parallel release-audit memory files.

- [x] **Step 1: Run the full SAXS matrix.**

Run:

```powershell
python -m pytest (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
```

Record the exact pass count and existing warning count in the task card.

- [x] **Step 2: Run the structured verifier.**

Run:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md --changed --types
```

Do not claim completion unless the command exits successfully. If it fails,
repair the smallest relevant issue, rerun the failing focused command, and then
rerun the verifier.

- [x] **Step 3: Review the allowlist and cumulative diff.**

Run:

```powershell
git diff --check
git status --short
git diff -- polynexus/core/saxs.py tests/test_saxs_batch_parameters.py tests/test_saxs_results_table_service.py
```

Confirm that pre-existing Origin/editor files, temporary pytest directories,
and the parallel release-audit memory edits are not included in the task
checkpoint.

- [x] **Step 4: Create the local atomic checkpoint.**

After verification passes, run:

```powershell
python scripts/auto_commit.py `
  --message "feat(saxs): wire Herman orientation into strain results" `
  --files polynexus/core/saxs.py `
    tests/test_saxs_batch_parameters.py `
    tests/test_saxs_results_table_service.py `
    docs/agent/tasks/2026-07-27-saxs-strain-herman-table.md `
    docs/superpowers/specs/2026-07-27-saxs-strain-herman-table-design.md `
    docs/superpowers/plans/2026-07-27-saxs-strain-herman-table.md
```

The helper must create exactly one checkpoint from this allowlist and must not
push or merge it.
