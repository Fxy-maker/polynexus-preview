# SAXS Static and Temperature Detector Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add conservative diagnostic 2D detector Figures to static and temperature SAXS providers using existing source paths and finite-pixel sampling.

**Architecture:** `figure_detector.py` owns only source extension checks, image reading, deterministic sampling, finite filtering, and compact provenance. Static and temperature providers own their Figure layout and selection policy, then attach the existing SAXS Figure evidence reference. No analysis service or GUI handler is changed.

**Tech Stack:** Python, NumPy, immutable SAXS Figure contracts, pytest, repository verifier.

---

### Task 1: Add RED tests for mode-specific detector Figures

**Files:**
- Create: `tests/test_saxs_detector_figure_modes.py`

- [x] **Step 1: Write the failing tests**

Add tests that monkeypatch `polynexus.core.saxs_engine.io.read_image` and assert the public builders expose the missing Figure. The test module defines `_static_engine(paths)` and `_temperature_engine(paths)` fixtures with `.edf` source paths:

```python
def test_static_detector_figure_projects_finite_pixels_and_counts(monkeypatch):
    engine = _static_engine(["static-0.edf", "static-1.edf"])
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (np.asarray([[1.0, np.nan], [4.0, 16.0]]), {}),
    )
    definition = next(
        item for item in build_static_saxs_figure_definitions(engine)
        if item.figure_id == "saxs.static.detector.2d"
    )
    source = definition.data_sources[0]
    assert source.values["pixel_x"] == (0, 0, 1)
    assert definition.recipe["parameters"]["detector_projection_quality"]["0"] == {
        "sampled_pixel_count": 4,
        "retained_pixel_count": 3,
        "nonfinite_pixel_count": 1,
        "status": "partial_nonfinite",
    }
    json.dumps(definition.recipe, allow_nan=False)


def test_temperature_detector_figure_preserves_selected_frame_indices(monkeypatch):
    engine = _temperature_engine(["temperature-0.edf", "temperature-1.edf", "temperature-2.edf"])
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (np.ones((2, 2)), {}),
    )
    definition = next(
        item for item in build_temperature_figure_definitions(engine)
        if item.figure_id == "saxs.temperature.detector.2d"
    )
    assert definition.recipe["parameters"]["included_frame_indices"] == [0, 1, 2]
    assert definition.publication_role == "diagnostic"


@pytest.mark.parametrize("builder", [build_static_saxs_figure_definitions, build_temperature_figure_definitions])
def test_all_invalid_detector_images_are_omitted(monkeypatch, builder):
    engine = _static_engine(["static-0.edf"]) if builder is build_static_saxs_figure_definitions else _temperature_engine(["temperature-0.edf"])
    monkeypatch.setattr(saxs_io, "read_image", lambda _path: (np.full((2, 2), np.nan), {}))
    assert not any(item.figure_id.endswith("detector.2d") for item in builder(engine))
```

- [x] **Step 2: Run the focused tests to verify RED**

Run:

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_static_temperature_detector_red'
python -m pytest -q tests/test_saxs_detector_figure_modes.py
```

Observed: `2 failed, 2 passed in 0.38s`; the two Figure lookups failed because
the current providers did not emit `*.detector.2d` definitions.

### Task 2: Implement the shared detector projection

**Files:**
- Create: `polynexus/core/saxs_engine/figure_detector.py`

- [x] **Step 1: Implement the minimal projection contract**

Implement `DetectorProjection`, `DetectorFrameEvidence`, `detector_capable`, and `build_detector_evidence`. The sampler must use `np.linspace` over each existing 2D array dimension with at most 256 positions, retain only finite sampled values, apply only `np.clip(value, tiny, None)` before `log10`, and return no record when no finite sampled value remains. Build memory sources with `pixel_x`, `pixel_y`, and `log_intensity` values and return frame-indexed reader/projection failures.

- [x] **Step 2: Run the RED tests again**

Run the same focused command. The provider lookup remains the expected failing
boundary until the mode-specific definitions are attached.

### Task 3: Add static diagnostic detector Figure

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py`

