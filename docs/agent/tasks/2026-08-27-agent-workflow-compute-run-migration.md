---
task_id: 2026-08-27-agent-workflow-compute-run-migration
kind: architecture
status: complete
date: 2026-08-27
title: Expose shared ComputeRun projections in Agent workflow steps
---

# Expose shared ComputeRun projections in Agent workflow steps

## Goal

Make each newly executed Agent/Codex workflow step carry the same JSON-safe
`ComputeRun` projection used by GUI and Batch, while preserving existing
workflow recipe, evidence, and provider compatibility.

## Non-goals

- No removal of `AnalysisResult` provider adapters.
- No recipe schema or database migration.
- No changes to scientific algorithms or raw inputs.

## Affected boundaries

- `polynexus/core/agent_workflow/models.py`
- `polynexus/core/agent_workflow/service.py`
- `tests/test_agent_workflow_contracts.py`
- `tests/test_project_workflow_adapters.py`

## Implementation plan

1. Add an optional JSON-safe `compute_run` projection to
   `WorkflowStepResult`, preserving the serialized shape of old steps.
2. Execute file-backed non-DSC workflow steps through `ComputeRunService` with
   a one-shot provider adapter, then attach the resulting shared projection.
3. Keep directory and DSC adapter routes unchanged until the dedicated DSC
   thermal-program phase; retain existing workflow status and receipt rules.
4. Add focused contract and project-workflow tests, then run the structured
   task verifier.

## Acceptance criteria

- [x] A completed workflow step exposes a JSON-safe shared `compute_run`
  projection containing artifact, dataset, plan, result, and canonical template
  fields when conversion is available.
- [x] Existing `result_summary`, evidence, figure, recipe, and receipt fields
  remain unchanged and old serialized steps without `compute_run` remain
  readable.
- [x] Provider exceptions and invalid recipes retain current blocked/failed
  behavior without fabricating a compute run.
- [x] Focused workflow tests and structured verifier pass.

## Completion evidence

- Generic file-backed IR/SAXS/WAXS workflow steps now execute through
  `ComputeRunService`; their step payload exposes artifact, dataset, plan,
  result, canonical template, and capability-item projections.
- Directory workflows and the protected DSC template adapter remain unchanged
  for the dedicated DSC migration phase.
- Focused workflow matrix passed `51`; structured verification passed task
  checks, Ruff/compile, quality `310`, preprocessing `157`, and whitespace.
- Existing recipe/step serialization remains compatible when `compute_run` is
  absent.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_contracts.py tests/test_project_workflow_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-agent-workflow-compute-run-migration.md --changed --types
git diff --check
```
