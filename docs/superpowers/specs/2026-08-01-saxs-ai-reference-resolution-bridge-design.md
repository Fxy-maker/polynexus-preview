---
title: SAXS AI reference resolution bridge
date: 2026-08-01
status: approved
---

# SAXS AI Reference Resolution Bridge

## Goal

Convert advisory `saxs_candidate_references` returned by the AI into a
detached diagnostic record tied to the current full SAXS result, so later
review code can distinguish an existing deterministic candidate from an
unknown or untrusted ID.

## Scope

The bridge accepts the current result, the normalized advisory mapping, and
the current mode. For `temperature` it reads the current result's existing
`sequence_rescue_candidates` and delegates identity checks to
`resolve_sequence_rescue_candidate`. It returns resolved candidate records,
unresolved IDs, and stable reason codes. The output is JSON-safe and detached.

The orchestrator attaches this record to the advisory result after the AI
call. It is diagnostic evidence only. It does not call an analysis engine,
validate physical or quality gates, mutate configuration, apply a candidate,
rerun a frame, interpolate data, or create a validation report.

## Fail-closed boundaries

- Only exact string IDs in `saxs_candidate_references` are considered.
- Only the current temperature result's candidate records are eligible.
- Static, strain, unsupported modes, missing results, malformed advice,
  duplicate candidate records, and incomplete candidate provenance resolve to
  no candidate and retain an explanatory reason code.
- An unresolved advisory ID is never converted into a candidate-shaped value.
- The source result and the advisory mapping are not mutated.

## Data contract

The core adapter returns:

```json
{
  "mode": "temperature",
  "status": "available",
  "resolved": [{"candidate_id": "...", "kind": "deterministic", "...": "..."}],
  "unresolved_ids": [],
  "reason_codes": []
}
```

`status` is `available` only when at least one reference resolves; otherwise
it is `unavailable`. The `resolved` records are detached `RescueCandidate`
serializations. Reason codes include `unsupported_mode`,
`candidate_references_missing`, `candidate_not_found`,
`candidate_identity_rejected`, and `result_candidates_missing` as applicable.

## Integration boundary

`orchestrator_run_round.py` copies the Advisor mapping before adding
`saxs_candidate_reference_resolution`. This keeps the existing AI response
normalization contract unchanged and makes the result available in round
history/export paths that already retain the advice mapping. No GUI handler
branches on the new record.

## Verification

TDD must cover one valid detached resolution, unknown and malformed IDs,
temperature-only mode handling, source/config immutability, and orchestrator
attachment without engine execution. Run the focused bridge tests, the full
SAXS matrix, and the AGENTS.md structured verifier before the explicit
allowlist checkpoint.
