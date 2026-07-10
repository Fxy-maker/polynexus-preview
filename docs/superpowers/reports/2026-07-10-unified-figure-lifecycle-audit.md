# Unified Figure Lifecycle Completion Audit

**Date:** 2026-07-10  
**Branch:** `codex/unified-figure-lifecycle-foundation`  
**Specification:** `docs/superpowers/specs/2026-07-10-unified-figure-artifact-lifecycle-design.md`  
**Result:** The automated acceptance boundary is implemented. External Word/WPS/LaTeX insertion remains a manual compatibility check, as required by the approved specification.

## Executive Result

SAXS, WAXS, DSC, IR, and NMR now share one `FigureDefinition` contract and one formal production publisher. A production call creates an immutable run, portable numerical snapshots, a normalized FigureDocument, one shared RenderPlan, a complete `paper_complete` asset group (`preview.png`, `figure.svg`, 600-DPI `figure.png`, and `figure.pdf`), one capability report, and one authoritative run Manifest.

The normal gallery is Manifest-only. Manifest-backed editor entries trust the same capability report and use the shared RenderPlan builder and renderer. Save Edits creates a working revision without replacing the last complete publication; Publish stages and atomically commits the complete formal asset group. Historical discovery is available only through an explicit recovery surface and never populates the active Manifest automatically.

Legacy rendering modules remain importable by fully qualified module path for recovery/regression tests, but their figure writers are not exported by the technique packages and are not called by production wrappers. AST quality gates prevent migrated wrappers/providers from reintroducing legacy writers, direct `savefig`, hard-coded publication extensions, technique-local format/DPI selection, or recursive normal-gallery discovery.

## Acceptance-Criteria Traceability

| Approved acceptance criterion | Implementation evidence | Automated evidence | Status |
|---|---|---|---|
| All five techniques implement the same FigureDefinition contract | `polynexus/core/figures/contracts.py`; five `*_engine/figure_provider.py` modules; five engine `build_figure_definitions()` methods | `test_five_technique_figure_pipeline.py`, provider suites, `test_engine_figure_production_cutover.py` | Implemented |
| Every run selects exactly one global output profile | `polynexus/core/figures/profiles.py`; `pipeline.py`; `production.py`; `GlobalConfig.figure_output_profile` | `test_figure_contracts.py`, `test_figure_production.py`, `test_config.py` | Implemented |
| Every ready figure satisfies the selected profile | `export_service.py`; `inspector.py`; `pipeline.py` | `test_figure_export_service.py`, `test_figure_pipeline.py`, five-technique smoke | Implemented |
| Every ready figure has a portable FigureDocument | `document_builder.py`; run-relative path validation in `manifest.py` | `test_figure_document_builder.py`, `test_run_figure_manifest.py`, pipeline suites | Implemented |
| Object-mode ready figures have validated numerical snapshots for every data-bound object | `validation.py`; `data_writer.py`; `render_plan.py` | `test_figure_data_writer.py`, `test_figure_render_plan_core.py`, provider/pipeline suites | Implemented |
| Static-background figures have portable background state and honest fidelity metadata | `legacy_recovery.py`; static recovery packages remain outside active runs and record `vector_fidelity="raster_embedded"` | `test_static_import_creates_portable_recovery_package_without_activation` | Implemented without false active-run promotion |
| Every run has one authoritative Manifest | `manifest.py`; `pipeline.py`; `production.py` | `test_run_figure_manifest.py`, `test_figure_production.py`, production cutover suite | Implemented |
| Gallery reads the Manifest rather than guessing from files | `plot_gallery_service.py`; `main_window_figure_mixin.py`; recursive discovery removed from `ChartGallery` | gallery/mixin suites; updated persistence tests; AST recursion gates | Implemented |
| Preview, editor, and published assets share one RenderPlan | `render_plan.py`; `renderer.py`; `export_service.py`; manifest editor rendering path | render-plan, export, editor-render, and cross-technique suites | Implemented structurally |
| Gallery badge and editor mode always agree | `capabilities.py`; Manifest capability report passed through gallery and `figure_window_service.py` | `test_figure_window_service.py`; capability-boundary AST test | Implemented |
| Standard single-axis data figures enter object editing | IR/WAXS/DSC/NMR/SAXS profile definitions plus shared capability resolver | five provider suites and five-technique smoke assert `editing_mode="object"` | Implemented |
| Multi-panel figures use the formal layout model and become object-editable without filename exceptions | `contracts.py`; SAXS temperature parameters/heatmap providers; shared renderer/editor | `test_saxs_temperature_figure_provider.py`, `test_cross_technique_figure_pipeline.py`, editor suites | Implemented for supported layouts/objects |
| Save Edits and Publish have distinct revisions | `project_service.py`; `chart_editor_save_mixin.py` | `test_figure_project_service.py`, `test_chart_editor_save_mixin.py` | Implemented |
| SVG, PNG, and PDF publish atomically | `export_service.py`; `project_service.py`; staging and Manifest replacement | exporter failure and project publish failure tests; PNG inspection at 600 DPI | Implemented |
| Current runs never mix with historical files; recovery is explicit and honest | `legacy_recovery.py`; `recovery_pipeline.py`; `legacy_figure_recovery_service.py`; separate toolbar/view | legacy discovery/static/rebuild/partial-repair suites; normal gallery isolation tests | Implemented |
| Only one formal production figure-output pipeline remains | `FigureProductionPublisher`; five wrapper `plot()` methods; legacy package exports removed; AST quality gates | `test_engine_figure_production_cutover.py`, `test_quality_gate.py`, real boundary scan | Implemented |

