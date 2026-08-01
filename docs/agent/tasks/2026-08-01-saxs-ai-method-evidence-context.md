---
task_id: 2026-08-01-saxs-ai-method-evidence-context
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Lock 1D method evidence in SAXS AI summary context
---

# SAXS AI 1D method evidence context

## Goal

Make the existing summary-only SAXS AI contract explicitly regression-tested
for Guinier, Porod, Kratky, invariant, and lamellar evidence across Static,
Temperature, and Strain modes.

## Non-goals

- no production behavior, evidence calculation, threshold, quality-level,
  physical-gate, or publication decision change;
- no new AI inference, candidate execution, rescue, interpolation, or frame
  repair;
- no raw q/I, detector pixels, source paths, or unbounded payloads in the
  summary/prompt context;
- no changes to Figure, Manifest, Export, Workbench, real data, scratch, or
  parallel memory files.

## Affected boundaries

- `tests/test_saxs_ai_summary_context.py`: explicit 1D method-family context
  contract;
- existing `polynexus/core/saxs_engine/saxs_ai_rescue.py` summary and prompt
  sanitizer boundaries are verified but not modified;
- this task's spec, plan, acceptance record, and task card.

## Acceptance criteria

- [x] Static, Temperature, and Strain summary contexts retain all five existing
      1D method evidence entries, including level, value, and physical checks.
- [x] The projected context remains strict JSON and candidate-only with physical
      validation required.
- [x] Existing raw-field exclusion and prompt sanitizer behavior remains green.
- [x] Focused regression, SAXS matrix, structured verifier, diff, storage
      dry-run, and explicit allowlist checkpoint are recorded.

## Implementation plan

1. [ ] Add a parameterized focused regression using existing metric evidence
   fields for all three modes.
2. [ ] Run the focused test and inspect whether the current generic projection
   already satisfies the contract; do not change production code if it does.
3. [ ] Run Advisor/prompt/summary regressions and the complete SAXS matrix.
4. [ ] Run task-scoped structured verification, storage dry-runs, and diff
   audit; record exact outcomes.
5. [x] Create one explicit allowlist checkpoint containing only the test and
   four task documents.

## Evidence

- Focused method/Advisor/prompt regression: `18 passed in 0.59s`, exit code `0`.
- Combined summary/live/Advisor/prompt/audit regression: `28 passed in 6.27s`,
  exit code `0`.
- Complete SAXS matrix including this regression: `713 passed, 6 warnings in
  568.82s`, exit code `0`.
- Structured verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, plus task/memory, Ruff, compile, type-baseline, and whitespace
  checks.
- Storage report and dry-run clean both exited `0`: `145` artifacts,
  `34,459,621,656` total bytes, `15,743,185,346` eligible bytes,
  `failures=[]`, and `removed=0`. No `test_storage.py --apply` was executed.
- `git diff --check` passed. The explicit allowlist checkpoint is the final
  task step.

No production code changed: the existing generic metric-evidence projection
already satisfied the contract. This task adds regression coverage only.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py -o addopts=
python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py tests/test_saxs_prompt_builder.py tests/test_advisor.py tests/test_saxs_ai_acceptance_audit_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-method-evidence-context.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Pytest counts only with a complete summary and exit code `0`. Storage commands
are dry-run only; `test_storage.py --apply` is not authorized.

## Explicit changed-file allowlist

- `tests/test_saxs_ai_summary_context.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-method-evidence-context-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-method-evidence-context.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-method-evidence-context.md`
- `docs/acceptance/2026-08-01-saxs-ai-method-evidence-context.md`

Parallel production, memory, GUI, real-data, generated-output, scratch, and
test-storage changes remain outside this task.
