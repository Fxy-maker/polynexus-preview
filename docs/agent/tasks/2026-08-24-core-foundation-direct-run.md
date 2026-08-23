---
task_id: 2026-08-24-core-foundation-direct-run
kind: architecture
status: implementation_complete_review_required
date: 2026-08-24
title: Define the direct-run core migration boundary
---

# Define the direct-run core migration boundary

## Goal

Establish the protected architecture boundary for a shared direct-run façade
before source migration begins.

## Non-goals

- Change DSC, IR, SAXS, WAXS, or NMR numerical algorithms.
- Delete legacy workflow, evidence, writing, manuscript, Joint, RAG, or
  persistence code.
- Change the database schema or migrate historical persisted results.

## Affected boundaries

- Analysis engine: adds a façade only; DSC, IR, SAXS, WAXS, and NMR numerical
  algorithms remain unchanged.
- Result/schema contract: creates compute contracts while legacy `AnalysisResult`
  remains a compatibility projection.
- CLI/AI: existing single-technique CLI commands return direct-run JSON via
  `--json`.
- GUI: `AnalysisWorker` invokes the same service and retains the received
  `ComputeRun` in memory.
- Persistence/export: the database schema remains unchanged; old legacy-result
  persistence is a temporary adapter.

## Shared objects and entry points

- Shared objects: `RawArtifact`, `CanonicalDataset`, `AnalysisPlan`, and
  `ComputeResult`; `ComputeRun` is the new direct-run record. Legacy
  `AnalysisResult` remains only as a temporary in-memory compatibility
  projection while consumers migrate.
- Changed entry points: the single-technique CLI route and GUI
  `AnalysisWorker` both move to `ComputeRunService.run_direct`.
- Unchanged compatibility consumers: `AgentWorkflowService` and the batch CLI
  remain on their legacy paths in this first CLI/Quick Analysis vertical slice.
  Each requires a separate migration task with focused contract tests.
- Persistence is unchanged and remains a temporary legacy-result bridge. No UI
  surface or paper-workflow contract changes are included.

## Acceptance criteria

- [x] A missing path produces `needs_input`, not a review state.
- [x] A legacy engine validation warning produces a `completed` run with
  warnings.
- [x] CLI and GUI both call `ComputeRunService.run_direct`.
- [x] `AgentWorkflowService` and the batch CLI remain unchanged compatibility
  consumers; this task does not claim that either route uses
  `ComputeRunService.run_direct`.
- [x] Public compute JSON contains no `analysis_evidence`, writing eligibility,
  or manuscript fields.
- [x] The façade preserves the legacy `AnalysisResult` only as an in-memory
  compatibility projection while consumer migrations are completed.

## Implementation plan

1. Record the protected direct-run contract and exclusions in this task card.
2. Inventory current import and entry-point consumers from scoped source search
   evidence before future deletion work.
3. Add the temporary-bridge status to durable active-work memory without
   removing legacy code.
4. Validate the task card and whitespace, then checkpoint only these records.

## Verification

```powershell
python scripts/task_check.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md
python scripts/verify.py --task docs/agent/tasks/2026-08-24-core-foundation-direct-run.md --changed --types
git diff --check
```

## Completion evidence

- Cumulative focused verification: `71 passed, 4 skipped`.
- Import/boundary verification: `25 passed, 3 skipped`.
- Final reviewer evidence: `python scripts/verify.py --task
  docs/agent/tasks/2026-08-24-core-foundation-direct-run.md --changed --types`
  passed, including quality `309` and preprocessing `157`; `git diff --check`
  passed.
- Local implementation range: `8962db67` (`docs(core): define direct-run
  migration boundary`) through `6a93624a` (`fix(core): reject malformed output
  paths`).  The sequence records the task-card/inventory checkpoints, direct
  compute contracts and their hardening, direct service routing and hardening,
  shared CLI/Quick Analysis routing, and direct-directory/output-path
  containment fixes.

## Limitations and review boundary

- This is an architecture task and requires human review before merge. No raw
  data was edited, and no push or merge was performed.
- Only direct CLI commands and `AnalysisWorker` migrated. `batch_run_service`
  and `AgentWorkflowService` remain explicit legacy consumers; the existing
  engine adapter still imports legacy core transitively.
- The direct canonical envelope is temporary source identity plus format, not
  a universal conversion replacement. GUI persistence still uses the legacy
  `AnalysisResult` compatibility bridge.
- No evidence, RAG, or Joint removal occurred. Do not delete old modules yet.
- This evidence does not claim release-wide or full-suite green status. Any
  external real-data fixture collection issue remains unrelated to this slice.

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(core): record direct-run foundation acceptance" `
  --files docs/agent/tasks/2026-08-24-core-foundation-direct-run.md docs/agent/memory/active-work.md
```
