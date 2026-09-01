---
task_id: 2026-08-31-codex-ars-research-loop
kind: architecture
status: implementation_complete_review_required
date: 2026-08-31
title: Add a recoverable Codex–PolyNexus–ARS research loop
---

# Recoverable Codex–PolyNexus–ARS research loop

## Goal

Give Codex one resumable, project-local research task that can inspect and
confirm data mappings, request deterministic PolyNexus analysis, hand the
result to the full ARS writing/review flow, route ARS actions, and block a
formal manuscript export until the required scientific and editorial gates
pass.

## Non-goals

- Do not add a second scientific calculation, provenance, evidence, chart, or
  manuscript data model.
- Do not make GUI Quick Analysis visible to the AI research task.
- Do not infer missing experimental conditions, assignments, compositions,
  geometry, or mechanism claims.
- Do not overwrite raw data, immutable `ComputeRun` results, frozen evidence
  packages, or historical task revisions.
- Do not auto-submit a paper or silently approve a scientific judgment.

## Shared objects and entry points

- Objects: `ResearchTask`/revision and `ResearchAction` are orchestration
  state; `AnalysisRequest`, `ProjectPlan`, `ProjectWorkflowRun`, `ComputeRun`,
  evidence packages, `ManuscriptSource`, and `PreflightReport` remain the
  authoritative shared scientific/public objects.
- AI/Codex/CLI: creates and resumes tasks, proposes mappings, asks for
  confirmations, invokes explicit stages, consumes the same run/evidence DTOs,
  and routes ARS actions.
- ARS: consumes a validated package handoff and returns structured
  `edit`/`recompute`/`ask_human` actions; it does not mutate Core results.
- GUI: continues to expose independent quick calculations. It may display
  persisted public run/evidence DTOs, but its transient Quick Analysis records
  are deliberately excluded from `ResearchTask` discovery.
- Cross-entry rule: all formal analysis is delegated to
  `ProjectWorkflowService` and all paper checks to Suite contracts; no
  task-local numerical or citation representation is introduced.

## Affected boundaries

- `polynexus.core.project_workflow`: append-only task/action persistence,
  shared run creation, task-scoped evidence freezing, and restart validation.
- `polynexus.suite`: package-bound ARS handoff, persisted completion receipt,
  and formal manuscript preflight. Package artifact hashing must remain
  streaming for large evidence packages.
- `polynexus.cli`: the `research-loop` adapter invokes the same service facade;
  it does not parse technique-specific data or compute scientific values.
- GUI Quick Analysis remains outside formal task discovery. Existing GUI,
  ProjectWorkflow, CLI, Suite and ARS consumers continue to exchange the
  established public run/evidence/manuscript DTOs.

## Implementation plan

1. Define append-only task/action contracts and recovery validation under the
   existing project workspace, then cover state, tampering and restart cases.
2. Route explicit inspect, mapping confirmation, deterministic run, checkpoint
   and task-scoped handoff stages through `ProjectWorkflowService`.
3. Add typed ARS action/completion persistence and use the existing Suite
   preflight contracts to block an incomplete, untraceable or self-declared
   formal manuscript.
4. Expose the same facade through the thin CLI adapter and verify shared object
   compatibility across ProjectWorkflow, Suite and existing GUI DTO boundaries.
5. Replay a small fixture and the real PA6-H input in derived storage only;
   document limitations, run the task-scoped matrix, and checkpoint the
   allowlisted changes locally.

## Persistence boundary

The only new writable area is:

```text
<project>/.polynexus/research/
  index.json
  tasks/<task_id>/revisions/task-000001.json
  tasks/<task_id>/revisions/task-000002.json
  tasks/<task_id>/actions/<action_id>.json
  tasks/<task_id>/handoffs/<handoff_id>.json
```

Revision files and action/handoff records are write-once. `index.json` is a
small latest-revision pointer and may be atomically refreshed. The store
validates hashes and parent revision links on load, so an interrupted write
can be resumed from the last complete revision.

## State and confirmation policy

Task states are finite and explicit: `draft`, `awaiting_mapping_confirmation`,
`ready`, `running`, `awaiting_human`, `ars_in_progress`, `revision_required`,
`export_ready`, `completed`, and `blocked`. Transitions reject invalid source
states. Fixed confirmation points are mapping, research/claim promotion,
material ARS disagreements, and final manuscript approval; an anomaly may add
an `ask_human` action without changing the scientific result.

The AI may try deterministic analyses and bounded recomputations. A new run or
paper iteration always gets a new ID and task revision. `edit` actions stay in
ARS, `recompute` actions return to PolyNexus, and `ask_human` pauses the task.

## Acceptance criteria

- [x] A task round-trips through JSON, has a content hash, and rejects invalid
      transitions or tampered revisions.
- [x] Multiple tasks in one project remain isolated while reusing immutable
      source/run objects only through an explicit reuse record.
- [x] Mapping proposals require one persisted human decision before formal run.
- [x] `inspect → propose_mapping → confirm → run → checkpoint → handoff` uses
      existing ProjectWorkflow/ComputeRun/evidence contracts.
