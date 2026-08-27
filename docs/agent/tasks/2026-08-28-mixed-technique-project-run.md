---
task_id: 2026-08-28-mixed-technique-project-run
kind: architecture
status: implementation_complete_review_required
date: 2026-08-28
title: Unify mixed-technology project workflow runs
---

# Unify mixed-technology project workflow runs

## Goal

Route one explicit mixed-technique project request through one composite
recipe/run while preserving independent deterministic technique steps.

## Non-goals

- No changes to DSC, FTIR, SAXS, WAXS, or NMR provider algorithms.
- No material database, automatic sample identity, or causal inference.
- No deletion of legacy single-technique compatibility paths.

## Affected objects and entry points

- `ProjectPlan`, `AnalysisRun`, `ProjectWorkflowRun`, evidence package.
- `analyze-project` CLI/project entry point and Agent workflow service.
- Existing single-file and series adapters remain component producers.

## Affected boundaries

- `polynexus/core/project_workflow/adapters.py`: composite recipe proposal and
  validation.
- `polynexus/core/project_workflow/service.py`: one-request planning and
  execution dispatch.
- `polynexus/core/project_workflow/package.py`: cross-technique relation for a
  single composite run.
- `tests/test_mixed_technique_project_run.py` plus existing project workflow
  and package consumers.

## Implementation plan

1. Add a failing mixed-technique project test asserting one request-level run
   with independent technique steps and a cross-technique package relation.
2. Add a composite adapter that delegates component proposal/validation to the
   existing DSC, single-input, and series adapters and rebases artifact indexes.
3. Route mixed plans through the composite adapter while preserving existing
   single-technique and series branches.
4. Update package relation projection to identify cross-technique membership
   even when all components are stored in one composite run.
5. Run the focused matrix, task verifier, and diff check; then checkpoint only
   the files changed by this task.

## Acceptance criteria

- [x] Mixed input is no longer blocked solely by `mixed_technique_inputs`.
- [x] One mixed request returns one request-level run with one step per selected
      technique/series component.
- [x] Each step still uses the shared `ComputeRun` and canonical template.
- [x] Package relations identify the result as cross-technique membership.
- [x] Single-technique and series tests remain green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_mixed_technique_project_run.py tests/test_ai_native_project_entrypoint.py tests/test_project_workflow_package.py
python scripts/verify.py --task docs/agent/tasks/2026-08-28-mixed-technique-project-run.md --changed --types
git diff --check
```

## Completion evidence

- Mixed-technique regression and existing project/package matrix: **44 passed**.
- Task verifier, Ruff, compile, quality gate (**311 passed**) and preprocessing
  gate (**157 passed**) completed successfully.
- The composite route is implementation-complete but remains review-required
  for scientific interpretation and the broader release boundary.
