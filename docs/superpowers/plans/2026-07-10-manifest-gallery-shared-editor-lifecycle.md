# Manifest Gallery And Shared Editor Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the normal gallery read only the active run manifest, open manifest-backed figures in object mode through the shared RenderPlan, and separate Save Edits from atomic complete-profile Publish.

**Architecture:** The manifest is the only normal gallery index and every gallery entry carries run/document/capability/revision context. Working saves and publications are immutable revision directories whose atomic manifest update is the commit point; the editor resolves run-relative data through `FigureRenderPlanBuilder` and renders through `MatplotlibFigureRenderer` instead of reinterpreting the document independently.

**Tech Stack:** Python, dataclasses, JSON, Matplotlib Figure API, PySide6, pytest, Ruff.

---

## Scope Boundary

Included:

- read APIs for active run manifests
- manifest-backed gallery entries with no directory recursion
- multi-panel/object mode editor entry based on the shared capability report
- shared RenderPlan editor first screen and redraw
- working revision save with a new document and preview only
- complete SVG/600-DPI PNG/PDF publication as a new immutable publication group
- editor Save Edits and Publish hooks

Deferred to wave 5:

- legacy discovery/recovery surface
- deletion of legacy writers
- save-as-copy lineage

## Tasks

### Task 1: Read Active Manifests And Build Gallery Entries

**Files:**

- Modify: `polynexus/core/figures/manifest.py`
- Modify: `polynexus/gui/plot_gallery_service.py`
- Modify: `polynexus/gui/main_window_figure_mixin.py`
- Modify: `tests/test_run_figure_manifest.py`
- Modify: `tests/test_plot_gallery_service.py`
- Modify: `tests/test_main_window_figure_mixin.py`

- [ ] Write failing tests for `FigureManifestEntry.from_payload`, `RunFigureManifest.from_payload`, `RunFigureManifestRepository.read_manifest()`, and `read_active_manifest()`.
- [ ] Write a failing gallery test that creates a complete pipeline run plus unrelated historical files, calls `build_active_manifest_gallery_entries(output_root)`, and asserts only manifest figures appear with run root, document path, capability report, revision, preview, SVG, PNG, and PDF.
- [ ] Extend `FigureGalleryEntry` with defaulted `output_root`, `run_root`, `run_id`, `document_path`, `capability_report`, `publication_status`, `working_revision`, `published_revision`, `status`, and `error` fields.
- [ ] Implement active-manifest entry building with run-root containment checks and role-based assets. Map `editing_mode="object"` to `FIGURE_STATE_OBJECT`; never inspect sibling files.
- [ ] Change `_populate_plots()` to call only `build_active_manifest_gallery_entries(self._output_dir)`. An absent manifest produces an empty normal gallery; it does not invoke `rglob`.
- [ ] Run `tests/test_run_figure_manifest.py tests/test_plot_gallery_service.py tests/test_main_window_figure_mixin.py` and commit `feat: drive figure gallery from active manifests`.

### Task 2: Add Immutable Working Save And Publication Service

**Files:**

- Create: `polynexus/core/figures/project_service.py`
- Create: `tests/test_figure_project_service.py`
- Modify: `polynexus/core/figures/__init__.py`

- [ ] Write a failing test that starts from a pipeline run, changes one object style, calls `save_working()`, and asserts: working revision advances, published revision stays, old formal asset paths/bytes stay unchanged, document and preview paths move under `revisions/r0002/`, and publication status is `unpublished_changes`.
- [ ] Write a failing publish test that calls `publish()` and asserts all four asset roles move atomically to `publications/r0002/assets/`, published revision becomes 2, PNG is 600 DPI, and the document export pointers match the manifest.
- [ ] Write a failure test with an exporter that raises; assert the manifest and previous publication paths remain byte-for-byte unchanged.
- [ ] Implement `FigureProjectService(output_root)` with `save_working(run_id, figure_id, document)` and `publish(run_id, figure_id)`. New files are written before one atomic `figure_manifest.json` replacement; old revisions/publications are never overwritten.
- [ ] Resolve capabilities after each operation with the existing shared resolver.
- [ ] Run focused plus pipeline/export regressions and commit `feat: add figure working and publication revisions`.

