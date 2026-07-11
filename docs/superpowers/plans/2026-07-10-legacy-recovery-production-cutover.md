# Legacy Recovery And Production Figure Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, honest recovery path for historical figure files and make the unified FigureDefinition/Manifest pipeline the only formal production output path for SAXS, WAXS, DSC, IR, and NMR.

**Architecture:** Recursive file discovery moves behind a dedicated legacy recovery service and can never populate the active-run Manifest or normal gallery. Recovery candidates are classified from concrete evidence as rebuildable, partially repairable, or static-only; rebuild and repair create new immutable runs, while static import creates a portable recovery package outside `runs/`. A shared production publisher owns run IDs, profile selection, Manifest activation, and the compatibility `{figure_id: primary_asset}` result returned by `BaseEngine.plot()`.

**Tech Stack:** Python dataclasses and enums, pathlib, JSON, shutil, Matplotlib-backed unified figure pipeline, PySide6 viewer surface, pytest, Ruff, AST-based CI gates.

---

## File Responsibility Map

- `polynexus/core/figures/legacy_recovery.py`: evidence model, recursive legacy discovery, classification, static import, rebuild callback, and partial-document repair dispatch.
- `polynexus/core/figures/recovery_pipeline.py`: copy and normalize a valid historical FigureDocument plus data snapshots into a new immutable run, regenerate a complete profile, resolve capabilities, and activate one Manifest.
- `polynexus/gui/legacy_figure_recovery_service.py`: map recovery candidates to legacy-only gallery entries without sharing normal-gallery discovery.
- `polynexus/gui/main_window_figure_mixin.py`: explicit recovery-view launch method only; normal `_populate_plots()` remains Manifest-only.
- `polynexus/gui/main_window.py`: add the user-invoked “Historical figure recovery” toolbar action.
- `polynexus/core/figures/production.py`: create immutable run IDs, call `FigurePipeline`, and return primary formal asset paths for engine/result compatibility.
- `polynexus/core/engine.py`: shared `publish_figure_definitions()` implementation used by all migrated engines.
- `polynexus/core/{saxs,waxs,dsc,ir,nmr}.py`: production `plot()` methods call only the shared publisher.
- `polynexus/core/saxs_engine/figure_provider.py`: fill the remaining static/strain SAXS provider gap so production cutover never falls back to direct writers.
- `scripts/quality_gate.py`: reject recursive discovery outside the recovery module, production calls to legacy direct writers, technique-level format choice in migrated wrappers/providers, and direct formal writes outside shared export internals.

## Task 1: Discover And Classify Historical Figure Projects

**Files:**

- Create: `polynexus/core/figures/legacy_recovery.py`
- Create: `tests/test_legacy_figure_recovery.py`
- Modify: `polynexus/core/figures/__init__.py`
- Modify: `polynexus/gui/plot_gallery_service.py`

- [ ] Write failing tests that create three isolated historical folders and assert exact classifications:

```python
def test_legacy_discovery_classifies_rebuildable_partial_and_static(tmp_path):
    # rebuildable/recovery_context.json declares technique, recipe, and existing source_paths
    # partial/figure.pnfig.json has resolvable data_sources but no active manifest
    # static/figure.png has no document or data evidence
    candidates = LegacyFigureRecoveryService(tmp_path).discover()
    assert {item.candidate_id: item.kind for item in candidates} == {
        "rebuildable": LegacyRecoveryKind.REBUILDABLE,
        "partial": LegacyRecoveryKind.PARTIALLY_REPAIRABLE,
        "static": LegacyRecoveryKind.STATIC_ONLY,
    }
```

- [ ] Run the test and verify it fails because `LegacyFigureRecoveryService` does not exist.

- [ ] Implement immutable contracts:

```python
class LegacyRecoveryKind(str, Enum):
    REBUILDABLE = "rebuildable"
    PARTIALLY_REPAIRABLE = "partially_repairable"
    STATIC_ONLY = "static_only"

@dataclass(frozen=True)
class LegacyFigureCandidate:
    candidate_id: str
    root: Path
    kind: LegacyRecoveryKind
    technique: str
    title: str
    assets: dict[str, Path]
    document_path: Path | None
    data_paths: tuple[Path, ...]
    recipe: dict[str, object]
    reason_code: str
    suggested_action: str
```

