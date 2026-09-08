---
task_id: 2026-09-08-agent-portable-export-replay
kind: architecture
status: complete
date: 2026-09-08
title: Replay source-bound portable exports through AgentWorkflow
---

# Replay source-bound portable exports through AgentWorkflow

## Goal

Allow a persisted project/Codex recipe that declares a portable export to be
replayed deterministically through the same Core conversion and ComputeRun
contracts used by the CLI.

## Non-goals

- Do not decode private vendor bytes or weaken the missing-reader boundary.
- Do not create a second provenance or result representation.
- Do not add the GUI portable-export dialog in this task.
- Do not silently accept a changed raw source, export table, exporter, or
  canonical template.

## Affected boundaries

- `polynexus/core/agent_workflow/service.py`: recipe admission, canonical
  replay, and shared execution input selection.
- `polynexus/core/project_workflow/adapters.py`: portable declaration and
  recipe integrity validation.
- Focused AgentWorkflow/project replay tests.

## Implementation plan

1. Add failing replay tests covering an opaque raw source, portable export,
   canonical-template hash replay, successful ComputeRun execution, and raw or
   export tampering.
2. Validate portable recipe declarations and bind them to the raw artifact
   identity before provider execution.
3. Reconvert portable exports during recipe replay and compare the complete
   canonical template hash.
4. Execute the portable table through the shared ComputeRun while retaining the
   raw artifact as the source provenance anchor.
5. Run focused tests, the structured verifier, and create one allowlisted local
   checkpoint.

## Acceptance criteria

- [x] A recipe built from an opaque raw file and portable export replays to a
  completed shared ComputeRun.
- [x] Raw-file mutation, export mutation, missing export, invalid exporter, and
  canonical-template tampering fail closed before provider execution.
- [x] The ComputeRun canonical template retains the raw source binding and
  export hash.
- [x] Existing non-portable AgentWorkflow replay remains unchanged.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_agent_portable_export_replay.py tests/test_project_workflow_adapters.py
python scripts/verify.py --task docs/agent/tasks/2026-09-08-agent-portable-export-replay.md --changed --types
git diff --check
```
