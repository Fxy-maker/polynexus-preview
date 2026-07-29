# SAXS 1D Figure Dirty Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Share a detached elementwise numeric projection across SAXS static, temperature, strain, and legacy 1D Figure providers.

**Architecture:** `figure_common._coerce_numeric_array()` creates a fresh float vector with invalid elements represented as `NaN`. Each provider keeps its current pair filtering, sorting, uniqueness, minimum-point, overlap, and fail-closed rules; only the conversion boundary is shared.

**Tech Stack:** Python, NumPy, pytest, repository verifier, explicit-allowlist auto-commit.

---

### Task 1: Add the failing provider regressions

**Files:**
- Modify: `tests/test_saxs_temperature_figure_panels.py`
- Modify: `tests/test_saxs_temperature_figure_provider.py`
- Modify: `tests/test_saxs_figure_evidence_binding.py`

- [x] **Step 1: Add a dirty temperature-provider test**

Append to `tests/test_saxs_temperature_figure_panels.py`:

```python
def test_dirty_projection_temperature_waterfall_keeps_valid_pairs() -> None:
    engine = _temperature_engine()
    engine._q_list[0] = np.asarray(["0.08", "bad-q", "0.18", "0.25"], dtype=object)
    engine._I_list[0] = np.asarray(["8.0", "6.0", "bad-intensity", "1.0"], dtype=object)
    q_before = engine._q_list[0].copy()
    intensity_before = engine._I_list[0].copy()

    definitions = build_temperature_figure_definitions(engine)
    waterfall = next(item for item in definitions if item.figure_id == "saxs.temperature.waterfall")
    source = next(item for item in waterfall.data_sources if item.source_id == "saxs-temperature-waterfall-000")

    assert source.values["q_nm1"] == (0.08, 0.25)
    assert source.values["intensity_offset"] == (8.0, 1.0)
    assert np.array_equal(engine._q_list[0], q_before)
    assert np.array_equal(engine._I_list[0], intensity_before)
```

- [x] **Step 2: Add a dirty legacy-provider test**

Append to `tests/test_saxs_temperature_figure_provider.py`:

```python
def test_dirty_projection_legacy_temperature_frame_keeps_valid_pairs(saxs_temperature_inputs):
    result, q_values, intensities = saxs_temperature_inputs
    q_values = list(q_values)
    intensities = list(intensities)
    q_values[0] = np.asarray(["0.1", "bad-q", "0.3", "0.4"], dtype=object)
    intensities[0] = np.asarray(["100.0", "80.0", "bad-intensity", "20.0"], dtype=object)

    definitions = build_saxs_temperature_definitions(result, q_values, intensities)
    source = definitions[0].data_sources[0]

    assert source.values["q_nm1"] == (0.1, 0.4)
    assert source.values["intensity_au"] == (100.0, 20.0)
```

- [x] **Step 3: Add a dirty strain-provider test**

Append to `tests/test_saxs_figure_evidence_binding.py`:

```python
def test_dirty_projection_strain_keeps_profile_and_q_strain_sources() -> None:
    engine = _strain_engine()
    engine._q_list[0] = np.asarray(["0.1", "bad-q", "0.3", "0.4"], dtype=object)
    engine._I_list[0] = np.asarray(["2.0", "3.0", "4.0", "bad-intensity"], dtype=object)

    definitions = build_strain_figure_definitions(engine)
    evolution = next(item for item in definitions if item.figure_id == "saxs.strain.evolution.1d")
    profile = next(item for item in evolution.data_sources if item.source_id == "representative-profile-000")
    heatmap = next(item for item in evolution.data_sources if item.source_id == "q-strain-heatmap")

    assert profile.values["q_nm_inv"] == (0.1, 0.3)
    assert profile.values["intensity"] == (2.0, 4.0)
    assert len(heatmap.values["q_nm_inv"]) >= 2
```

- [x] **Step 4: Add dirty derived-trace regressions**

Append one temperature trace regression to
`tests/test_saxs_temperature_figure_panels.py`:

```python
def test_dirty_projection_temperature_trace_keeps_valid_pairs() -> None:
    engine = _temperature_engine()
    engine._batch_results[0].correlation = {
        "r": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "gamma": np.asarray(["0.8", "0.5", "0.2", "bad-gamma"], dtype=object),
    }
    definitions = build_temperature_figure_definitions(engine)
    evidence = next(item for item in definitions if item.figure_id == "saxs.temperature.evidence.000")
    source = next(item for item in evidence.data_sources if item.source_id == "saxs-temperature-correlation-000")

    assert source.values["r_nm"] == (1.0, 3.0)
    assert source.values["gamma"] == (0.8, 0.2)
```

Append one strain trace regression to
`tests/test_saxs_figure_evidence_binding.py`:

