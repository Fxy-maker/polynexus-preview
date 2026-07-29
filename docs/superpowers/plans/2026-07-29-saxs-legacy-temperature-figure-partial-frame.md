# SAXS Legacy Temperature Figure Partial-Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the legacy SAXS temperature Figure provider omit only fully unplottable frames while preserving source-index evidence.

**Architecture:** Keep a full-length internal slot list of either a cleaned q/I pair or `None`. Build valid-frame definitions and series sources from the valid slots, while the existing evidence plan and summary arrays continue to use original zero-based indices. Add only a stable omission reason to recipe evidence.

**Tech Stack:** Python, NumPy, pytest, repository verifier, explicit-allowlist auto-commit.

---

### Task 1: Add the failing regression

**Files:**
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [x] **Step 1: Add one test for a partially unavailable legacy temperature series**

```python
def test_legacy_temperature_provider_omits_unplottable_frame_with_evidence(
    saxs_temperature_inputs,
):
    result, q_values, intensities = saxs_temperature_inputs
    q_values = list(q_values)
    intensities = list(intensities)
    q_values[1] = np.asarray(["bad-q", "also-bad"], dtype=object)
    intensities[1] = np.asarray(["bad-intensity", "still-bad"], dtype=object)

    definitions = build_saxs_temperature_definitions(
        result,
        q_values,
        intensities,
    )

    frame_ids = {item.figure_id for item in definitions}
    assert "saxs.frame.temperature.scattering.001" in frame_ids
    assert "saxs.frame.temperature.scattering.002" not in frame_ids
    parameters = next(
        item for item in definitions
        if item.figure_id == "saxs.series.temperature.parameters"
    )
    assert parameters.data_sources[0].values["temperature_C"] == (30.0,)
    evidence = parameters.recipe["evidence"]
    assert evidence["included_frame_indices"] == [0]
    assert evidence["omitted_frame_indices"] == [1]
    assert evidence["omission_reasons"][1] == "figure_profile_unavailable"
```

- [x] **Step 2: Run the RED test and inspect the failure**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_temperature_partial_red'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k unplottable
```

Expected result before implementation: one failure caused by the existing
`ValueError` from `_clean_frame()` for the second frame.

### Task 2: Preserve unavailable slots in the legacy provider

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_provider.py`

- [x] **Step 1: Add an optional frame-level projection helper**

Add a helper beside `_clean_frame()` that calls the existing cleaner and
returns `(clean_q, clean_intensity)` on success or `(None, "figure_profile_unavailable")` when the current frame-level cleaner rejects the slot. Do not catch structural sequence-count validation outside the per-frame loop.

- [x] **Step 2: Build temperature definitions from valid slots only**

In `build_saxs_temperature_definitions()`, keep `cleaned_frames` full-length
with `None` for unavailable slots and collect `available_indices`. Use the
original loop index plus one for valid per-frame Figure ids. Filter evidence
selected indices through `available_indices`, and add unavailable indices to
`omitted_frame_indices` and `omission_reasons`.

- [x] **Step 3: Keep waterfall and summary indices source-aligned**

Update the legacy temperature waterfall helper to accept the full slot list and
select only valid source indices. Pass the same valid-index list to parameter
and heatmap builders. Keep existing clean-series selection, source ids, roles,
and V2 adapter metadata unchanged.

- [x] **Step 4: Run the RED test as GREEN**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_temperature_partial_green'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k unplottable
```

Expected: the new regression passes with one omitted source frame and original
index evidence.

### Task 3: Verify compatibility and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md`
- Create: `docs/acceptance/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md`

- [x] **Step 1: Run focused provider coverage**

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py
```

Expected: the complete file passes, including clean lifecycle and dirty-valid-
pair tests.

- [x] **Step 2: Run structured and exact SAXS verification**

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
```

Count the SAXS matrix only with a final pytest summary and exit code `0`.

- [x] **Step 3: Run non-mutating audits and inspect scope**

```powershell
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git status --short
```

Both storage commands must remain dry-run. Do not run `--apply`.

- [x] **Step 4: Record evidence and create one explicit checkpoint**

Update the task and acceptance note with actual command summaries and known
limitations, then run:

```powershell
python scripts/auto_commit.py --message "fix(saxs): degrade legacy temperature figure gaps" --files polynexus/core/saxs_engine/figure_provider.py tests/test_saxs_temperature_figure_provider.py docs/agent/tasks/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md docs/superpowers/specs/2026-07-29-saxs-legacy-temperature-figure-partial-frame-design.md docs/superpowers/plans/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md docs/acceptance/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md
```

Do not stage or commit parallel files, memory files, scratch, or generated
outputs.

## Actual evidence

- RED: `1 failed, 10 deselected`.
- GREEN: `1 passed, 10 deselected`; complete provider file `11 passed`.
- Related consumers: `30 passed, 25 deselected`.
- Structured verifier: exit `0`, quality `287`, preprocessing `106`.
- Exact SAXS matrix: `574 passed, 6 warnings`, exit `0`.
- Storage report/clean: dry-run, `30` artifacts, `0` eligible bytes, `0`
  removed; `--apply` was not run.
