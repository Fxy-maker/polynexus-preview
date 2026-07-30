# SAXS Temperature Method Evidence Diagnostic Figure Design

## Goal

Expose existing temperature 1D method evidence for Porod, Kratky, invariant,
and lamellar metrics as one auditable diagnostic Figure definition.

## Scope

Extend the portable temperature Figure provider with
`saxs.series.temperature.method_evidence`. The figure consumes the existing
per-frame `MetricEvidence` mappings on `TempSeriesResult.temp_points` and the
existing condition/source/summary metadata. It emits one nullable audit source
for every supported method and a separate finite-value source for each plotted
line.

## Safety and scientific boundaries

- No metric is recalculated, normalized, filtered by a new threshold, or
  reclassified.
- Missing, non-finite, or malformed values remain `None` in audit sources and
  are omitted only from the corresponding renderer line.
- Frame order, existing temperature values, source indices, levels, and reason
  codes are preserved. No interpolation, frame fabrication, source repair, or
  sorting is introduced.
- The figure is always `publication_role="diagnostic"`; it cannot promote a
  Main/SI figure or affect physical, quality, rescue, AI, or publication gates.
- Existing Figure evidence attachment remains the provenance authority.

## Acceptance criteria

1. A temperature result with existing per-frame method evidence emits the new
   diagnostic Figure with all four supported methods represented.
2. Each method audit source preserves frame positions, nullable values, source
   indices, levels, and reason codes; finite plot sources contain only existing
   numeric pairs.
3. The recipe records the no-interpolation and no-reclassification boundary,
   and all source values are strict JSON-safe and detached from the result.
4. A result without method evidence keeps the existing figure set and does not
   emit an empty diagnostic figure.
5. Existing temperature provider tests, structured verification, the exact
   SAXS matrix, storage dry-run, diff check, and an explicit allowlist
   checkpoint are recorded.
