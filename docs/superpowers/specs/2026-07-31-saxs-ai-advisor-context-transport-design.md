---
title: Transport SAXS AI summary context through Advisor
date: 2026-07-31
status: approved
---

# SAXS AI Advisor context transport

## Decision

Preserve the optional `saxs_ai_context` field in `Advisor._normalize_case()` so
the real `Advisor -> PromptBuilder` path can consume the already-defined
summary-only SAXS context. `PromptBuilder` remains the trust boundary and
filters the context through `sanitize_saxs_ai_summary_context()` before any
prompt text is built.

This task does not call a model, generate an intent, execute candidates, or
change any SAXS analysis, quality, physical, rescue, or publication behavior.

## Acceptance

- A SAXS case carrying a summary context retains it in the normalized case and
  the actual advisor prompt contains the summary section.
- The no-context Advisor path remains unchanged.
- Prompt-side summary sanitization remains authoritative, so transport cannot
  widen the raw-data boundary.
- Existing Advisor, prompt, preprocessing, and SAXS tests remain green.
