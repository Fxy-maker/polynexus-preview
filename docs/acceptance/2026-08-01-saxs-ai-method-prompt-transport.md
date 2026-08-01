---
kind: acceptance
status: recorded
date: 2026-08-01
title: SAXS AI 1D method evidence in Advisor prompt
task: docs/agent/tasks/2026-08-01-saxs-ai-method-prompt-transport.md
---

# Acceptance Record

## Automated Evidence

- `python -m pytest -q tests/test_advisor.py tests/test_saxs_prompt_builder.py
  tests/test_saxs_ai_summary_context.py tests/test_saxs_ai_live_context.py
  -o addopts=` returned `25 passed in 2.61s`, exit code `0`.
- The fresh complete SAXS matrix returned `713 passed, 6 warnings in 482.99s`, exit
  code `0`.
- Structured verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report and dry-run clean exited `0` in non-destructive mode: `145`
  artifacts, `34,459,621,656` total bytes, `eligible_bytes=0`, `failures=[]`,
  and `removed=0`. No `test_storage.py --apply` ran.
- `git diff --check` exited `0`.

## Contract Result

The actual Advisor prompt retained all five existing 1D method evidence keys:
Guinier, Porod, Kratky, invariant, and lamellar. The prompt also retained
`candidate_only=true` and `physical_validation_required=true` after summary
sanitization. Existing model, candidate, rescue, and publication authority was
unchanged, and no production code changed.

## Remaining Gates

Real scientific interpretation, detector geometry/mask/beam-center/orientation
review, human temperature/strain meaning review, and final publication/release
approval remain outside this transport regression.
