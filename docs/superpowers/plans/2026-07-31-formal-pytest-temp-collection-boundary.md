# Formal pytest temporary-directory collection boundary plan

## Goal

Prevent repository-local temporary diagnostics from contaminating the formal
pytest release gate while preserving explicit direct invocation for debugging.

## Tasks

1. Reproduce the baseline: confirm the formal collector includes
   `tests/_tmp_phase3` and record the full-gate failure.
2. Apply the single configuration change `norecursedirs = _tmp*` in
   `pytest.ini`.
3. Verify collection no longer includes `_tmp_phase3`, then run the full
   verifier with an external D: test root and capture complete stdout,
   stderr, and process outcome.
4. Run the task-scoped verifier, boundary audit, and diff check; record exact
   results and create one explicit allowlist checkpoint.

## Non-goals

- Do not edit or delete `tests/_tmp_phase3`.
- Do not change product, scientific, GUI, SAXS, NMR, IR, or Joint behavior.
- Do not apply test-storage cleanup.
