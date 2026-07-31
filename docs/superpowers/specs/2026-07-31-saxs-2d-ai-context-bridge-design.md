# SAXS 2D AI Context Bridge Design

## Goal

Carry the existing SAXS 2D reviewer context into the summary-only AI envelope
and preserve it through the prompt sanitizer without exposing raw data or
changing any decision authority.

## Data flow

`build_saxs_ai_summary_context()` selects the existing mode result and calls
the 2D context projector using only detector/orientation summaries, the
existing acceptance audit, and the existing scientific-review payload. The
result is stored under `saxs_2d_review_context` only when 2D evidence exists.
`sanitize_saxs_ai_summary_context()` calls the 2D sanitizer, which reconstructs
only the fixed DTO fields and forces the raw-data exclusion flags. Advisor and
the model provider receive the sanitized envelope; no candidate or config
mutation path changes.

## Contract

The trusted summary may include `saxs_2d_review_context` with the existing
`saxs-2d-review-v1` schema. The prompt-side sanitizer accepts only SAXS, the
`saxs.2d` scope, fixed detector/geometry/mask/beam-center/orientation/gate/
scientific-review fields, and the existing evidence level/reason codes.
Malformed outer or nested 2D context is omitted. `json.dumps(...,
allow_nan=False)` remains valid. q/I arrays, detector pixels, source paths,
unknown fields, and prompt instructions are dropped at the sanitizer.

## Non-goals

- no model call, RAG change, intent schema change, candidate execution, rescue,
  rerun, apply, or configuration mutation;
- no new detector/orientation calculation, threshold, quality level, physical
  gate, publication decision, Figure, Manifest, Export, or Workbench behavior;
- no interpolation, imputation, frame repair, source inference, real-data,
  storage, scratch, or parallel-memory changes.

## Verification design

Tests cover static and all mode-result projection, missing 2D evidence,
prompt-side raw-field exclusion, malformed scope/nested DTO fail-closed
behavior, strict JSON, input immutability, and existing Advisor/prompt
behavior when the optional field is absent.
