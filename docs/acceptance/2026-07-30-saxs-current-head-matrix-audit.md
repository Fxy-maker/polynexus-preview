---
kind: acceptance
status: accepted
date: 2026-07-30
title: Current-head SAXS matrix audit after Workbench provenance checkpoint
task: docs/agent/tasks/2026-07-30-saxs-current-head-matrix-audit.md
---

# Acceptance Record

## Scope

This audit verifies the current checkout after `fd9bb3d` without changing SAXS
production behavior. It executes all 99 repository test files matching
`tests/test_saxs_*.py` with offscreen Qt and a writable workspace basetemp.

## Evidence

- Fresh SAXS-only matrix: `631 passed, 6 warnings in 409.19s`, exit code `0`.
- Warnings are the existing Arial CJK glyph warnings and EDF geometry-default
  warnings; no SAXS test failure was reported.
- The first attempt was stopped by the tool window after about 5 seconds with
  exit `124`, without a pytest summary. A process audit found no residual
  Python/pytest process, so it is classified as an execution interruption and
  not counted as evidence.
- Structured verification returned exit code `0`: task/memory checks, Ruff,
  compile, type baseline, quality `290 passed`, preprocessing `106 passed`,
  and whitespace checks passed.
- `git diff --check` passed.

## Limitations

This is fresh SAXS-only regression evidence, not a full-repository
full/boundary or release approval. Native Qt full-suite stability, restarted
GUI visual review, real-detector calibration/mask interpretation,
reviewer-owned scientific meaning, and final publication/release authorization
remain separate gates. No test-storage apply or data deletion was performed.
