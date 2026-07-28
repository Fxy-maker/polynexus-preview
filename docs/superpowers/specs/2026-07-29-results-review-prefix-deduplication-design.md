# Results Review prefix deduplication design

Date: 2026-07-29
Status: approved working design

## Problem

The shared Results Review boundary wraps risk and next-step content with the
localized `Risk note |` / `Next step |` labels. Some window fallbacks already
contain those labels, so the native Results surface can show duplicated text
such as `Risk note | Risk note | WAXS ...`.

## Decision

Normalize only the leading localized panel prefix at the shared boundary. The
normalizer accepts the active language plus the other supported language so a
persisted label from a prior language session is also safe. It repeatedly
removes the prefix at the beginning of the value, preserves the remaining
evidence verbatim, and lets the existing panel formatter add exactly one label.

Technique-specific producers, risk content, next-step meaning, and Joint
semantics remain unchanged.

## Error and fallback semantics

Empty or unprefixed values retain the existing no-risk/no-next fallback. A
prefix appearing later in the evidence is not removed; only leading panel
decoration is normalized.

## Verification boundary

Tests cover repeated and single English/Chinese prefixes, unprefixed content,
and the window-state fallback path. The task verifier and diff check remain the
handoff gates.
