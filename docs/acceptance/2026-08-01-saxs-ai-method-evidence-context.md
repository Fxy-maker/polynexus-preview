---
kind: acceptance
status: recorded
date: 2026-08-01
title: SAXS AI 1D method evidence context
task: docs/agent/tasks/2026-08-01-saxs-ai-method-evidence-context.md
---

# Acceptance Record

## Automated Evidence

- Focused method/Advisor/prompt regression returned `18 passed in 0.59s`, exit
  code `0`.
- Combined summary/live/Advisor/prompt/audit regression returned `28 passed in
  6.27s`, exit code `0`.
- Complete SAXS matrix returned `713 passed, 6 warnings in 568.82s`, exit code
  `0`. The six warnings are the existing Arial CJK glyph warnings and EDF
  geometry-default warnings.
- Structured verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report and dry-run clean exited `0` in non-destructive mode: `145`
  artifacts, `34,459,621,656` total bytes, `15,743,185,346` eligible bytes,
  `failures=[]`, and `removed=0`. No `test_storage.py --apply` ran.
- `git diff --check` exited `0`.

## Contract Result

The existing generic `metric_evidence` projection preserves Guinier, Porod,
Kratky, invariant, and lamellar entries for Static, Temperature, and Strain
summary contexts. The projected values remain strict JSON, candidate-only, and
subject to physical validation. Raw q/I, detector pixels, and source paths
remain excluded by the existing sanitizer.

No production code changed. This checkpoint adds focused regression coverage
for an existing contract and does not add thresholds or scientific inference.

## Remaining Gates

Real detector geometry/mask/beam-center/orientation interpretation, scientific
meaning of temperature/strain trends, and final publication/release approval
remain separate human and instrument-aware gates.
