# SAXS AI Finite Confidence Design

## Problem

The Advisor fallback boundary now catches normalization exceptions, but Python
accepts `"NaN"` and `"Infinity"` through `float()`. A provider can therefore
return a non-finite confidence that is not a meaningful evidence value.

## Goal

Require normalized Advisor confidence to be finite before it can reach the
existing candidate/decision path. Non-finite provider values must reuse the
existing `provider_unavailable` fallback.

## Scope and authority

- Add only a finite-number guard in `Advisor._normalize_advice()`.
- The live `Advisor.advise()` fallback remains the authority for provider
  failures; no new error payload or retry is introduced.
- `LLMCancelledError`, SAXS summary context, physical gates, candidate
  validation, deterministic rerun, and apply policy remain unchanged.
- Direct normalization callers receive a `ValueError` for non-finite input;
  live provider calls convert that error to the existing fallback.

## Acceptance

1. A provider response with `confidence="NaN"` fails closed to
   `provider_unavailable`, `llm_used=False`, and no changes.
2. Finite numeric confidence values retain existing clamping behavior.
3. Existing Advisor, SAXS AI, preprocessing, and cancellation regressions
   remain green.