```python
def test_dirty_projection_strain_trace_keeps_valid_pairs() -> None:
    engine = _strain_engine()
    engine._batch_results[0].correlation = {
        "r": np.asarray(["1.0", "bad-r", "3.0", "4.0"], dtype=object),
        "gamma": np.asarray(["0.8", "0.5", "0.2", "bad-gamma"], dtype=object),
    }
    definitions = build_strain_figure_definitions(engine)
    correlation = next(item for item in definitions if item.figure_id == "saxs.strain.correlation")
    source = next(item for item in correlation.data_sources if item.source_id == "correlation-trace-000")

    assert source.values["x"] == (1.0, 3.0)
    assert source.values["y"] == (0.8, 0.2)
```

- [x] **Step 5: Preserve the existing static shared-helper regression**

The previously checkpointed static regression remains in
`tests/test_saxs_static_figure_panels.py`; it remains green after the static
provider imports the shared helper. This file has no new worktree change and
is not part of this checkpoint's changed-file allowlist.

- [x] **Step 6: Run the RED selection**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_figure_1d_dirty_red'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_evidence_binding.py -k dirty_projection
```

Expected: the new temperature, legacy, and strain tests fail because their
providers reject whole-array dirty conversions; the existing static test is
not selected. Record the actual summary and failure reasons.

### Task 2: Implement the shared conversion boundary

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_common.py`
- Modify: `polynexus/core/saxs_engine/figure_static.py`
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`
- Modify: `polynexus/core/saxs_engine/figure_strain.py`
- Modify: `polynexus/core/saxs_engine/figure_provider.py`

- [x] **Step 1: Add the shared helper**

Add near the other private projection helpers in `figure_common.py`:

```python
def _coerce_numeric_array(values: Any) -> np.ndarray:
    source = np.asarray(values).reshape(-1)
    projected = np.full(source.shape, np.nan, dtype=float)
    for index, value in enumerate(source):
        try:
            projected[index] = float(value)
        except (OverflowError, TypeError, ValueError):
            continue
    return projected
```

- [x] **Step 2: Migrate the static provider**

Import `_coerce_numeric_array` with `SAXSFrameView` and replace the local
`_elementwise_float_array` body/use in `figure_static.py` with the shared
helper. Keep `_numeric_pairs` filtering and return logic unchanged.

- [x] **Step 3: Migrate temperature 1D paths**

In `figure_temperature.py`, replace both q/intensity conversions in
`_positive_curve` and both x/y conversions in `_mapping_curve` with
`_coerce_numeric_array`. Keep existing count, finite, positive, sort, and
minimum checks unchanged.

- [x] **Step 4: Migrate strain 1D paths**

In `figure_strain.py`, replace conversions in `_profile_values`,
`_q_strain_source`, and `_analysis_trace` with the shared helper. Do not change
detector image or azimuthal chi paths.

- [x] **Step 5: Migrate the legacy frame cleaner**

In `figure_provider.py`, replace the two whole-array conversions in
`_clean_frame` with the shared helper. Keep its length mismatch and no-plottable
data `ValueError` contracts unchanged.

- [x] **Step 6: Run focused GREEN**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_figure_1d_dirty_green'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_static_figure_panels.py -k dirty_projection
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py tests/test_saxs_figure_evidence_binding.py tests/test_saxs_static_figure_panels.py
```

Expected: all dirty regressions and the complete focused provider files pass.

### Task 3: Verify, document, and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-figure-1d-dirty-projection.md`
- Create: `docs/acceptance/2026-07-29-saxs-figure-1d-dirty-projection.md`
- Preserve: staged `docs/agent/memory/active-work.md`; its evidence is outside
  this checkpoint because the same file contains parallel release-packet work.

- [x] **Step 1: Run the structured verifier**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-figure-1d-dirty-projection.md --changed --types
```

Expected: exit `0` with exact quality/preprocessing, Ruff, compile, type,
memory/task, and whitespace summaries.

- [x] **Step 2: Run exact SAXS and storage audits**

Run the exact `tests/test_saxs_*.py` matrix with an external basetemp and count
it only if pytest gives a final summary and exit `0`. Then run
`python scripts/test_storage.py report --json` and
`python scripts/test_storage.py clean --older-than-hours 24`; both storage
commands remain dry-run.

- [x] **Step 3: Inspect diff and update evidence**

Run `git diff --check` and `git status --short`. Record exact RED/GREEN,
verifier, SAXS, storage, and limitation evidence. Do not edit
`current-state.md`, include scratch, or mix the staged `active-work.md` file.

- [x] **Step 4: Create one explicit checkpoint**

```powershell
python scripts/auto_commit.py --message "fix(saxs): harden 1d figure dirty projection" --files <the explicit allowlist from the task card>
```

The helper must create one local commit containing only this task's allowlist;
`active-work.md` is intentionally excluded because its staged parallel release
packet must remain intact;
do not push, merge, deploy, delete, or migrate unrelated files.
