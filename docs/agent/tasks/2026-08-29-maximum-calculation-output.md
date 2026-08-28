---
task_id: 2026-08-29-maximum-calculation-output
kind: scientific
status: active
date: 2026-08-29
title: Expose maximum deterministic calculation output
---

# Expose maximum deterministic calculation output

## Goal

Make all deterministically computable values visible through shared results,
then provide explicit per-file and group-level tables validated on six real
samples.

## Non-goals

- Defer AI grouping, literature interpretation, paper-role selection, RAG, and
  material databases.
- Do not change scientific algorithms, thresholds, templates, or raw data.

## Affected boundaries

- Providers: DSC, IR/FTIR, SAXS, WAXS, NMR result projections.
- Shared objects: `ComputeRun`, evidence package, result-field manifest, group
  table DTO/export.
- Consumers: CLI, Batch, Agent/Codex, GUI; all read the shared projection.

## Implementation plan

1. Document and test the result-field inventory and identify fields that are
   computed but not projected.
2. Implement the technique-neutral per-file/group result-table projection,
   preserving source rows, units, methods, warnings, and condition keys.
3. Replay the six-sample project and write an acceptance report showing field
   coverage and unexplained failures.

## Acceptance criteria

- [x] Each supported technique has an explicit inventory and coverage status.
- [x] Finite diagnostic values remain visible in the shared projection.
- [x] Group statistics are explicit, condition-scoped, and traceable to rows.
- [x] Six-sample persisted replay produces a coverage report without raw-data changes.
- [x] Focused tests, task verifier, and `git diff --check` pass.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-29-maximum-calculation-output.md --changed --types
git diff --check
```

## Pre-existing changes

Leave `active_run.json`, `runs/`, and `tests/_tmp_phase3/` untouched.

## Completion evidence so far

- Result-field inventory and shared serialization are checkpointed in commit
  `9c1a9dc9`.
- Condition-scoped result table DTO/statistics are checkpointed in commit
  `9a2ae3c`.
- Six-sample persisted-result coverage is recorded in
  `docs/acceptance/2026-08-29-maximum-calculation-output.md`; provider rerun was
  intentionally not repeated because the existing external replay is already
  available and its raw directory is outside the repository.
- `build_group_results_table_model()` adapts the shared `GroupResultTable` into
  GUI primary rows, condition-scoped statistics, and warning diagnostics.
- `ProjectAnalysisSummary.to_dict()` exposes caller-supplied `result_tables`
  unchanged for the CLI/ARS JSON consumer; both entry points consume the same
  DTO. Automatic condition-axis inference remains intentionally out of scope.
- Shared-result verification: 91 focused tests passed (3 skipped); task
  verifier quality 313 and preprocessing 157 passed, with Ruff/compile/
  whitespace checks green.