- [x] ARS actions are persisted and deterministically routed as
      `edit`/`recompute`/`ask_human`; resume continues from the latest revision.
- [x] A present GUI Quick Analysis attachment is not discovered by a research
      task unless a user explicitly supplies a formal source scope.
- [x] Formal manuscript export is blocked when ARS is incomplete, methods or
      citations are unverified, internal audit terms leak into visible text, or
      traceability/layout checks fail.
- [x] A small fixture passes the complete state/recovery matrix; the real
      `弹性体中文` project is replayed read-only into derived storage and its
      scientific limitations remain explicit.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q `
  tests/test_research_loop.py `
  tests/test_research_loop_cli.py `
  tests/test_suite_research_loop_contracts.py `
  tests/test_research_loop_integration.py `
  tests/test_working_evidence_scope.py `
  tests/test_research_loop_risk_boundaries.py `
  tests/test_research_loop_real_mapping.py `
  tests/test_suite_handoff.py `
  tests/test_paper_pipeline.py `
  tests/test_project_workflow_recovery.py `
  tests/test_project_evidence_workspace.py `
  tests/test_project_workflow_adapters.py `
  tests/test_compute_service.py `
  tests/test_agent_prevalidated_template_reuse.py
python scripts/verify.py --task docs/agent/tasks/2026-08-31-codex-ars-research-loop.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "feat(research): add recoverable codex ars loop" `
  --files polynexus/core/project_workflow/research_loop.py `
          polynexus/core/project_workflow/workspace.py `
          polynexus/core/project_workflow/service.py `
          polynexus/core/project_workflow/adapters.py `
          polynexus/core/project_workflow/__init__.py `
          polynexus/cli/run_research_loop_service.py `
          polynexus/cli/run_suite_service.py `
          polynexus/cli/parser.py `
          polynexus/__main__.py `
          polynexus/suite/handoff.py `
          polynexus/suite/preflight.py `
          polynexus/suite/__init__.py `
          tests/fixtures/research_loop/raw/IR/spectrum.csv `
          tests/test_research_loop.py `
          tests/test_research_loop_cli.py `
          tests/test_research_loop_integration.py `
          tests/test_research_loop_real_mapping.py `
          tests/test_research_loop_risk_boundaries.py `
          tests/test_suite_research_loop_contracts.py `
          tests/test_working_evidence_scope.py `
          tests/test_suite_handoff.py `
          docs/acceptance/2026-08-31-codex-ars-research-loop.md `
          docs/agent/tasks/2026-08-31-codex-ars-research-loop.md `
          docs/agent/memory/active-work.md `
          docs/agent/memory/current-state.md
```

## Completion evidence

- `run()` constructs and validates the shared `AnalysisRequest` before it
  persists the `running` transition; an invalid request leaves the task
  `blocked`. Mapping/action approval accepts only an actual JSON boolean, so
  string values such as `"false"` never approve an irreversible stage.
- Every `recompute` route is persisted. A regular `run()`/`advance()` cannot
  bypass a `revision_required` action; action resolutions can be replayed
  safely even if the resolution record reached disk before the task head.
- `record_ars_completion()` writes an append-only completion record bound to
  the task, current handoff hash, evidence-package hash, and the complete ARS
  action set. Submission preflight accepts this durable record only and
  invalidates it if a handoff or ARS action changes. This is a local protocol
  receipt, not authentication that a remote ARS service executed the work.
- Formal manuscript evidence, metric, and figure identifiers are checked
  against the package bound to the recorded handoff; an empty-data manuscript
  cannot pass through self-reported workflow status. Handoff validation also
  confirms task-owned run manifests before calling ARS.
- A final boundary review found and fixed the case where a compatible handoff
  provider could report `ready` for a package without `manifest.json`; formal
  handoff now rejects missing or hash-mismatched manifests before persisting a
  handoff or advancing the task to `ars_in_progress`.
- Package artifact SHA-256 checks stream 1 MiB chunks, preventing a large
  immutable package from being loaded fully into memory for integrity checks.
- Exact commands and outcomes are recorded in
  `docs/acceptance/2026-08-31-codex-ars-research-loop.md`; the final fresh
  matrix and task-scoped verifier are run before checkpointing.
- Known limitations: actual ARS model execution, online citation checks,
  scientific promotion and final manuscript approval still require the
  installed ARS runtime and human review. The service provides the durable
  protocol and gates but does not invent scientific values or decisions.
- Real replay: `PA6-H.csv` was copied read-only to
  `D:\PolyNexus-real-project-replay-final-20260831-v3`; one NMR run, one
  package and one task-bound handoff were produced, with status
  `ars_in_progress`/`review_required` and a pending human-scientific-review
  decision.
- Pre-existing changes left untouched: all unrelated modified/untracked files
  listed by `git status`, including AI-platform trust-boundary changes, paper
  drafts/specs/plans, `active_run.json`, `runs/`, `tests/_tmp_phase3/`, and
  literature scratch files.