- [x] **Step 1: Add the mode-specific definition builder**

Use `select_representative_frames(frames, maximum=3, minimum_separation=2)`, call `build_detector_evidence` only for selected frames, create a `heatmap` object for each usable source, and return `None` when no usable source exists. Use `figure_id="saxs.static.detector.2d"`, `category="diagnostic"`, `publication_role="diagnostic"`, and recipe parameters containing `source_capability`, selected frame indices/reasons, source paths, failures, and projection quality.

- [x] **Step 2: Attach the definition without changing existing definitions**

Append the returned definition before the existing per-frame diagnostic loop, then keep the existing sort and Figure evidence attachment unchanged.

- [x] **Step 3: Run the static RED test**

Run:

```powershell
python -m pytest -q tests/test_saxs_detector_figure_modes.py -k static
```

Observed: static detector tests passed before the temperature provider was
attached.

### Task 4: Add temperature diagnostic detector Figure

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_temperature.py`

- [x] **Step 1: Build from the existing selection**

Use `selection.indices` from `build_temperature_figure_definitions`, call the shared service, create `heatmap` panels with the existing condition value only as a label, and include selection/source/failure/projection provenance in the recipe.

- [x] **Step 2: Append before final ordering and preserve evidence attachment**

Append only a usable diagnostic definition; retain all existing evolution, Avrami, waterfall, and selected-evidence definitions unchanged.

- [x] **Step 3: Run focused GREEN tests**

Run:

```powershell
python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_saxs_static_figure_panels.py tests/test_saxs_temperature_figure_panels.py
```

Observed: `81 passed` with exit code `0`.

### Task 5: Preserve detector axis labels

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_common.py`
- Modify: `polynexus/core/saxs_engine/figure_provider.py`

- [x] **Step 1: Extend only the shared label mapping**

Before the generic q/intensity fallback, map labels containing `detector` and `x`/`y` to `AXIS_LABELS["detector_x"]`/`AXIS_LABELS["detector_y"]`. Do not change numeric data or layout semantics.

- [x] **Step 2: Run focused Figure validation**

Run the mode tests and existing Figure evidence/publication tests. All passed
and detector axes remained pixel axes.

### Task 6: Verify and checkpoint

**Files:**
- Modify: all files in the explicit allowlist from the task card, including `docs/agent/memory/active-work.md`.

- [x] **Step 1: Run focused and task-scoped verification**

Run the exact commands from the task card and record fresh summaries, exit codes, warnings, and any timeout limitation.

- [x] **Step 2: Audit scope and storage**

Run `git diff --check`, `git status --short`, the storage report, and the non-mutating storage clean. Do not run `test_storage.py --apply`; do not stage pre-existing files.

- [x] **Step 3: Update durable memory**

Add one dated entry to `active-work.md` containing the task status, exact focused/task/SAXS evidence, storage dry-run result, and the unchanged scientific limitations; report the checkpoint hash in the handoff after commit.

- [x] **Step 4: Create the allowlist checkpoint**

After verification, run:

```powershell
python scripts/auto_commit.py --message "feat(saxs): add static and temperature detector figures" --files polynexus/core/saxs_engine/figure_detector.py polynexus/core/saxs_engine/figure_common.py polynexus/core/saxs_engine/figure_provider.py polynexus/core/saxs_engine/figure_static.py polynexus/core/saxs_engine/figure_temperature.py tests/test_saxs_detector_figure_modes.py docs/agent/tasks/2026-07-29-saxs-static-temperature-detector-figure.md docs/superpowers/specs/2026-07-29-saxs-static-temperature-detector-figure-design.md docs/superpowers/plans/2026-07-29-saxs-static-temperature-detector-figure.md docs/agent/memory/active-work.md
```

Expected: one checkpoint containing exactly the allowlisted changed files and
no pre-existing workspace artifacts; the resulting hash is reported in the
handoff.
