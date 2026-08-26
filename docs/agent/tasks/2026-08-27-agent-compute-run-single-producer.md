---
task_id: 2026-08-27-agent-compute-run-single-producer
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Make Agent file workflow use one shared producer
---

# Make Agent file workflow use one shared producer

## Goal

Ensure default file-backed Agent/Codex steps invoke the provider only through
`ComputeRunService`, while retaining custom provider-runner compatibility for
integrations that supply their own result adapter.

## Non-goals

- No directory workflow, DSC adapter, recipe schema, or provider algorithm
  changes.
- No removal of legacy `AnalysisResult` fields used by evidence consumers.

## Shared objects and entry points

- Producer: `AgentWorkflowService._run_shared_compute` and
  `ComputeRunService`.
- Consumers: Agent/Codex workflow receipts, project workflow adapters, and
  ARS evidence projections.

## Affected boundaries

- Default file-backed steps resolve an engine and call `ComputeRunService`
  exactly once.
- Explicit custom `provider_runner` integrations remain wrapped for backward
  compatibility.
- A non-completed shared run propagates its structured reason instead of being
  converted into a fabricated provider result.

## Implementation plan

1. Add a regression test proving ambiguous canonical mapping blocks before a
   default provider call.
2. Route default file-backed steps through the shared service and retain the
   compatibility adapter only for explicit custom runners.
3. Run Agent/project workflow and shared producer matrices.

## Acceptance criteria

- [x] Default file-backed Agent/Codex execution has one provider invocation.
- [x] Mapping failures are returned before provider execution.
- [x] Custom provider-runner and directory/DSC compatibility paths remain
  available.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_agent_workflow_cli.py tests/test_agent_workflow_contracts.py tests/test_project_workflow_adapters.py tests/test_project_workflow_cli.py tests/test_project_workflow_index.py tests/test_project_workflow_models.py tests/test_project_workflow_package.py tests/test_project_workflow_recovery.py tests/test_project_workflow_service.py tests/test_project_workflow_workspace.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-agent-compute-run-single-producer.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(agent): make file workflow use shared producer" `
  --files docs/agent/tasks/2026-08-27-agent-compute-run-single-producer.md polynexus/core/agent_workflow/service.py tests/test_agent_workflow_contracts.py docs/agent/tasks/2026-08-27-shared-object-migration.md docs/acceptance/2026-08-27-shared-compute-run-migration.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md
```
