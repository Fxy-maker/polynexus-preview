---
task_id: 2026-08-01-saxs-ai-sequence-rescue-mode-boundary
kind: scientific-cross-module
status: completed
date: 2026-08-01
title: Enforce SAXS sequence rescue candidate mode boundary
---

# SAXS AI sequence rescue mode boundary

## Goal

Prevent sequence-rescue candidates from crossing the SAXS AI summary/prompt
boundary for static, strain, unsupported, or missing modes.

## Non-goals

- no rescue calculation, candidate execution, interpolation, threshold,
  quality-level, physical-gate, publication, or mode-selection change;
- no raw q/I, detector pixels, source paths, real data, GUI, export, memory,
  scratch, or storage change.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`: existing summary sanitizer;
- `tests/test_saxs_ai_summary_context.py`: direct mode-boundary regression;
- this task's spec, plan, task card, and acceptance record.

## Acceptance criteria

- [x] Temperature candidates remain available after sanitization.
- [x] Static, strain, unsupported, and missing modes omit sequence candidates.
- [x] Existing raw-field exclusion and strict JSON behavior remain unchanged.
- [x] Focused tests, complete SAXS matrix, structured verifier, storage dry-run,
      diff audit, and explicit checkpoint are recorded.

## Implementation plan

1. Add and run the direct non-temperature sanitizer RED regression.
2. Add the normalized temperature-only guard to the existing sanitizer.
3. Run focused and complete SAXS verification plus storage dry-run.
4. Review the allowlist and create one local checkpoint.

## TDD evidence

- RED: the direct static/strain sanitizer regression failed because candidates
  crossed the boundary without a mode check.
- GREEN: summary/Advisor/prompt focused regression passed `24`.

## Verification evidence

- Complete SAXS matrix: `724 passed, 6 warnings in 480.18s`, exit code `0`.
- Structured verifier exited `0`: quality `297 passed`, preprocessing `106
  passed`, task/memory, Ruff, compile, type baseline, and whitespace checks
  passed.
- Storage report and clean dry-run: `150` artifacts,
  `34,459,624,456` total bytes, `eligible_bytes=0`, `removed=0`, and
  `failures=0`. No `test_storage.py --apply` was executed.
- `git diff --check` is required immediately before checkpointing.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_summary_context.py tests/test_advisor.py tests/test_saxs_prompt_builder.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-08-01-saxs-ai-sequence-rescue-mode-boundary.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

Storage commands are dry-run only; `test_storage.py --apply` is not authorized.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_ai_rescue.py`
- `tests/test_saxs_ai_summary_context.py`
- `docs/superpowers/specs/2026-08-01-saxs-ai-sequence-rescue-mode-boundary-design.md`
- `docs/superpowers/plans/2026-08-01-saxs-ai-sequence-rescue-mode-boundary.md`
- `docs/agent/tasks/2026-08-01-saxs-ai-sequence-rescue-mode-boundary.md`
- `docs/acceptance/2026-08-01-saxs-ai-sequence-rescue-mode-boundary.md`
