# Capability evidence projection — 2026-08-28

Completed canonical capability items from `ComputeRun` are now copied into the
public Agent workflow step summary and projected into the package citation
ledger. Each numeric record uses a deterministic `canonical.<capability_id>`
method and includes the capability item id, measurement id, source hash, and
run id through the existing evidence contract.

Unsupported, unavailable, and failed capability items remain explicit in the
run projection and never create fabricated numeric metrics. Generic capability
metrics are diagnostic-only by default and do not override technique-specific
scientific eligibility.

Verification:

- `python -m pytest -p no:cacheprovider -q tests/test_capability_evidence_projection.py tests/test_capability_execution.py tests/test_project_workflow_package.py tests/test_ai_native_project_entrypoint.py tests/test_compute_service.py tests/test_project_workflow_adapters.py` — **104 passed, 3 skipped**
- `python scripts/verify.py --task docs/agent/tasks/2026-08-28-capability-evidence-projection.md --changed --types` — selected checks passed; quality **311 passed**, preprocessing **157 passed**
- `git diff --check` — passed

Limitations: this expands provenance and citable observations; it does not
change provider algorithms or automatically promote values to manuscript
Results.
