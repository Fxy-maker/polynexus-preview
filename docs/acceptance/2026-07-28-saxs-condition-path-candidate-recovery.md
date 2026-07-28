# SAXS condition path-candidate recovery acceptance

Date: 2026-07-28

## Scope

The path parser now evaluates every directory component for a path-search
condition pattern until a candidate passes the existing numeric conversion and
validator. This repairs paths nested below pytest basetemp names without
changing context/header precedence or condition semantics.

## Evidence

- TDD RED: the two directory-source/metadata regressions reported
  `unresolved` under the pytest basetemp parent.
- Focused GREEN: `5 passed in 0.29s`.
- Exact sorted SAXS recheck: `518 passed, 6 warnings in 201.93s`, exit code
  `0`.
- Warnings were the existing Arial CJK glyph and SAXS geometry-header fallback
  warnings.
- Task-scoped verifier without changed-file lint passed: Pyright `0 errors, 0
  warnings, 0 informations`, quality `287`, preprocessing `106`, compile,
  whitespace, task, and memory checks passed.
- The required `--changed --types` variant exited `1` on ten pre-existing Ruff
  findings in `io.py` (`E402`, `E741`, `F401`). Targeted Ruff with those
  baseline rules ignored and `py_compile` passed; unrelated lint cleanup was
  intentionally excluded.
- Storage report/dry-run: `530` artifacts, `202` eligible, `328` protected,
  `0` removed. No `--apply` was run.

## Scientific and scope limits

No condition is inferred or fabricated. Rejected candidates remain rejected;
the first valid candidate under the existing pattern order is used. Source,
source key, confidence, labels, and unresolved keys keep their existing
contracts.
