# SAXS export fallback dirty-provenance design

## Decision

When SAXS bundle export uses the legacy analysis fallback without a canonical
`ProcessedProfile`, count elementwise q and exported layer conversion failures
and include them in that profile's existing provenance record. A fallback item
with conversion failures reports profile `quality_status="WARN"` when no
stronger status was already supplied.

## Invariants

- Existing analysis quality flags and scientific evidence are preserved; this
  profile status is export provenance, not a new analysis level.
- Invalid positions remain in the CSV as empty cells.
- Input arrays and existing diagnostics are not mutated.
- Clean fallback exports are byte/field compatible with current behavior.
- No interpolation, repair, sorting, threshold, rescue, AI, or publication
  behavior is introduced.

## Out of scope

This task does not change analysis paths, `DataQualityReport`, physical gates,
Figure/Manifest semantics, or the canonical processed-profile implementation.
