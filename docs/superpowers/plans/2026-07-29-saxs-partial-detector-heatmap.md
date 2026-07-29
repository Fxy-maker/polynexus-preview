# SAXS Partial Detector Heatmap Implementation Plan

Goal: Make partial static and temperature detector heatmaps renderable in the existing FigurePipeline without filling missing pixels.

Architecture: Add one explicit object-level opt-in for detector heatmaps. The shared renderer uses that opt-in to keep missing grid cells masked; the providers set it only on their detector objects. Existing complete-grid validation and all Manifest/Export orchestration remain unchanged.

Tech stack: Python, NumPy masked arrays, Matplotlib, immutable Figure contracts, pytest, repository verifier.

---

### Task 1: Add the RED renderer and production regressions

Files:
- Modify: tests/test_figure_render_plan_core.py
- Modify: tests/test_saxs_detector_figure_modes.py

- [x] Step 1: Add the renderer contract tests.

Add one test with detector coordinates (0,0), (1,0), (0,1) and
allow_partial_detector_grid=True; assert rendering succeeds and the QuadMesh
array contains one masked cell. Add a companion test with the same missing
cell and no opt-in; assert the existing complete-grid ValueError.

- [x] Step 2: Add static and temperature pipeline tests.

For each existing builder fixture, patch saxs_io.read_image to return
[[1.0, nan], [4.0, 16.0]], run only its detector definition through
FigurePipeline().run(...), and assert the matching Manifest entry is ready,
has exported png/svg assets, and persists
recipe.parameters.detector_projection_quality["0"].status =
partial_nonfinite.

- [x] Step 3: Run the RED tests.

Run:

    python -m pytest -q tests/test_figure_render_plan_core.py -k "partial_detector or strict_missing_grid"
    python -m pytest -q tests/test_saxs_detector_figure_modes.py -k "pipeline or manifest"

Expected: the new partial-render and pipeline assertions fail because the
renderer rejects the missing grid and the detector objects have no opt-in.

### Task 2: Implement the minimal explicit partial-grid path

Files:
- Modify: polynexus/core/figures/renderer.py
- Modify: polynexus/core/saxs_engine/figure_static.py
- Modify: polynexus/core/saxs_engine/figure_temperature.py

- [x] Step 1: Make the renderer conditional only on the exact opt-in.

In _render_heatmap(), retain duplicate-cell and empty-data errors. Change the
missing-cell check to:

    if not seen.all() and figure_object.get("allow_partial_detector_grid") is not True:
        raise ValueError("heatmap data does not form a complete regular grid")

Leave the existing matrix initialization and np.ma.masked_invalid(matrix)
call in place so omitted cells remain masked.

- [x] Step 2: Mark only the two detector providers as partial-safe.

Add allow_partial_detector_grid: True to the heatmap object returned by
_detector_heatmap_object() and to the temperature detector heatmap object.
Do not add the flag to the temperature evolution heatmap or any other Figure.

- [x] Step 3: Run the focused GREEN tests.

Run the two RED commands from Task 1 and then:

    python -m pytest -q tests/test_figure_render_plan_core.py tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_evidence_binding.py tests/test_run_figure_manifest.py

Expected: all focused tests pass and persisted detector recipe provenance is
unchanged.

### Task 3: Verify and checkpoint

Files:
- Modify: all files in the explicit allowlist in the task card.

- [x] Step 1: Run structured verification.

    python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-partial-detector-heatmap.md --changed --types

Record exact exit code and summaries; do not treat a timeout or no-summary
process exit as a pass.

- [x] Step 2: Run the fresh SAXS matrix and hygiene checks.

    python -m pytest -q tests/test_saxs_*.py
    python scripts/test_storage.py report --json
    python scripts/test_storage.py clean --older-than-hours 24
    git diff --check

The storage commands are dry-run only. Do not execute --apply.

- [x] Step 3: Update durable memory and audit the allowlist.

Add the task status, exact fresh evidence, limitations, and the unchanged
current-state.md/scratch exclusions to docs/agent/memory/active-work.md.
Review git diff --stat, git diff --check, and git status --short; do not
stage pre-existing files.

- [x] Step 4: Create the checkpoint.

    python scripts/auto_commit.py --message "fix(saxs): render partial detector figures" --files docs/agent/tasks/2026-07-29-saxs-partial-detector-heatmap.md docs/superpowers/specs/2026-07-29-saxs-partial-detector-heatmap-design.md docs/superpowers/plans/2026-07-29-saxs-partial-detector-heatmap.md polynexus/core/figures/renderer.py polynexus/core/saxs_engine/figure_static.py polynexus/core/saxs_engine/figure_temperature.py tests/test_figure_render_plan_core.py tests/test_saxs_detector_figure_modes.py docs/agent/memory/active-work.md

Expected: one allowlist-only local commit and no push, merge, cleanup, or
changes to the parallel workspace files.
