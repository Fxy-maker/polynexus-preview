# DSC Lifecycle Closure Design

## Goal

 Close the remaining DSC acceptance boundary for `dsc.standard`,
 `dsc.isothermal`, and `dsc.nonisothermal` by proving that one completed
 analysis can move through the shared figure lifecycle: publication provider,
 active Manifest/Gallery, editable working revision, complete publication,
 export provenance, and history restore.

## Scope and non-goals

 The slice covers the product connections and regression evidence needed by
 the existing DSC providers. It reuses the current `FigureProductionPublisher`,
 `RunFigureManifestRepository`, `build_active_manifest_gallery_entries`,
 `FigureProjectService`, and export-context helpers.

 It does not change DSC calculations, evidence thresholds, provider role
 assignment, input readers, or the normal manifest-only gallery policy. It also
 does not claim restarted-GUI visual or scientific release sign-off; those stay
 explicit acceptance gates.

## Design

 Each DSC mode is represented by a completed provider DTO. The test publishes
 its definitions into an isolated output root, reads the active manifest, and
 asserts that Gallery entries preserve the provider's Main/SI/diagnostic roles
 and run context. The first entry is loaded as a document, saved as one
 working revision, and published through `FigureProjectService`; the manifest
 must retain the run and figure identity while changing revision state.

 The output root is copied through `copy_export_bundle_sections`, and the
 export manifest is written with `figure_runs` and `active_figure_run` paths.
 A small Qt history harness restores a record carrying the DSC technique,
 submodule, source path, and output directory, then asserts that the restored
 MainWindow repopulates the same active manifest Gallery. This keeps GUI code
 responsible only for routing and leaves lifecycle semantics in shared core
 services.

## Failure and fallback boundary

 Provider-level diagnostic-only definitions remain diagnostic-only in the
 Gallery and are never promoted by the lifecycle harness. Missing or invalid
 source paths make history restore fail explicitly. AI-off and failure/fallback
 behavior will be covered by the shared cross-technique matrix; this slice
 records the DSC lifecycle dependency without changing those policies.

## Verification

 The task will run the new focused lifecycle test together with the existing
 DSC provider, Workbench, project-service, export, and persistence tests, then
 run `python scripts/verify.py --task docs/agent/tasks/2026-07-25-dsc-lifecycle-closure.md --changed --types`.