`discover()` must recurse only below the explicitly supplied legacy root, skip every `runs/`, `.staging`, and `legacy_recovery/` subtree, group sibling SVG/PNG/PDF/JPEG assets by logical stem, and resolve documents/data without writing files. `recovery_context.json` is rebuildable only when it contains a supported technique, non-empty recipe module/function, and every declared source path exists. A valid document with resolvable data is partially repairable. Everything else with a rendered asset is static-only.

- [ ] Move the implementation of recursive `collect_plot_figure_paths()` behind the recovery module. Keep a deprecated compatibility wrapper in `plot_gallery_service.py` that calls the recovery scanner, but no normal-gallery code may import it.

- [ ] Add a test that creates an active run plus unrelated legacy files, calls `discover()`, and asserts the active Manifest bytes and active normal-gallery entries are unchanged.

- [ ] Run `tests/test_legacy_figure_recovery.py tests/test_plot_gallery_service.py tests/test_main_window_figure_mixin.py` and commit `feat: classify historical figure recovery candidates`.

## Task 2: Recover Without Rewriting Historical Files

**Files:**

- Create: `polynexus/core/figures/recovery_pipeline.py`
- Modify: `polynexus/core/figures/legacy_recovery.py`
- Modify: `tests/test_legacy_figure_recovery.py`
- Create: `tests/test_figure_recovery_pipeline.py`

- [ ] Write a failing static-import test. `import_static(candidate, output_root)` must copy the selected rendered asset to `output_root/legacy_recovery/<candidate_id>/background/`, write a portable `figure.pnfig.json` with `mode="static_background"`, `category="legacy"`, `vector_fidelity="raster_embedded"` for raster sources, and write `recovery_record.json`. It must not create or modify `active_run.json` or any `runs/<run_id>/figure_manifest.json`.

- [ ] Implement static import with `create_static_figure_document()`, then replace the generated absolute background path with a package-relative POSIX path and `path_kind="package_relative"` before the atomic JSON write.

- [ ] Write a failing partial-repair test from a historical version-2 document and CSV. Call:

```python
manifest = FigureRecoveryPipeline(output_root).recover_document(
    run_id="recovered-run",
    technique="ir",
    document_path=legacy_document,
    data_root=legacy_root,
    profile_id="paper_complete",
)
```

Assert the old files are byte-for-byte unchanged, the new document/data paths are run-relative, SVG/600-DPI PNG/PDF are complete, capability is object editing, and only the new run is activated.

- [ ] Implement recovery through a new staging run. Copy data to `figures/<figure_id>/data/`, recompute SHA-256, rewrite each data source to `path_kind="run_relative"`, increment/reset the recovered document to revision 1 in the new run, build one RenderPlan, export and inspect one complete asset group, resolve capability once, write Manifest/run metadata, rename staging, then atomically activate.

- [ ] Write a failing rebuildable test whose `definition_factory(candidate)` returns a real `FigureDefinition`; `LegacyFigureRecoveryService.rebuild()` must call `FigurePipeline.run()` with a caller-supplied new run ID and must reject missing factories instead of guessing how to rerun scientific analysis.

- [ ] Run recovery, pipeline, exporter, inspector, and Manifest tests; commit `feat: recover legacy figures into isolated projects`.

## Task 3: Add An Explicit Legacy Recovery View

**Files:**

- Create: `polynexus/gui/legacy_figure_recovery_service.py`
- Modify: `polynexus/gui/main_window_figure_mixin.py`
- Modify: `polynexus/gui/main_window.py`
- Modify: `polynexus/gui/main_window_retranslate_mixin.py`
- Modify: `polynexus/gui/i18n.py`
- Create: `tests/test_legacy_figure_recovery_service.py`
- Modify: `tests/test_main_window_figure_mixin.py`

- [ ] Write failing service tests that map candidates to `FigureGalleryEntry` rows with `category="legacy"`, visible classification/reason text, asset-only candidates forced to `static_background`, and document/data candidates retaining their honest recovery action. No row may have `run_id`, `published_revision`, or active Manifest capability fields.

- [ ] Implement `build_legacy_recovery_gallery_entries(root)` using only `LegacyFigureRecoveryService.discover()`; do not call `build_active_manifest_gallery_entries()` and do not activate a run.

