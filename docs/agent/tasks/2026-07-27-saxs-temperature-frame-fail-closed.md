# SAXS Temperature Frame Fail-Closed Isolation

## Goal

Make the temperature 1D Guinier path degrade per frame when invariant or
reference calculations encounter malformed q/I data, so unaffected frames are
still analyzed and every loss remains explicit.

## Non-goals

- Do not change Guinier fitting, q-window selection, qRg rules, or physical
  thresholds.
- Do not interpolate, repair, reorder, delete, or copy frames.
- Do not select a neighboring frame as a replacement reference.
- Do not change Porod, Kratky, invariant, lamellar algorithms, AI rescue,
  publication roles, or GUI event logic.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- This task's design/spec/plan and durable memory at task completion.

## Acceptance criteria

- [x] A failure in a middle frame's invariant calculation does not abort the
  temperature series; later frames retain their normal Guinier evidence.
- [x] A failed or non-finite frame invariant remains unavailable and carries a
  stable diagnostic warning; it is never replaced by zero or another frame's
  value.
- [x] A failure in the initial reference invariant or long-period calculation
  does not abort later frame analysis and leaves the reference-dependent value
  unavailable rather than inventing a baseline.
- [x] Temperature sorting, original `source_index`, frame count, sequence
  missingness, and existing quality levels remain unchanged.
- [x] Existing good-data and `analyze_single()` failure behavior remains green.
- [x] TDD RED is observed for the new middle-frame and reference-failure
  regressions before production code changes.
- [x] The structured task verifier and relevant SAXS matrix pass.
- [x] One checkpoint is created with the explicit changed-file allowlist.

## Implementation plan

1. Add focused failing tests that inject invariant/reference failures and assert
   continuation, unavailable values, stable warnings, and preserved mapping.
2. Run those tests and record the expected RED failures.
3. Add minimal guarded helpers/call sites in `analyze_temperature_series()`;
   preserve existing calculations and output contracts.
4. Run the focused tests, the temperature Guinier/quality consumer matrix, and
   the complete SAXS matrix.
5. Run the structured verifier, review the cumulative diff and explicit
   allowlist, update durable memory, and create one checkpoint.

## Verification

The focused and complete SAXS commands below use a dedicated external
basetemp. The structured verifier is the authoritative task-level gate.

```powershell
$env:PYTEST_ADDOPTS='--basetemp=C:\Temp\PolyNexus_saxs_temperature_fail_closed'
python -m pytest -q tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py
python -m pytest -q tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_status.py tests/test_saxs_mode_evidence_propagation.py tests/test_saxs_workbench_series_evidence.py tests/test_saxs_export_bundle.py
python scripts/verify.py --task docs/agent/tasks/2026-07-27-saxs-temperature-frame-fail-closed.md --changed --types
git diff --check
```

## Known limitations

This task only isolates failures at the temperature-series boundary. It does
not establish real-data scientific acceptance, replace expert review, or
authorize automatic rescue or publication.

## Verification result

- TDD RED: the two new regressions failed at the expected unguarded reference
  and middle-frame invariant calls.
- TDD GREEN: the two new regressions passed (`2 passed`).
- Temperature Guinier/status matrix: `20 passed`.
- Temperature consumer matrix (mode propagation, Workbench, Export):
  `44 passed`.
- Complete SAXS matrix: `346 passed, 4 warnings`; warnings are the existing
  Arial CJK glyph warnings from figure layout.
- Structured task verifier with a repository-local dedicated basetemp passed:
  task/memory checks, Ruff, compile/type baseline, quality `282`, preprocessing
  `106`, and whitespace checks. An attempted `C:\Temp` basetemp was blocked by
  Windows `WinError 5` during unrelated test temp-directory cleanup (`229
  passed, 53 errors`); it is environmental evidence only and not used as the
  code verdict.

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_temperature_guinier_evidence.py`
- `docs/agent/tasks/2026-07-27-saxs-temperature-frame-fail-closed.md`
- `docs/superpowers/specs/2026-07-27-saxs-temperature-frame-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-27-saxs-temperature-frame-fail-closed.md`

## Pre-existing workspace changes intentionally excluded

The tracked full-software GUI audit and its concurrent durable-memory edits
were already modified outside this task. They remain untouched and are
excluded from this checkpoint; the task's own evidence is complete in this
card and the design/plan files.
