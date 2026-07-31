---
task_id: 2026-07-31-saxs-live-advisor-summary-context
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Bind live SAXS state to Advisor summary context
---

# SAXS live Advisor summary context

## Goal

Make the real `ParameterOrchestrator` state expose the existing summary-only
SAXS evidence to `Advisor`, so model prompts can reason over evidence without
receiving raw analysis data.

## Non-goals

- No model-provider or new prompt call.
- No intent generation, candidate execution, replay, configuration mutation,
  rescue, or automatic acceptance.
- No q/I, detector-pixel, source-path, interpolation, or threshold changes.
- No non-SAXS, Figure, Manifest, Export, or publication changes.
- No edits to real data, generated output, scratch, storage, or parallel memory.

## Affected boundaries

- `polynexus/orchestrator_state.py`: live SAXS state projection.
- `tests/test_saxs_ai_live_context.py`: static/temperature/strain and failure
  boundary regressions.

## Acceptance criteria

- [x] Static SAXS state uses `engine.result` for the summary context.
- [x] Temperature and strain state use their existing series result and retain
  condition/source-index evidence.
- [x] The context is candidate-only, requires physical validation, and omits
  raw q/I, detector pixels, and source paths.
- [x] Projection failure returns an empty context and does not abort state
  construction.
- [x] Non-SAXS state has no new SAXS context field.

## Implementation plan

1. Add RED tests for static, temperature, strain, raw-field exclusion, and
   projection failure.
2. Select the existing active SAXS result and call the existing summary-only
   context builder from `_build_agent_state()`.
3. Run focused Advisor/prompt regressions, the SAXS matrix, structured
   verification, storage dry-runs, and diff check.
4. Create an explicit allowlist checkpoint containing only this task's files.

The strain regression follows the existing summary contract: temperature
projects `guinier_sequence_evidence`, while strain asserts the available
`metric_evidence.guinier` projection. No production summary contract was
expanded for this task.

## Verification

```powershell
python -m pytest -q tests/test_saxs_ai_live_context.py -o addopts=
python -m pytest -q tests/test_saxs_ai_live_context.py tests/test_advisor.py tests/test_saxs_prompt_builder.py tests/test_saxs_ai_summary_context.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-live-advisor-summary-context.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

All pytest claims require a complete summary and exit code `0`. Storage
commands are dry-run only; `test_storage.py --apply` is not authorized.

Evidence:

- Focused live-context: `5 passed in 1.26s`.
- Advisor/orchestrator/PromptBuilder regressions: `103 passed in 48.27s`.
- Ruff and compileall passed for the changed production/test files.
- Exact SAXS file matrix: `685 passed, 6 warnings in 561.43s`, exit code `0`.
- Structured verifier: task card, memory, Ruff, compile, quality `297 passed`,
  preprocessing `106 passed`, and whitespace checks passed; exit code `0`.
- Storage report and `clean --older-than-hours 24 --json` were both dry-run:
  `63` artifacts, `1,368,593,231` bytes, `13` emergency-eligible artifacts
  (`18,784` bytes), and `removed_count=0`. No `--apply` was run.

## Changed-file allowlist

- `polynexus/orchestrator_state.py`
- `tests/test_saxs_ai_live_context.py`
- `docs/superpowers/specs/2026-07-31-saxs-live-advisor-summary-context-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-live-advisor-summary-context.md`
- `docs/agent/tasks/2026-07-31-saxs-live-advisor-summary-context.md`
