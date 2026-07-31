# SAXS Live Advisor Summary Context Design

## Goal

Pass the existing summary-only SAXS quality and physical evidence from the
live `ParameterOrchestrator` state into the existing Advisor/PromptBuilder
path.

## Scope

When building an Advisor state for SAXS, select the already-computed result
for the active mode and call `build_saxs_ai_summary_context()`. Temperature
and strain series use their existing series result; static uses the engine's
existing result. The resulting strict-JSON envelope is attached as
`saxs_ai_context`, which the existing Advisor transport and prompt sanitizer
already understand.

## Non-goals

- No new model call, prompt policy, intent schema, candidate, replay, or apply
  behavior.
- No raw q/I, detector pixels, source paths, interpolation, frame repair, or
  new physical/quality threshold.
- No changes to SAXS calculations, evidence levels, physical gates, Figure,
  Manifest, Export, or non-SAXS state.

## Failure behavior

The context builder remains the only summary projection boundary. If the
selected result is unavailable or projection raises a recoverable value/type
error, the state carries an empty context and the Advisor retains its existing
no-context behavior. The model never receives raw analysis inputs through this
change.

## Acceptance criteria

1. Static SAXS state carries a summary context from `engine.result`.
2. Temperature and strain state select their existing series result and retain
   source-index/condition evidence.
3. Contexts are marked candidate-only and physical-validation-required, and
   contain no q/I, detector-pixel, or path fields.
4. Non-SAXS state remains unchanged and projection failure fails closed.

## Verification

- RED/GREEN live-state tests in `tests/test_saxs_ai_live_context.py`.
- Existing Advisor/prompt/summary-context regressions.
- SAXS matrix, structured task verifier, storage dry-run, and diff check.
