# SAXS Guinier Source-Mapping Trust Boundary Design

## Goal

Make temperature Guinier sequence evidence distinguish diagnostic source-index
facts from a mapping that downstream consumers may trust.

## Design

At the existing `build_guinier_sequence_evidence()` boundary, inspect the raw
`source_indices` values before integer normalization. A mapping is trusted
only when it is supplied, has exactly one entry per observed frame, contains
non-negative finite integers (booleans excluded), and has no duplicates. A
valid mapping may be out of order and is recorded as reordered provenance.

When the supplied mapping is malformed, duplicated, or length-mismatched, the
result keeps the invalid/duplicate position lists and diagnostic reason codes,
but emits an empty `frame_source_indices` and empty `pair_source_indices`.
This prevents invalid identities from being consumed as source-pair evidence.
When no mapping is supplied, the existing empty mapping behavior remains
unchanged. No Rg values, temperature values, frame positions, quality levels,
thresholds, interpolation, rescue, or AI behavior changes beyond the existing
Diagnostic downgrade for an invalid mapping.

## Safety boundary

The builder remains observational. It does not sort, fill, delete, infer, or
repair frames. Existing `source_index_order_reordered` remains a provenance
fact and does not lower a complete valid sequence from `Trend`.

## Acceptance

- Complete valid mappings preserve frame and pair source identities.
- Complete reordered mappings preserve identities and set the reordered flag.
- Duplicate, invalid, and length-mismatched mappings expose diagnostic position
  facts but expose no trusted frame/pair mapping.
- Omitted mappings remain unchanged.
- All payloads remain strict JSON-safe and round-trip through the existing DTO.
