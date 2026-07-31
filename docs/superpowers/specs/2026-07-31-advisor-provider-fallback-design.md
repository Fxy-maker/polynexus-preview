# Advisor Provider Failure Fallback Design

## Context

`Advisor.advise()` already falls back to the deterministic mock response when
the provider call or response parsing raises an ordinary exception. Response
normalization was outside that protected boundary, so a malformed provider
payload could escape instead of following the existing fallback contract.

## Decision

Normalize a parsed provider response inside the same ordinary-exception
boundary as the provider call and parser. If normalization fails, return the
existing mock response with `llm_used=False` and the provider failure reason.
Preserve `LLMCancelledError` as a control-flow signal and re-raise it without
fallback, so user cancellation is not reported as provider failure.

## Invariants

- Normal provider responses keep the existing normalized advice contract.
- Malformed provider responses cannot reach candidate execution or config
  mutation; they produce the existing mock/failure advice.
- Provider cancellation is not converted into an advice payload.
- Reference-case provenance is attached after either successful normalization
  or fallback, as before.

## Out of scope

No model prompt, provider protocol, retry policy, scientific interpretation,
AI intent authority, candidate execution, persistence, or technique-specific
behavior changes.
