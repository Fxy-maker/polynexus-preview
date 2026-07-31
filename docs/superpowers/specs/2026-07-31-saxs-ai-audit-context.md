# SAXS AI scientific acceptance audit context

**Date:** 2026-07-31
**Status:** Approved working design

## Decision

Project the already-computed `scientific_acceptance_audit` into the existing
SAXS AI summary context. The projection is detached, strict-JSON, summary-only,
and candidate-only. It never rebuilds the audit, evaluates a gate, or changes
publication, Figure, Manifest, Export, rescue, or rerun behavior.

## Data flow

`SAXS engine result.parameters audit -> summary-only context -> prompt sanitizer -> Advisor`

The builder accepts either the direct SAXS result or the existing engine
wrapper. For temperature and strain, frame/series evidence still comes from
the active series result; the audit comes from the engine's existing result
parameters. Missing or malformed audit data is omitted rather than inferred.

## Boundary

Only the existing audit summary fields are allowed: status, automated
validation status, existing publication-gate values, evidence levels,
provenance validity, physical-gate evidence, method-gate status, reliability,
reason codes, audit scope, publication-decision-changed, and detector
provenance audit. Nested values are JSON-safe and raw q/I, detector pixels,
source paths, and unknown prompt fields are excluded.

## Acceptance

1. A result or engine wrapper with an existing audit carries that detached
   audit into the context.
2. Static, temperature, and strain frame/series evidence remains unchanged.
3. Missing/unsupported audit evidence is absent, not fabricated, and strict
   JSON remains valid.
4. Prompt-side sanitization keeps the same audit whitelist and excludes raw
   or unknown fields.
5. Existing validation, candidate, publication, Figure, Manifest, Export, and
   no-context behavior remain unchanged.
