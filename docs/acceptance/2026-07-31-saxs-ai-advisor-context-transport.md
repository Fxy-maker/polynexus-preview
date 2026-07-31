---
task_id: 2026-07-31-saxs-ai-advisor-context-transport
status: accepted-automated
date: 2026-07-31
---

# SAXS AI Advisor context transport acceptance

## Delivered boundary

`Advisor._normalize_case()` now retains a mapping-valued optional
`saxs_ai_context`, so the real `Advisor.advise()` path passes the previously
implemented summary-only context to `PromptBuilder`. Non-mapping values become
an empty context. The existing prompt sanitizer remains the raw-data boundary.

No model provider, intent authority, candidate execution, configuration
mutation, SAXS threshold, quality level, physical gate, rescue policy,
publication role, Figure, Manifest, or Export behavior changed.

## Verification evidence

- RED reproduced the dropped context through the actual Advisor prompt and the
  missing non-mapping contract.
- Focused Advisor/prompt/AI suite: `44 passed`, exit `0`.
- Exact SAXS matrix: `678 passed, 6 warnings`, exit `0`.
- Structured verifier: exit `0`; quality `297 passed`, preprocessing `106
  passed`, plus Ruff/compile/type/memory/task/whitespace checks.
- Storage report and clean were non-destructive dry-runs: `58` artifacts,
  `1,368,590,431` bytes total, `7,873` eligible bytes, `0` removed.
- `git diff --check`: exit `0`.

## Remaining gates

The next AI phase is still intent-generation quality and candidate replay
evidence. Any generated payload must continue through the existing SAXS
validator, bounded candidate plan, physical/quality decision gates, and
confirmation policy.

## Checkpoint

The explicit allowlist checkpoint is created locally with
`scripts/auto_commit.py`; no push or merge is performed.
