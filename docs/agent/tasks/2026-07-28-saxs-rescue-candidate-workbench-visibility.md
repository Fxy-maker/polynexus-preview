# Task: SAXS rescue-candidate visibility in Workbench

**Status:** complete; checkpoint pending

## Goal

Expose the existing deterministic temperature sequence-rescue candidates in
the public parameters payload and Results Workbench as read-only audit
evidence, so a potentially recoverable frame is visible without being treated
as rescued or accepted.

## Affected boundaries

- `polynexus/core/saxs_batch_helpers.py` and `polynexus/core/saxs.py`: copy the
  existing candidate list as an additive quality/evidence field and expose it
  from the temperature parameters branch.
- `polynexus/gui/saxs_results_table_service.py`: format candidate-only review
  text from the emitted payload.
- `tests/test_saxs_batch_parameters.py` and
  `tests/test_saxs_workbench_series_evidence.py`: transport and review
  regressions.
- Task/spec/plan and durable SAXS memory records.

## Non-goals

- No AI model calls, candidate application, deterministic rerun, interpolation,
  frame fabrication, or source-data mutation.
- No new physical threshold, quality level, rescue acceptance rule, or
  publication role.
- No changes to candidate generation or validation semantics.
- No propagation of a temperature candidate into strain/static rows.

## Implementation plan

1. Add RED regressions for detached temperature candidate transport and
   candidate-only Workbench review, including malformed and localized inputs.
2. Extend the existing quality-copy allowlist and temperature parameters branch
   without changing candidate generation; add a pure review formatter that
   consumes only valid public mappings.
3. Run focused tests, the exact SAXS matrix, task-scoped verifier, and diff
   checks; record any full/boundary limitation.
4. Update durable memory and create one explicit-allowlist checkpoint.

## Contract

- `TempSeriesResult.sequence_rescue_candidates`, when present, is deep-copied
  into the temperature `get_parameters()` payload under the same public key.
- Workbench review reports only well-formed candidate mappings. It shows the
  candidate count, candidate IDs, frame/source information, existing
  `candidate_only`/`requires_validation` state, and existing reason codes.
- Missing or malformed candidate values remain absent and never create a
  positive quality or rescue claim. The full nested list remains in
  Diagnostics/History/Export through existing payload paths.

## Acceptance criteria

- [x] Temperature parameters transport existing candidates without mutating the
      series or source list.
- [x] Workbench exposes candidate-only review text with frame/source and
      validation-required wording.
- [x] Missing, malformed, and empty candidate lists produce no rescue claim;
      candidate-only text never says applied, accepted, or physically valid.
- [x] Existing static/strain/Guinier/metric/detector review behavior remains
      unchanged.
- [x] Focused tests, exact SAXS matrix, task verifier, and diff checks pass;
      full/boundary status is reported separately if not run.

## Verification

```powershell
python -m pytest -q tests/test_saxs_batch_parameters.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_results_table_service.py --basetemp C:\Temp\PolyNexus_saxs_rescue_candidate_redgreen
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_rescue_candidate_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-rescue-candidate-workbench-visibility.md --changed --types
$exit = $LASTEXITCODE
Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
exit $exit
git diff --check
```

## Verification result

- TDD RED: `2 failed, 1 passed`; the expected failures were missing parameter
  transport and missing Workbench candidate review text.
- TDD GREEN: `3 passed`.
- Focused consumer matrix: `97 passed`.
- Exact SAXS file matrix: `393 passed, 6 warnings`. Warnings are the existing
  Arial CJK glyph and EDF geometry-header warnings.
- Full/boundary verification was not run for this presentation/transport
  slice; no full/boundary pass is claimed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_batch_helpers.py`
- `polynexus/core/saxs.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_batch_parameters.py`
- `tests/test_saxs_workbench_series_evidence.py`
- `docs/agent/tasks/2026-07-28-saxs-rescue-candidate-workbench-visibility.md`
- `docs/superpowers/specs/2026-07-28-saxs-rescue-candidate-workbench-visibility-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-rescue-candidate-workbench-visibility.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`
