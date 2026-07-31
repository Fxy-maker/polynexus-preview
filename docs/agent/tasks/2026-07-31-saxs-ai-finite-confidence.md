---
task_id: 2026-07-31-saxs-ai-finite-confidence
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Reject non-finite SAXS AI confidence
---

# SAXS AI finite confidence boundary

## Goal

Prevent non-finite model confidence values from entering the Advisor decision
path; use the existing deterministic provider fallback instead.

## Non-goals

- No new model call, retry, prompt field, confidence policy, or candidate rule.
- No SAXS q/I, detector, quality, physical-gate, rescue, rerun, or apply change.
- No changes to memory, real data, generated outputs, scratch, storage, or
  parallel GUI files.

## Affected boundaries

- `rag/advisor.py`: finite confidence normalization.
- `tests/test_advisor.py`: non-finite provider regression.

## Acceptance criteria

- [x] `confidence="NaN"` fails closed to normalized
      `provider_unavailable` advice with `llm_used=False` and empty changes.
- [x] Finite confidence values keep current clamping behavior.
- [x] Existing Advisor/SAXS AI/preprocessing regressions remain green.
- [x] TDD RED/GREEN, exact SAXS matrix, structured verification, storage
      dry-runs, diff check, and explicit allowlist checkpoint are recorded.

## Evidence

- TDD RED: `confidence="NaN"` returned ordinary advice with empty diagnosis
  instead of the existing provider fallback.
- Focused Advisor/SAXS context/prompt suite: `20 passed in 1.52s`, exit code
  `0`.
- Extended AI/preprocess/SAXS handoff matrix: `82 passed in 1.94s`, exit code
  `0`.
- Exact SAXS matrix: `685 passed, 6 warnings in 388.56s`, exit code `0`.

The six warnings are the existing Arial glyph and EDF geometry-header
warnings. This task does not claim a new full/boundary release pass.

## Implementation plan

1. Add the non-finite provider regression and observe the expected RED.
2. Add the minimal `math.isfinite()` guard in `_normalize_advice()`.
3. Run focused/AI/preprocess/SAXS verification and checkpoint only the listed
   files.

## Verification

```powershell
python -m pytest -q tests/test_advisor.py::test_advisor_falls_back_on_nonfinite_provider_confidence -o addopts=
python -m pytest -q tests/test_advisor.py tests/test_saxs_ai_live_context.py tests/test_saxs_ai_summary_context.py tests/test_saxs_prompt_builder.py -o addopts=
python -m pytest -q -o addopts= (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-ai-finite-confidence.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

All pytest claims require complete summaries and exit code `0`. Storage is
dry-run only; `test_storage.py --apply` is not authorized.

## Changed-file allowlist

- `rag/advisor.py`
- `tests/test_advisor.py`
- `docs/superpowers/specs/2026-07-31-saxs-ai-finite-confidence-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-ai-finite-confidence.md`
- `docs/agent/tasks/2026-07-31-saxs-ai-finite-confidence.md`
