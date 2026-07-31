---
task_id: 2026-07-31-real-eval-output-isolation
kind: test-infrastructure
status: complete
date: 2026-07-31
title: Isolate real evaluation output directories
---

# Real evaluation output isolation

## Goal

Let real EvalRunner cases forward an explicit external output directory to the
engine without changing scientific or analysis semantics.

## Non-goals

- No NMR algorithm, assignment, ppm, Xc, Figure, or publication changes.
- No edits to `测试数据`, generated source outputs, or real regression data.
- No deletion, storage apply, push, merge, or deployment.

## Affected boundaries

- `tests/eval/runner.py` real-engine output forwarding.
- Existing NMR vendor registry regression and bridge test.

## Implementation plan

1. Add a fake-engine RED test for `eval_output_dir` forwarding.
2. Implement the optional forwarding at the EvalRunner boundary.
3. Re-run the real NMR registry and existing bridge, then verify and checkpoint.

## Acceptance criteria

- [x] Without `eval_output_dir`, the existing empty-string behavior remains.
- [x] With `eval_output_dir`, the exact path reaches `engine.run_pipeline`.
- [x] The registry and existing NMR bridge regressions remain green: `8 passed in 143.03s`, exit code `0`.
- [x] Real input files are unchanged and generated outputs remain external.
- [x] Task verifier and diff check pass; checkpoint creation uses the six-file allowlist below.

## Explicit changed-file allowlist

- `tests/eval/runner.py`
- `tests/eval/test_nmr_vendor_real_case_registry.py`
- `docs/superpowers/specs/2026-07-31-real-eval-output-isolation-design.md`
- `docs/superpowers/plans/2026-07-31-real-eval-output-isolation.md`
- `docs/agent/tasks/2026-07-31-real-eval-output-isolation.md`
- `docs/acceptance/2026-07-31-real-eval-output-isolation.md`

The acceptance record is also included, so the checkpoint contains six files.
Parallel SAXS, memory, real data, and scratch paths are excluded.

## Verification

```powershell
python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py tests/eval/test_runner_real_nmr.py -vv
python scripts/verify.py --task docs/agent/tasks/2026-07-31-real-eval-output-isolation.md --changed --types
git diff --check
```

## Verification evidence

- Focused matrix: `8 passed in 143.03s`, exit code `0`.
- Structured verifier: exit code `0`; quality gate `297 passed in 7.83s`, preprocessing `106 passed in 2.16s`; task-check, memory check, Ruff, compile, type baseline, and whitespace checks passed.
- `git diff --check`: exit code `0`.

## TDD evidence

- RED: `python -m pytest -q tests/eval/test_nmr_vendor_real_case_registry.py -k output_isolation -vv` -> `1 failed, 6 deselected`; the fake engine received `output_dir=""`.
- GREEN: the same command -> `1 passed, 6 deselected`.

## Explicit changed-file allowlist

- `tests/eval/runner.py`
- `tests/eval/test_nmr_vendor_real_case_registry.py`
- `docs/superpowers/specs/2026-07-31-real-eval-output-isolation-design.md`
- `docs/superpowers/plans/2026-07-31-real-eval-output-isolation.md`
- `docs/agent/tasks/2026-07-31-real-eval-output-isolation.md`
- `docs/acceptance/2026-07-31-real-eval-output-isolation.md`

Parallel SAXS, memory, real data, and scratch paths are excluded.
