# Current full-verifier regression repair acceptance

Date: 2026-07-30
Task: `docs/agent/tasks/2026-07-30-full-verifier-regressions.md`

## Root-cause repair

- IR mapping tests now assert the empty `policy_version` carried by the
  JSON-safe scientific review snapshot.
- SAXS Results Workbench tests now include the intentional
  `Scientific review: Not applicable | reason=not_applicable` suffix for a
  non-gated SAXS mode.
- The real published-run lifecycle selects a `ready` figure for Editor
  persistence. Error-status diagnostic entries remain present and visible;
  they are not edited as if they were ready documents.

## Focused verification

- `tests/test_ir_mapping.py`: `13 passed in 3.46s`, exit code `0`.
- The two affected MainWindow tests: `2 passed in 6.62s`, exit code `0`.
- SAXS strain lifecycle: `1 passed, 12 deselected in 20.52s`, exit code `0`.

## Task-scoped verification

- `python scripts/verify.py --task docs/agent/tasks/2026-07-30-full-verifier-regressions.md --changed --types`: passed; quality `290`, preprocessing `106`, Ruff, compile, type baseline, memory, task, and whitespace checks passed.
- `python -m pytest -q --ignore=tests/_tmp_phase3`: `3091 passed, 18 skipped, 12 warnings in 1986.68s (0:33:06)`. The launcher did not persist the wrapper exit code, so this records the pytest summary only and does not claim an observed exit code.
- `git diff --check`: passed.

The current-HEAD full verifier before this repair had
`3080 passed, 18 skipped, 12 warnings` and five failures. Four were the
contract/test mismatches repaired here. The remaining untracked
`tests/_tmp_phase3/test_visual_audit_capture.py` failure is an obsolete local
scratch test and is intentionally excluded from this task.

## Boundary

No scientific formula, threshold, reviewer value, publication role, error
entry visibility, real dataset, or test-storage artifact was changed.
