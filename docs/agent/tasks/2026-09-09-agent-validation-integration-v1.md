---
task_id: 2026-09-09-agent-validation-integration-v1
kind: architecture
status: implementation_complete_review_required
date: 2026-09-09
title: Expose project validation through agent workflow
---

# Agent validation integration v1

## Goal

Expose the project validation batch through the existing machine-readable
Agent/Codex workflow so an agent can run a JSON validation manifest and receive
the same persisted project report as the standalone project CLI.

## Non-goals

- Do not change `AgentWorkflowService` provider execution or AnalysisRun
  validation semantics.
- Do not execute arbitrary Python from an agent manifest.
- Do not import reports into Evidence Package, promote capabilities, or claim
  uncertainty/scientific validity.

## Shared objects and entry points

- Objects: `ProjectValidationEntry`, `ProjectValidationBatch`, and
  `ProjectWorkspace` validation report.
- AI/Codex/CLI: add `agent-workflow validate-project` using a JSON manifest;
  it delegates to the same project batch runner.
- GUI: unchanged; it may later read `.polynexus/validation/latest.json`.
- Cross-entry rule: standalone `project-validate` and Agent operation produce
  the same batch/report projection and storage location.

## Affected boundaries

- Agent CLI parser and adapter only; the pre-existing dirty
  `core/agent_workflow/service.py` is intentionally untouched.
- Project validation aggregation and workspace persistence are reused.
- Security boundary remains JSON-only with no dynamic code execution.

## Implementation plan

1. Add `validate-project` operation and project-root argument to the Agent CLI.
2. Route its manifest through `run_project_validation_batch` and
   `ProjectWorkspace.write_validation_batch`.
3. Add focused parser, success, invalid-manifest, and output-path tests.

## Acceptance criteria

- [x] Agent CLI accepts `validate-project` with project root and validation
  manifest.
- [x] It persists under `.polynexus/validation/latest.json` and returns one
  JSON envelope with the aggregate report.
- [x] It reuses the same DTO/hash validation and returns nonzero on failures.
- [x] Existing Agent `run`, `validate`, and `export` behavior is unchanged.
- [x] No ComputeRun/Evidence/capability mutation occurs.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_agent_validation_integration.py
python scripts/verify.py --task docs/agent/tasks/2026-09-09-agent-validation-integration-v1.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(agent): expose project validation workflow" `
  --files polynexus/cli/parser.py polynexus/cli/run_agent_workflow_service.py tests/test_agent_validation_integration.py docs/agent/tasks/2026-09-09-agent-validation-integration-v1.md docs/agent/memory/current-state.md docs/agent/memory/active-work.md
```

## Completion evidence

- Exact commands and outcomes: focused Agent validation and existing Agent
  workflow tests pass (12 total); final task verifier pending.
- Known limitations or follow-up: GUI presentation and real instrument/standard
  sample replay remain separate work.
- Pre-existing changes left untouched: `polynexus/core/agent_workflow/service.py`
  and unrelated untracked plans/data.
