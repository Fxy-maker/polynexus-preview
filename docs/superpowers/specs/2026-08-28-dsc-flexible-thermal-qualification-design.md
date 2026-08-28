# Flexible DSC thermal qualification

## Decision

The generic `thermal_program.v1` conversion path must not assume a material
specific melt temperature or require a preceding melt hold. Every finite,
monotonic thermal segment that meets the minimum sampling duration is retained
for deterministic analysis. Temperature offset, span, and noise are soft
quality observations recorded on the segment and result; they are not parse or
execution blockers.

Hard blockers remain malformed/non-finite arrays, non-increasing time, missing
sample mass, or insufficient points/duration for the requested calculation.

## Data flow

Mettler text -> canonical thermal segments -> DSC executor -> Avrami/thermal
results. The converter records `quality_warnings` beside each segment's source
range. The executor copies those warnings into scan metadata and Avrami quality
flags while still returning deterministic values when the numerical fit is
possible.

## Compatibility and boundary

The old converter IDs remain accepted. No provider algorithm or raw input is
changed. Existing callers that inspect status continue to receive `ready` when
at least one calculable segment exists. Scientific publication eligibility may
still downgrade results with warnings; this change only prevents premature
loss of computable data.
