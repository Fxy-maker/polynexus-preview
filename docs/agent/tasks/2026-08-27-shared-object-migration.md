---
task_id: 2026-08-27-shared-object-migration
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Migrate all entry points to shared ComputeRun objects
---

# Migrate all entry points to shared ComputeRun objects

## Goal

Complete the staged migration of Batch, GUI persistence, Codex/Agent workflow,
and DSC multi-program conversion without deleting user-facing features.

## Non-goals

- No raw data modification or automatic merge/push.
- No immediate deletion of legacy readers or persistence rows.
- No change to existing scientific provider algorithms.

## Shared objects and entry points

- Shared producer: `ComputeRunService` and canonical converters.
- Consumers: Batch CLI, Quick Analysis/GUI persistence, Agent/Codex workflow.
- DSC remains a protected scientific adapter until thermal-program tests pass.

## Affected boundaries

- Batch result summaries and database persistence.
- GUI history/result restore DTOs.
- Agent workflow step results and replay receipts.
- DSC canonical conversion and existing Avrami provider bridge.

## Acceptance criteria

- [x] Each entry point has a focused migration task and shared-object tests.
- [x] New Batch runs persist a `ComputeRun` projection and retain legacy read compatibility.
- [x] GUI persistence can round-trip canonical template/capability fields.
- [x] Codex/Agent steps expose the same run fields without reparsing raw data.
- [x] DSC multi-program input has a `thermal_program.v1` template with protected Avrami results.
- [x] GUI folder batch execution uses `ComputeRunService` and retains the
  shared run on each displayed batch row.
- [ ] Redundant producers are removed only after consumer and six-sample acceptance.

The final deletion criterion remains intentionally open: compatibility readers
and legacy result fields are still needed for historical records and must not
be removed until full-boundary verification and human review authorize it.

## Phase tasks

1. `docs/agent/tasks/2026-08-27-batch-compute-run-migration.md`
2. `docs/agent/tasks/2026-08-27-gui-persistence-compute-run-migration.md`
3. `docs/agent/tasks/2026-08-27-agent-workflow-compute-run-migration.md`
4. `docs/agent/tasks/2026-08-27-dsc-thermal-program-migration.md`
5. `docs/agent/tasks/2026-08-27-gui-batch-compute-run-migration.md`
6. `docs/agent/tasks/2026-08-27-agent-compute-run-single-producer.md`

## Verification

Each phase uses its own focused task verifier; the final migration requires
`python scripts/verify.py --changed --types --full --boundary` and the six
sample replay acceptance record.

## Completion evidence

The six-sample replay and focused shared-object matrix are recorded in
`docs/acceptance/2026-08-27-shared-compute-run-migration.md`. The migration is
implementation-complete but remains review-required because legacy full-suite
failures and scientific acceptance are not closed.