- [ ] Add a “Historical figure recovery” button beside “Open Current Figure”. `_open_legacy_recovery_view()` creates a separate `ChartViewer`, loads only legacy recovery entries, titles the window as a recovery surface, and never replaces `_chart_gallery` or `_current_figure_path`.

- [ ] Add Chinese/English keys for the button, recovery window title, classifications, and empty state. Add a retranslation assertion.

- [ ] Run main-window figure/retranslate/viewer and recovery-service tests; commit `feat: add explicit historical figure recovery view`.

## Task 4: Add The Shared Production Publisher

**Files:**

- Create: `polynexus/core/figures/production.py`
- Create: `tests/test_figure_production.py`
- Modify: `polynexus/core/figures/__init__.py`
- Modify: `polynexus/core/engine.py`
- Modify: `tests/test_core.py`

- [ ] Write a failing publisher test with two definitions. Assert one generated run ID, one `paper_complete` Manifest, one active pointer, and a compatibility mapping whose values are the absolute SVG role paths from that exact Manifest.

- [ ] Implement:

```python
@dataclass(frozen=True)
class FigureProductionResult:
    run_id: str
    manifest: RunFigureManifest
    primary_assets: dict[str, str]

class FigureProductionPublisher:
    def publish(self, *, output_root, technique, definitions,
                profile_id="paper_complete", run_id=None) -> FigureProductionResult:
        resolved_run_id = run_id or new_immutable_run_id(technique)
        manifest = FigurePipeline().run(...)
        # ready entries map to SVG, then PNG, then PDF, then preview by asset role
```

Use UTC microseconds plus a UUID suffix for collision-resistant immutable IDs; validate through the existing pipeline rather than duplicating run-ID rules.

- [ ] Add `BaseEngine.publish_figure_definitions(output_dir, definitions=None, profile_id="paper_complete")`. It calls `self.build_figure_definitions()` when definitions are omitted, updates `result.metadata["figure_run_id"]` and `result.metadata["figure_manifest"]`, and returns the compatibility primary-asset mapping.

- [ ] Add a default `build_figure_definitions()` contract that raises `NotImplementedError` so a migrated engine can never silently fall back to legacy writers.

- [ ] Run production, core engine, pipeline, Manifest, and five-technique uniformity tests; commit `feat: add shared production figure publisher`.

## Task 5: Close SAXS Provider Gaps And Switch Five Engines

**Files:**

- Modify: `polynexus/core/saxs_engine/figure_provider.py`
- Modify: `polynexus/core/saxs.py`
- Modify: `polynexus/core/waxs.py`
- Modify: `polynexus/core/dsc.py`
- Modify: `polynexus/core/ir.py`
- Modify: `polynexus/core/nmr.py`
- Create: `tests/test_engine_figure_production_cutover.py`
- Modify: `tests/test_saxs_temperature_figure_provider.py`

- [ ] Write failing SAXS provider tests for static single/batch and strain states. Required minimum definitions are per-frame scattering profiles plus a series waterfall for multi-frame inputs; temperature retains its existing per-frame/waterfall/dashboard/heatmap definitions. Every object must reference portable numerical snapshots.

- [ ] Implement `build_saxs_figure_definitions(engine_state)` as the one SAXS provider entry point. Dispatch temperature to the existing builder; otherwise build profiles from `_q_list/_I_list` or analyzed result arrays, and add a strain/ordered-series waterfall when more than one frame exists. Do not introduce output paths, extensions, DPI, or save calls.

- [ ] Write parameterized failing cutover tests for SAXS/WAXS/DSC/IR/NMR engines. Stub each `build_figure_definitions()` with one real definition, monkeypatch every imported legacy writer to raise, call `plot(tmp_path)`, and assert a complete active Manifest plus returned SVG mapping. The test must fail if `generate_all_figures`, `generate_temperature_figures`, `generate_strain_figures`, or a direct `fig_*` writer is invoked.

- [ ] Replace every migrated engine `plot()` body with:

```python
def plot(self, output_dir: str = "") -> dict[str, str]:
    if not self.build_figure_definitions():
        self.log("No figure definitions available")
        return {}
    output_root = output_dir or <technique output default>
    figures = self.publish_figure_definitions(output_root)
    for path in figures.values():
        self.log(f"  Figure saved: {path}")
    return figures
```

Compute definitions once and pass them explicitly to avoid provider recomputation. Remove legacy writer imports from the five wrapper modules. Specialized submodules that have analysis results but no special series provider publish their standard per-result definitions; they do not call old output modules.