## Fresh Verification Evidence

| Verification | Result |
|---|---|
| Core lifecycle, recovery, provider, production, and quality-gate suites | `98 passed` |
| Manifest gallery and ChartEditor suites selected from the full test tree | `306 passed`, `1276 deselected` |
| Five-technique complete-profile smoke plus all three recovery classifications | `5 passed` |
| Task 6 engine/provider/legacy-module regression | `146 passed`, `4` legacy-writer font warnings |
| Complete repository suite after audit fixes | `1563 passed`, `19 skipped`, `4 warnings`, `0 failed` |
| Local quality gate (`compileall`, focused tests, whitespace) | `260 passed`; all selected checks passed |
| Strict Ruff on shared lifecycle core, all five providers, gallery/recovery/editor services, and quality gate | All checks passed |
| Broad Ruff on all Wave lifecycle/core/provider/GUI Python changes with documented historical exclusions | All checks passed |
| `scan_figure_lifecycle_sources(Path('.'))` | `[]` |

The complete-suite skips are deliberate and visible:

- IR SPA and IR temperature-series fixtures are not present under `测试数据/IR` in this worktree.
- NMR FID/JDF instrument fixtures are not present under `测试数据/NMR` in this worktree.
- Provider-level and synthetic NMR coverage passes, but it is not reported as a substitute for absent instrument-data validation.

The four warnings come only from fully qualified legacy SAXS writer tests requesting Arial glyphs for two Chinese characters. Shared production exports use the unified font policy and are covered independently.

## Production And Recovery Smokes

The five-technique smoke constructs representative real analysis-result objects, invokes each real technique provider, and runs every definition through `FigurePipeline`. For each technique it verifies:

- `output_profile == "paper_complete"`
- one ready Manifest entry
- exact asset roles `preview`, `svg`, `png`, and `pdf`
- object editing capability
- 600-DPI publication PNG
- document export pointers identical to the Manifest asset group

Recovery smoke coverage verifies:

- `rebuildable`: requires an explicit Definition factory and creates a new immutable active run
- `partially_repairable`: copies and rehashes data, rewrites portable paths, republishes a complete profile, and leaves historical bytes unchanged
- `static_only`: creates a package-relative static-background project with `raster_embedded` fidelity outside `runs/` and does not change `active_run.json`

## Manual Word, WPS, And LaTeX Boundary

Automatic insertion into external document applications is explicitly out of scope. The generated roles are ready for manual compatibility checks, but those checks were not executed in this headless audit.

| Manual check | Expected asset | Audit state |
|---|---|---|
| Insert into a current Word version | `figure.svg` first; `figure.png` fallback | Pending manual application check |
| Insert into WPS | `figure.svg` where supported; 600-DPI `figure.png` fallback | Pending manual application check |
| LaTeX `\includegraphics` and PDF inspection | `figure.pdf` | Pending manual TeX/application check |
| Verify copied path/label matches role | Manifest-backed asset panel | UI structure covered automatically; OS/application clipboard workflow remains manual |

PDF is therefore retained as the LaTeX/publication-vector role. It is not used as the editor source or primary gallery preview.

## Non-Blocking Follow-Ups

The umbrella design describes two later product extensions that are not part of the approved completion criteria for this goal and were explicitly deferred in the Wave 5 plan:

- Save As Copy with a new semantic figure ID and lineage metadata
- compatible style inheritance across reanalysis runs

Additional convenience actions such as generating a LaTeX `\includegraphics{}` snippet can be layered onto the Manifest asset panel without changing the completed lifecycle contract.

## Final Audit Decision

The repository satisfies the approved automated acceptance criteria for the unified figure artifact lifecycle. The implementation has one production truth path and explicit historical recovery. Remaining work is limited to external application compatibility checks and separately scoped copy/reanalysis enhancements; neither reopens technique-owned formal output behavior.
