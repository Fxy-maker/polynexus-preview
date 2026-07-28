# SAXS strain sector fail-closed design

## Context

The strain consumer accepts optional sector data. A mapping whose nested
`meridional` or `equatorial` value is not a mapping currently reaches
`.get()` and raises, aborting the whole series. The canonical 2D anisotropy
path already reports invalid input through `DetectorQualityReport` and
`MetricEvidence`; the strain fallback should use the same contract.

## Design

Validate the outer and nested sector mappings before fallback integration. For
invalid payloads, return NaN legacy Herman scalars plus a detached detector
quality report for an empty sector map and an Unusable orientation evidence
record with `strain_sector_data_invalid` in its reason codes. The series
consumer attaches these records to the affected point and continues processing
all 1D data.

No numeric threshold, repair, interpolation, or interpretation is added. A
valid payload follows the existing canonical anisotropy or sector integration
path unchanged.

## Testing

The regression first exercises the helper directly, then runs one complete
strain point with malformed sector data and asserts frame retention, exact
reason provenance, and strict JSON serialization.

The focused matrix returned `54 passed`; the structured verifier returned
quality `287` and preprocessing `106`. The full SAXS matrix remains an
explicitly unclaimed bounded-time diagnostic from the preceding task.
