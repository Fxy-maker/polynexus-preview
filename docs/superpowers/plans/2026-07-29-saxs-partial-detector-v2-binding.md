# SAXS Partial Detector V2 Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make partial static and temperature SAXS detector Figures usable by the existing Reactive Figure V2 flow without repairing missing pixels.

**Architecture:** The detector providers will opt into their existing V2 adapter in their recipe.  Existing `FigurePipeline`, `LayoutResolver`, and `ReactiveFigureProjectService` then retain sparse finite cells as-is and provide the sidecar/editor/export lifecycle.

**Tech Stack:** Python 3.14, NumPy, pytest, PolyNexus FigurePipeline and plot runtime.

---

### Task 1: Prove V2 binding is absent for a partial detector Figure

**Files:**
- Modify: `tests/test_saxs_detector_figure_modes.py`

- [x] **Step 1: Write the failing regression**

```python
@pytest.mark.parametrize("mode", ["static", "temperature"])
def test_partial_detector_figure_is_reactive_v2_ready_and_publishable(
    monkeypatch, mode, tmp_path
):
    if mode == "static":
        engine = _static_engine(["static-0.edf"])
        builder = build_static_saxs_figure_definitions
        figure_id = "saxs.static.detector.2d"
    else:
        engine = _temperature_engine(["temperature-0.edf"])
        builder = build_temperature_figure_definitions
        figure_id = "saxs.temperature.detector.2d"
    monkeypatch.setattr(
        saxs_io,
        "read_image",
        lambda _path: (np.asarray([[1.0, np.nan], [4.0, 16.0]]), {}),
    )
    definition = next(item for item in builder(engine) if item.figure_id == figure_id)
    run_id = f"saxs-partial-v2-{mode}"
    manifest = FigurePipeline().run(
        output_root=tmp_path,
        run_id=run_id,
        technique="saxs",
        definitions=(definition,),
    )
    entry = manifest.figures[0]
    assert entry.capability_report["v2_runtime"] == "ready"
    service = ReactiveFigureProjectService(tmp_path)
    handle = service.load(run_id=run_id, figure_id=figure_id)
    node = handle.session.scene.node_by_id("detector-pattern-000")
    assert len(node.rectangles) == 3
    service.save_working(handle)
    published = service.publish(
        handle,
        profile=PublicationProfile(dpi=100, formats=("png",)),
    )
    assert len(published.assets) == 1
    assert published.assets[0].is_file()
```

- [x] **Step 2: Run RED**

Run: `python -m pytest -q tests/test_saxs_detector_figure_modes.py -k "partial_detector and v2"`

Expected: FAIL because the Manifest capability is `not_configured`.

### Task 2: Bind only detector recipes to existing V2 adapters

**Files:**
- Modify: `polynexus/core/saxs_engine/figure_static.py:917-996`
- Modify: `polynexus/core/saxs_engine/figure_temperature.py:911-1006`

- [x] **Step 1: Add explicit existing adapters**

```python
v2_adapter: str = "",
```

Add the preceding keyword-only parameter to static `_definition`, then add
this exact recipe member beside the existing `parameters` member:

```python
**({"v2_adapter": v2_adapter} if v2_adapter else {}),
```

At the existing static detector `_definition` call, add:

```python
v2_adapter="saxs_static",
```

The existing temperature detector recipe receives this key:

```python
recipe = {
    "module": "polynexus.core.saxs_engine.figure_temperature",
    "function": "build_temperature_figure_definitions",
    "inputs": {"source_paths": [frame.source_path for frame in frames]},
    **_selection_recipe(selection, axis),
    "parameters": parameters,
    "v2_adapter": "temperature_saxs",
}
```

Place each key in the detector Figure recipe alongside the existing module,
function, input, selection, and provenance fields.  Do not add values to the
sparse detector data source or relax other Figure paths.

- [x] **Step 2: Run GREEN**

Run: `python -m pytest -q tests/test_saxs_detector_figure_modes.py -k "partial_detector and v2"`

Expected: `2 passed`.

### Task 3: Verify the affected production boundaries and checkpoint

**Files:**
- Modify: `docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md`
- Modify: `docs/agent/memory/active-work.md`

- [x] **Step 1: Run focused regression matrix**

Run: `python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_reactive_figure_project_service.py tests/test_reactive_figure_layout.py`

Expected: exit code 0.

- [x] **Step 2: Run structured verification and SAXS matrix**

Run: `python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md --changed --types`

Run: `python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })`

Expected: both exit code 0.

- [x] **Step 3: Run hygiene checks**

Run: `python scripts/test_storage.py report --json`

Run: `python scripts/test_storage.py clean --older-than-hours 24`

Run: `git diff --check`

Expected: storage commands remove nothing; diff check exits 0.

- [x] **Step 4: Update durable evidence and create allowlist checkpoint**

Run:

```powershell
python scripts/auto_commit.py `
  --message "fix(saxs): bind partial detector figures to v2" `
  --files docs/agent/tasks/2026-07-29-saxs-partial-detector-v2-binding.md docs/superpowers/specs/2026-07-29-saxs-partial-detector-v2-binding-design.md docs/superpowers/plans/2026-07-29-saxs-partial-detector-v2-binding.md docs/agent/memory/active-work.md polynexus/core/saxs_engine/figure_static.py polynexus/core/saxs_engine/figure_temperature.py tests/test_saxs_detector_figure_modes.py
```

Expected: one local-only allowlist checkpoint; no unrelated staged or
untracked files are included.