- [ ] Run provider, engine, GUI worker, CLI, and five-technique pipeline tests; commit `feat: cut production engines over to unified figure pipeline`.

## Task 6: Disable Legacy Formal Writers And Enforce CI Boundaries

**Files:**

- Modify: `scripts/quality_gate.py`
- Modify: `tests/test_quality_gate.py`
- Modify: `polynexus/core/{saxs,waxs,dsc,ir,nmr}_engine/__init__.py`
- Modify: `polynexus/utils/config.py`
- Modify: `tests/test_config.py`

- [ ] Add failing AST gate tests that reject migrated wrapper calls/imports of `generate_all_figures`, `generate_temperature_figures`, `generate_strain_figures`, or direct `fig_*` writers; reject `fig_format`, `figure_format`, and publication DPI access in migrated wrappers/providers; reject `rglob`, recursive `glob("**")`, and `os.walk` anywhere except `legacy_recovery.py`.

- [ ] Extend `scan_figure_lifecycle_sources()` to scan all five wrapper modules, providers, normal GUI gallery files, and shared figure core. Formal `savefig` remains allowed only in `export_service.py`; recovery copies existing assets but never formally renders outside the shared exporter.

- [ ] Stop exporting legacy `generate_all_figures` functions from migrated engine package `__init__.py` files. Keep old output modules importable only by explicit fully-qualified legacy/recovery tests; add module docstrings stating they are disabled from production.

- [ ] Replace `GlobalConfig.figure_format` and `figure_dpi` with `figure_output_profile="paper_complete"`. During config loading, consume old keys only as ignored migration inputs and never propagate them to technique configurations. Retain scientific plot-content settings.

- [ ] Run the quality gate against real sources and mutation fixtures, config tests, and all engine/provider tests; commit `test: enforce the single production figure pipeline`.

## Task 7: Final Requirement Audit And Branch Verification

**Files:**

- Create: `docs/superpowers/reports/2026-07-10-unified-figure-lifecycle-audit.md`
- Modify only if audit finds a concrete gap: the exact affected source/test file.

- [ ] Re-read the umbrella specification and produce a table mapping every acceptance criterion to implementation files, tests, and fresh command evidence. Explicitly distinguish implemented behavior from manual Word/WPS/LaTeX checks.

- [ ] Run focused recovery, provider, production, gallery/editor, and quality-gate suites with unique `--basetemp` directories.

- [ ] Run the complete pytest suite, Ruff on every lifecycle/core/provider/GUI file changed by Waves 1–5, `python -m compileall`, `scan_figure_lifecycle_sources(Path('.'))`, and `git diff --check`.

- [ ] Run one real five-technique smoke that produces complete `paper_complete` groups and one recovery smoke for each classification. Record NMR instrument-data availability honestly; synthetic/provider-level coverage does not substitute for absent external instrument fixtures.

- [ ] Commit the audit and any verified gap fixes as `docs: audit unified figure lifecycle completion`.

## Plan Self-Review

- Spec coverage: Tasks 1–3 cover explicit discovery, classification, static honesty, partial repair, rebuild-to-new-run, and isolation from active manifests. Tasks 4–6 cover one global profile, five production engine cutovers, removal/disablement of legacy formal entry points, and CI boundaries. Task 7 covers every acceptance criterion and the manual-workflow boundary.
- Placeholder scan: the plan contains no deferred implementation placeholders. Rebuildable recovery deliberately requires a supplied scientific definition factory because guessing analysis-result reconstruction would violate the design’s truth model.
- Type consistency: `LegacyRecoveryKind`, `LegacyFigureCandidate`, `FigureRecoveryPipeline.recover_document()`, `FigureProductionPublisher.publish()`, and `BaseEngine.publish_figure_definitions()` retain the same names and argument roles across tasks.
- Scope control: Save-As-Copy lineage and reanalysis style inheritance remain outside this Wave 5 cutover because the approved Wave 4 plan explicitly deferred only copy lineage and the active goal prioritizes recovery plus single-pipeline production closure. They will be reported as separate post-goal work if the final umbrella audit treats them as blocking.

## Execution Handoff

This plan is saved for inline execution with `superpowers:executing-plans`, matching the user’s instruction to continue the active goal without subagent delegation.
