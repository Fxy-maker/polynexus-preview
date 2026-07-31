---
kind: task
status: completed
date: 2026-07-31
title: Honor explicit language in Results review summaries
---

# Results review explicit language contract

## Goal

Keep Results/NMR review summaries deterministic when a caller supplies an
explicit language, regardless of the persisted GUI language, and isolate
History table tests from the user's local language setting.

## Non-goals

- Do not change scientific review decisions, evidence values, or promotion
  rules.
- Do not change the persisted application language or parallel SAXS review
  entry behavior.
- Do not edit real datasets, generated outputs, or test-storage artifacts.

## Affected boundaries

- `polynexus/gui/results_review_service.py`: NMR summary translation uses the
  existing `tr_for_language` contract.
- `tests/test_results_review_service.py` and
  `tests/test_history_table_service.py`: regression and language-state
  isolation.

## Implementation plan

1. Reproduce the language-sensitive History and NMR review failures.
2. Route NMR review labels through the requested language without changing
   evidence or gate calculations.
3. Add regression coverage for explicit language and isolate History tests.
4. Run the focused matrix, task verifier, and diff check.

## Acceptance criteria

- [x] NMR summary text uses the requested `language` for assignment, source,
  axis, vendor-axis, and Xc-gate labels.
- [x] A global Chinese language state does not change a summary requested in
  English.
- [x] History table expectations explicitly select English and restore the
  previous language.
- [x] Focused Results/History/scientific-review regression and task verifier
  pass.

## Verification

```powershell
python -m pytest -q tests/test_history_table_service.py tests/test_results_review_service.py tests/test_scientific_review.py tests/test_scientific_review_workbench.py
python scripts/verify.py --task docs/agent/tasks/2026-07-31-results-review-explicit-language.md --changed --types
git diff --check
```

## Explicit changed-file allowlist

- `polynexus/gui/results_review_service.py`
- `tests/test_history_table_service.py`
- `tests/test_results_review_service.py`
- `docs/agent/tasks/2026-07-31-results-review-explicit-language.md`

## Verification evidence

- The pre-fix focused reproduction was `5 failed, 32 passed`; two failures
  came from persisted Chinese UI language and three from ignored explicit
  `language="en"` arguments.
- Focused regression after the fix: `87 passed in 1.09s`.
- Task verifier: exit `0`; task card and memory checks passed, Ruff and
  compile passed, type baseline had no changed files, quality gate was
  `297 passed`, preprocessing gate was `106 passed`, and whitespace passed.
- `git diff --check`: passed.
