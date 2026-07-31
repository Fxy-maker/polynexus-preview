---
kind: acceptance
status: accepted
date: 2026-07-31
title: Real evaluation output isolation
task: docs/agent/tasks/2026-07-31-real-eval-output-isolation.md
---

# Acceptance record

## Scope

The EvalRunner can now forward a caller-selected external output directory to
the existing engine pipeline. This is a test/evaluation safety control only.

## Scientific boundary

No result, score, assignment, axis calibration, Xc state, figure role, or
publication decision changes. `vendor_unreviewed` remains unreviewed.

## Verification record

TDD RED:

```text
python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py -k output_isolation -vv
1 failed, 6 deselected in 0.45s; exit code 1
```

The failure was the expected pre-fix contract mismatch: the fake engine
received `output_dir=""` instead of the case's external directory.

TDD GREEN:

```text
python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py -k output_isolation -vv
1 passed, 6 deselected in 0.47s; exit code 0
```

Focused matrix:

```powershell
python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py tests/eval/test_runner_real_nmr.py -vv
8 passed in 143.03s (0:02:23); exit code 0
```

Remaining required checks:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-real-eval-output-isolation.md --changed --types
git diff --check
```

Actual results:

- Structured verifier exit code `0`. Task-check, memory check, Ruff, compile,
  type baseline, and whitespace checks passed; quality gate reported `297
  passed in 7.83s`; preprocessing reported `106 passed in 2.16s`.
- `git diff --check` exit code `0`.

## Explicit checkpoint scope

The checkpoint is limited to these six files:

- `tests/eval/runner.py`
- `tests/eval/test_nmr_vendor_real_case_registry.py`
- `docs/superpowers/specs/2026-07-31-real-eval-output-isolation-design.md`
- `docs/superpowers/plans/2026-07-31-real-eval-output-isolation.md`
- `docs/agent/tasks/2026-07-31-real-eval-output-isolation.md`
- `docs/acceptance/2026-07-31-real-eval-output-isolation.md`

Parallel SAXS changes, memory files, real input data, and scratch directories
remain untouched.

No storage apply is part of this task.
