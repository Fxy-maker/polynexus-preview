---
task_id: 2026-08-27-batch-compute-run-migration
kind: architecture
status: implementation_complete_review_required
date: 2026-08-27
title: Migrate Batch CLI to ComputeRun
---

# Migrate Batch CLI to ComputeRun

## Goal

Make each Batch CLI file use `ComputeRunService` and persist the shared public
run projection while preserving progress summaries and legacy database reads.

## Non-goals

- No Batch parallelism redesign.
- No database schema deletion.
- No Codex, GUI, or DSC migration in this phase.

## Affected boundaries

- `polynexus/cli/batch_run_service.py`
- `tests/test_cli_batch.py`, `tests/test_cli_batch_run_service.py`

## Implementation plan

1. Add failing tests proving Batch rows carry a shared `ComputeRun` for generic
   inputs and block ambiguous mappings before provider execution.
2. Route `run_batch_one` through `ComputeRunService`, retain legacy result
   compatibility through a narrow engine adapter, and pass the shared run to
   persistence.
3. Run Batch/output focused tests and the structured verifier; record the
   checkpoint before beginning the next migration phase.

## Acceptance criteria

- [x] Batch provider invocation occurs through `ComputeRunService`.
- [x] Summary rows retain `file`, `technique`, `status`, `r2`, and `elapsed`.
- [x] A shared `ComputeRun` projection is available to persistence.
- [x] Ambiguous generic input is reported as a failed/needs-input row without provider execution.
- [x] Existing batch CLI tests remain green.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_cli_batch.py tests/test_cli_batch_run_service.py tests/test_cli_output.py
python scripts/verify.py --task docs/agent/tasks/2026-08-27-batch-compute-run-migration.md --changed --types
git diff --check
```

## Completion evidence

- Focused Batch/output matrix: `21 passed`.
- Structured verification passed task-check, Ruff, compile, quality `309`,
  preprocessing `157`, and whitespace with the command above.
- Known limitations: database schema and GUI history migration remain separate.
