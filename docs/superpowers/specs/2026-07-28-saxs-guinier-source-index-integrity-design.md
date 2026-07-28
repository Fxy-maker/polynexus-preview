# SAXS Guinier sequence source-index integrity design

## Decision

Extend the existing `GuinierSequenceEvidence` builder with deterministic
provenance checks for the optional `source_indices` mapping. A source index
that is duplicated across frame positions, negative, or non-integral is an
invalid frame-to-source mapping and must keep the sequence at `Diagnostic`
when otherwise valid Rg frames exist. The existing length-mismatch reason is
preserved.

Temperature sorting can legitimately reorder source indices (for example,
sorted temperatures may produce `[1, 0]`). Reordering alone is not invalid and
does not downgrade a valid sequence; it is recorded as diagnostic provenance
metadata in the existing relative-change statistics and physical checks.

## Invariants

- Frame positions, Rg values, temperature values, and source indices are never
  sorted, interpolated, deleted, or rewritten by the builder.
- Missing frame payloads remain represented by `missing_frame_indices` and are
  not replaced by a source-index guess.
- No expected source-index range is inferred, so a gap cannot be called a
  missing source frame without authoritative upstream metadata.
- Sequence evidence remains at most `Trend`, never `Quantitative`.
- Existing temperature-axis checks, continuity diagnostics, quality gates, and
  valid `[1, 0]` sorting behavior remain unchanged.
- All new fields and reason codes use the existing strict JSON-safe contract.

## Acceptance criteria

1. Duplicate source indices report their original frame positions, add
   `guinier_sequence_source_index_duplicate`, and make the sequence
   `Diagnostic` when valid frames exist.
2. Negative or non-integral source indices report their original frame
   positions, add `guinier_sequence_source_index_invalid`, and make the
   sequence `Diagnostic` when valid frames exist.
3. A valid reordered mapping such as `[1, 0]` remains `Trend` and records
   `source_index_order_reordered=True` without an invalid-mapping reason.
4. Existing source-index length mismatch remains diagnostic and existing JSON
   round-trip behavior remains valid.

## Verification boundary

Verification uses focused sequence tests, the temperature Guinier propagation
matrix, the structured task verifier, `git diff --check`, and a dry-run test
storage report. The exact SAXS matrix is counted only if a fresh pytest summary
is emitted; a timeout or no-summary run is recorded as a limitation.
