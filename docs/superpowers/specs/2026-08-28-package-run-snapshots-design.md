# Package Run Snapshots

Validated run manifests are copied unchanged into a package-local `runs/`
directory. The package manifest references these snapshots with relative paths;
raw sources remain referenced by hash and are never copied. This preserves the
existing validation contract while allowing a moved package to retain its run
provenance without depending on the original workspace path.
