# NMR and Joint published-run provenance matrix — 2026-07-25

## Delivered

- NMR `NMREngine.plot()` now persists spectrum as `main` and deconvolution as
  `diagnostic`, matching the customized Workbench profile instead of relying on
  the default `si` role.
- NMR and Joint synthetic published runs are discoverable through the normal
  manifest-only active Gallery.
- Gallery entries resolve object-editing documents and all publication assets
  under the exact run root; document data sources retain `path_kind=run_relative`.
- A failed diagnostic FigureDefinition remains a Manifest entry with explicit
  `generation_failed`, `diagnostic`, and error fields.

## Evidence

- NMR/Joint provenance, Gallery, failure visibility, provider, Coordinator, and
  shared role-order matrix: 10 passed.
- Task-scoped verifier passed with external basetemp; quality gate 282 and
  preprocessing gate 103 were green.
- Real-data and restarted-GUI review, export-bundle inspection, AI-off/failure/
  fallback scientific review remain open.
