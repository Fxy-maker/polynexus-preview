# ARS evidence file links — 2026-08-29

`ars-writing-input.json` now explicitly points to the package-relative shared
projections:

- `result_tables`: `result-tables.json`
- `writing_evidence`: `writing-evidence.json`
- `citation_metrics`: `citation-metrics.json` (existing)

The payload still contains only lightweight IDs and eligibility boundaries;
large result/evidence objects are not duplicated. GUI, CLI, and ARS therefore
continue to consume the same package files.

Verification:

```text
pytest -q tests/test_project_workflow_package.py::test_package_writes_citation_metrics_with_writing_evidence_links tests/test_project_ars_writing_handoff.py
4 passed

python scripts/verify.py --task docs/agent/tasks/2026-08-29-ars-evidence-file-links.md --changed --types
selected checks passed; quality 313; preprocessing 157
```