### Task 3: Open Manifest Entries Through The Shared RenderPlan

**Files:**

- Modify: `polynexus/core/figure_document.py`
- Modify: `polynexus/gui/figure_window_service.py`
- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_generated_document_mixin.py`
- Modify: `tests/test_figure_document.py`
- Modify: `tests/test_figure_window_service.py`
- Modify: `tests/test_chart_editor_generated_document_mixin.py`

- [ ] Make `load_figure_document()` accept a direct `*.pnfig.json` path in a failing unit test.
- [ ] Add a failing editor-entry test for a four-panel manifest entry with object capability; assert it is not forced static and its explicit document path is used.
- [ ] Add a failing generated-document mixin test whose fake entry supplies `run_root` and `document_path`; assert `_build_generated_figure_document()` calls `FigureRenderPlanBuilder(run_root).build(document_path, document)` and `MatplotlibFigureRenderer.render()`.
- [ ] Trust the manifest capability report for manifest entries and remove recipe-name/multi-panel filename fallbacks from that path. Legacy entries retain existing fallback behavior.
- [ ] In ChartEditor, load `entry.document_path` directly while keeping `entry.preview_path`/SVG as the source display path.
- [ ] In manifest mode, build every redraw from the in-memory FigureDocument with the shared plan builder and renderer. Store the resolved plan on the editor for capability/status inspection.
- [ ] Run document/window/editor mixin tests and commit `feat: open manifest figures with shared render plans`.

### Task 4: Connect Editor Save Edits And Publish

**Files:**

- Modify: `polynexus/gui/widgets/chart_editor.py`
- Modify: `polynexus/gui/widgets/chart_editor_save_mixin.py`
- Modify: `tests/test_chart_editor_save_mixin.py`
- Modify: `tests/test_chart_editor.py`

- [ ] Add failing mixin tests: manifest Save Edits calls `FigureProjectService.save_working` and does not call `savefig`; Publish calls `publish`, refreshes entry/document/source preview, and emits the new preview path.
- [ ] Add a `Publish complete assets` button next to Save Edits. Keep SVG/PNG buttons as export-copy actions that do not alter publication revision.
- [ ] Route manifest entries through the project service; keep legacy/static save behavior unchanged.
- [ ] After save/publish, replace `_source_entry_context`, `_figure_document`, `_source_path`, target label, and capability banner from the returned manifest-backed entry.
- [ ] Run save mixin, focused ChartEditor, figure-window, and gallery tests and commit `feat: connect editor save and publish lifecycle`.

### Task 5: Quality Gates And Wave Verification

**Files:**

- Modify: `scripts/quality_gate.py`
- Modify: `tests/test_quality_gate.py`

- [ ] Add tests rejecting `rglob`/recursive filesystem discovery in `main_window_figure_mixin.py` and rejecting a second editor capability decision for manifest entries.
- [ ] Run all lifecycle/gallery/window/editor/project tests.
- [ ] Run Ruff on changed core/GUI/test files, the lifecycle boundary scan, and `git diff --check`.
- [ ] Run one end-to-end test: pipeline run → gallery entry → save working revision → publish → gallery reload. Assert gallery/editor capability agreement and complete r0002 formal assets.
- [ ] Commit `test: enforce manifest gallery and editor lifecycle`.

## Plan Self-Review

The plan maps every wave 4 acceptance requirement to a testable commit: manifest-only discovery, one capability result, shared first-screen renderer, separate working/published revisions, complete atomic publication, and gallery refresh. Legacy recovery and removal remain isolated in wave 5. Public names and revision semantics match the already implemented contracts.

## Execution Handoff

Execute inline with `superpowers:executing-plans`; do not delegate without explicit user authorization.
