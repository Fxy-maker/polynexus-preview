# Task: SAXS data-quality review visibility in Workbench

**Status:** complete; checkpointed at `fb76039`

## Goal

Expose the existing q/I `DataQualityReport` as read-only Workbench review
context for static, temperature, and strain payloads, so dirty-data evidence is
visible before a user interprets exported metrics or figures.

## Affected boundaries

- `polynexus/gui/saxs_results_table_service.py`: presentation-only formatter.
- `tests/test_saxs_results_table_service.py`: focused Workbench regressions.
- Task/spec/plan and durable SAXS memory records.

## Non-goals

- No changes to q/I cleaning, sorting, fitting, quality levels, physical gates,
  rescue, AI, figure roles, or publication eligibility.
- No aggregation that invents a report or infers scientific validity from
  counts; batch text only counts and displays already-emitted reports.
- No mutation of the source payload, real datasets, generated outputs, or
  parallel GUI/release scratch files.

## Acceptance criteria

- [x] A top-level `data_quality_report` shows its existing level, source/ref,
  defect counts, reason codes, and actions in the Workbench review channels.
- [x] `_batch_data` reports show explicit reported-frame coverage and emitted
  level/reason information without copying one frame's report to another.
- [x] Missing reports remain absent/empty and do not create a positive status;
  source rows and payload immutability are preserved.
- [x] English and Chinese review text remain deterministic and the next-step
  text clearly treats the report as an advisory review gate.
- [x] Existing metric, Guinier, detector, table, and export behavior remains
  unchanged; focused, SAXS, structured verifier, and checkpoint evidence are
  recorded.

## Implementation plan

1. Add RED tests for top-level and batch data-quality review text, missing data,
   bilingual output, and payload immutability.
2. Implement `_data_quality_review_text(payload, language)` using only existing
   report mappings and existing review message plumbing.
3. Compose its risk/next text with the existing metric/Guinier/detector review
   channels and run focused/SAXS/task verification.
4. Update durable memory and checkpoint only the explicit allowlist.

## Verification

```powershell
python -m pytest -q tests/test_saxs_results_table_service.py tests/test_saxs_data_quality_dataframe.py tests/test_saxs_mode_evidence_propagation.py --basetemp C:\Temp\PolyNexus_saxs_data_quality_workbench
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_data_quality_workbench_verify'; python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-data-quality-workbench-visibility.md --changed --types; $exit=$LASTEXITCODE; Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue; exit $exit
git diff --check
```

Actual evidence on 2026-07-28:

- TDD RED: the malformed-top-level/batch-boundary test failed because batch
  reports were repeated as top-level details; the raw-reference assertion also
  failed before the formatter exposed that existing field.
- TDD GREEN/focused matrix: `59 passed`.
- Structured verifier with external basetemp exited `0`: task/memory checks,
  Ruff, compile/type baseline, quality `283`, preprocessing `106`, and
  whitespace all passed.
- No full/boundary verifier was run for this presentation-only slice; exact
  full SAXS coverage remains a follow-up beyond the task-scoped matrix.
- The implementation and its explicit task/spec/plan allowlist were
  checkpointed in `fb76039`; no push was performed.
- A later documentation-only reconciliation verifier hit the pre-existing
  `tests/_tmp_phase3` `.pyc` WinError 5 permission lock after task validation;
  this does not invalidate the original task-scoped pass recorded above.

## Scientific limitation

Workbench text reports provenance and emitted quality evidence only. It does
not decide whether a curve supports a physical claim or publication.

## Explicit changed-file allowlist

- `docs/agent/tasks/2026-07-28-saxs-data-quality-workbench-visibility.md`
- `docs/superpowers/specs/2026-07-28-saxs-data-quality-workbench-visibility-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-data-quality-workbench-visibility.md`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_results_table_service.py`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
