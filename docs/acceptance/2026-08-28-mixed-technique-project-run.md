# Mixed-technique project run — 2026-08-28

`analyze-project` now submits one request for explicitly selected files across
multiple techniques. The planner no longer treats the presence of multiple
techniques as a blocker. A composite adapter merges the existing component
recipes into one immutable recipe, and `AgentWorkflowService` executes every
component through the shared `ComputeRun` path.

The project result contains one `ProjectWorkflowRun` with independent IR,
WAXS (and supported DSC/SAXS series) steps. The evidence package retains
technique-level provenance and writes a `cross_technique_evidence_set`
relation even when there is only one request-level run.

Verification:

- `python -m pytest -p no:cacheprovider -q tests/test_mixed_technique_project_run.py tests/test_ai_native_project_entrypoint.py tests/test_project_workflow_package.py` — **44 passed**
- `python scripts/verify.py --task docs/agent/tasks/2026-08-28-mixed-technique-project-run.md --changed --types` — selected checks passed; quality **311 passed**, preprocessing **157 passed**
- `git diff --check` — passed

Limitations: scientific Results/Discussion promotion remains an ARS/human
review decision; legacy full-suite failures remain recorded separately.
