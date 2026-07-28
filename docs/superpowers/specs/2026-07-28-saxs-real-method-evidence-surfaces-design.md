# Real SAXS method-evidence surfaces design

**Date:** 2026-07-28

## Decision

Use the already-emitted `metric_evidence` mapping as the authoritative
method-level record. The parameter summary and Export `quality_evidence.json`
must match exactly. Figure provenance remains intentionally compact: every
field it includes must equal the corresponding authoritative value, while
series-only aggregate fields may remain in the parameter/Export surfaces.

## Evidence boundary

The regression covers existing Porod, Kratky, invariant, lamellar, and any
existing Guinier method record. It compares mappings only; it does not
recalculate a metric, judge applicability, add a threshold, or infer a
publication role. Missing fixtures skip explicitly and no synthetic fixture is
created.

## Implementation boundary

For Temperature, Figure frame records bind to the already-emitted series point
through its `source_index`, because the series may be condition-sorted. For
Strain, Figure frame records bind to the existing series-point order. The
provider only selects the emitted `metric_evidence` mapping; it does not
recalculate, merge, interpolate, or alter any evidence field.

## Failure policy

Any mismatch is a contract failure. A rendered Figure is not evidence of
scientific validity, and a compact projection is not permitted to alter the
level, reason codes, source reference, condition axis, or any other field it
retains. Temperature's existing validation failure remains an expected
diagnostic boundary.
