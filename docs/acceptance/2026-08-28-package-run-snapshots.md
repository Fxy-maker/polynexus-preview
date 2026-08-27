# Package run snapshots — 2026-08-28

Evidence packages now include one validated run-manifest snapshot per run at
`runs/<run_id>.json`; `manifest.json.run_manifests` uses only those relative
paths. Raw input files remain external and hash-bound, so this change improves
provenance portability without copying or mutating experimental data.

Verification:

- Package/evidence/AI matrix: **50 passed**.
- Task-scoped structured verification and quality gates are recorded after the
  checkpoint.
