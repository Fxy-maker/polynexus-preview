# NMR and Joint provenance matrix design

The matrix exercises existing production entrypoints rather than adding a
technique-specific gallery. NMR uses `NMREngine.plot()` and Joint uses
`JointCoordinator.publish_hub_report()`; both are inspected through
`build_active_manifest_gallery_entries()` and the run-relative figure documents.

Publication role is read from the persisted Manifest, not inferred from title or
GUI ordering. Diagnostic entries may be ready assets, but remain diagnostic by
role. Any generation failure must remain as a Manifest entry with an explicit
failure status and error.
