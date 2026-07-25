# Export figure-run provenance design

The unified figure lifecycle stores immutable run manifests under
`<output>/runs/<run_id>` and selects one through `<output>/active_run.json`.
Export already copies the run tree under `metadata/runs`; this slice makes that
relationship explicit and relocatable by copying the active pointer to
`metadata/active_run.json` and declaring both paths in `metadata/export_manifest.json`.

The bundle is descriptive, not implicitly activated in the running GUI. A future
consumer can use the declared paths to create an explicit Gallery root while
preserving run-relative document/data-source provenance.
