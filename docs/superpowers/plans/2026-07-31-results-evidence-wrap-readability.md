# Implementation Plan: Results Evidence Wrap Readability

## Scope

One shared Qt presentation fix and one focused regression. No scientific or
analysis-layer changes.

## Steps

1. Add `tests/test_wrapped_evidence_label.py` with the long evidence scenario
   and run it to confirm the current policy loses height-for-width.
2. Add a small helper or policy update in
   `polynexus/gui/widgets/wrapped_evidence_label.py` so callers can preserve
   the current horizontal policy while enabling height-for-width.
3. Apply that contract in the existing Results label setup without changing
   text generation.
4. Run the focused test and the existing Results/Workbench GUI tests.
5. Run the structured verifier and `git diff --check`; inspect the cumulative
   diff and create one explicit allowlist checkpoint.
6. Record exact command results and remaining native/scientific limitations in
   the acceptance record and durable active-work state.

## Changed-file allowlist

- `polynexus/gui/widgets/wrapped_evidence_label.py`
- `tests/test_wrapped_evidence_label.py`
- `docs/agent/tasks/2026-07-31-results-evidence-wrap-readability.md`
- `docs/superpowers/specs/2026-07-31-results-evidence-wrap-readability-design.md`
- `docs/superpowers/plans/2026-07-31-results-evidence-wrap-readability.md`
- `docs/acceptance/2026-07-31-results-evidence-wrap-readability.md`

Pre-existing modified memory files, untracked test directories, and native
evidence directories are intentionally excluded.

## Recorded outcome

- TDD RED: `1 failed` because the Results `Ignored/Preferred` policy disabled
  `heightForWidth`.
- Focused GREEN and Results GUI matrix: `52 passed in 2.72s`.
- Ruff and compile checks passed.
- Structured verifier passed with quality `297 passed` and preprocessing `106
  passed`, plus task/memory, Ruff, compile, type-baseline, and whitespace
  checks.
- Native Windows recheck: `2 passed, 15 deselected in 71.69s`, exit code `0`.
- `git diff --check`: exit code `0`.
