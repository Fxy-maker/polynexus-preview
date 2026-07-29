# SAXS export dirty-profile guard design

## Decision

Make the SAXS bundle profile export consume the canonical `ProcessedProfile`
projection when one is available. If a legacy profile item has no canonical
projection, the export boundary converts q/layer values element by element and
writes failed conversions as empty CSV cells. Existing profile diagnostics are
written to `provenance.json` unchanged.

## Invariants

- Export never mutates caller-owned arrays or profile diagnostics.
- q/I positions and lengths are preserved; invalid values become empty cells,
  not deleted, sorted, interpolated, or fabricated.
- A dirty projection remains visibly dirty through `quality_status` and
  `diagnostics`; export success is not scientific validation.
- Existing CSV columns, bundle paths, analysis results, quality gates, and
  publication roles remain unchanged for clean input.

## Out of scope

No analysis sanitization, physical threshold, evidence-level promotion,
rescue/AI action, Figure/Manifest semantics, or real-data modification is
introduced.
