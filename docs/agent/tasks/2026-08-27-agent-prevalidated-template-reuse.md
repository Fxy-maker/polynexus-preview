---
task_id: 2026-08-27-agent-prevalidated-template-reuse
kind: architecture
status: complete
date: 2026-08-27
title: Reuse validated templates in Agent ComputeRun execution
---

# Reuse validated templates in Agent ComputeRun execution

## Goal

Avoid reconverting a canonical template after Agent/Codex replay validation;
the shared `ComputeRunService` must execute the already source-bound template.

## Non-goals

- No weakening of artifact hash or canonical provenance validation.
- No change to provider algorithms, result semantics, or directory adapters.
- No removal of historical recipe fields or compatibility readers.

## Shared objects and entry points

- Producer: `ComputeRunService` with an optional source-bound template input.
- Consumer: `AgentWorkflowService.run_recipe` and TPAE recipe execution.
- AI/Codex: replay validation remains mandatory before execution.
- GUI/CLI: unchanged; they continue to use normal path conversion.

## Affected boundaries

- Canonical template source-artifact and technique linkage is checked before
  the provider runs.
- Capability items are computed from the reused template exactly as for a new
  conversion.
- Agent/TPAE execution no longer invokes the converter a second time.

## Implementation plan

1. Add RED tests proving direct ComputeRun reuse and Agent/TPAE no-reconversion.
2. Add an optional validated-template parameter to `ComputeRunService`.
3. Pass the replay-validated template through Agent workflow execution.
4. Run shared producer, Agent, TPAE, and structured verification matrices.

## Acceptance criteria

- [x] A supplied template bound to the current artifact is reused without
  calling the converter registry.
- [x] A mismatched supplied template fails closed before provider execution.
- [x] Agent/TPAE replay still validates source hashes and exposes the same
  ComputeRun projection and capability items.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_compute_service.py tests/test_agent_prevalidated_template_reuse.py tests/test_tpae_golden_workflow.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-agent-prevalidated-template-reuse.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(agent): reuse replay-validated canonical templates" `
  --files polynexus/core/compute/service.py polynexus/core/agent_workflow/service.py tests/test_agent_prevalidated_template_reuse.py docs/agent/tasks/2026-08-27-agent-prevalidated-template-reuse.md docs/agent/memory/active-work.md docs/agent/memory/current-state.md docs/acceptance/2026-08-27-shared-compute-run-migration.md
```

## Completion evidence

- `python -m pytest -p no:cacheprovider -q tests/test_agent_prevalidated_template_reuse.py tests/test_compute_service.py tests/test_agent_workflow_contracts.py tests/test_tpae_golden_workflow.py` — 68 passed, 3 skipped.
- `python -m pytest -p no:cacheprovider -q tests/test_agent_prevalidated_template_reuse.py tests/test_agent_workflow_contracts.py tests/test_project_workflow_adapters.py tests/test_project_workflow_models.py tests/test_project_workflow_service.py tests/test_canonical_converter_registry.py tests/test_canonical_one_dimensional.py tests/test_compute_models.py` — 91 passed, 1 skipped.
- `git diff --check` — passed.
- The shared artifact identity now matches between Agent `InputArtifact` and Compute `RawArtifact`; replay-validated templates are passed directly to `ComputeRunService` and are not reconverted.
- Known limitations: directory compatibility adapters and legacy provider fields remain by design; full-boundary historical failures and human architecture/scientific review remain open for the overall migration goal.
- Pre-existing local runtime outputs (`active_run.json`, `runs/`, `tests/_tmp_phase3/`) were left untouched and are not part of this checkpoint.
