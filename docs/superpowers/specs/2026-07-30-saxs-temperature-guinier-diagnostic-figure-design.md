# SAXS Temperature Guinier Diagnostic Figure Design

## Goal

Close the temperature 1D Guinier evidence path at the Figure boundary by
emitting one auditable diagnostic figure from the already-produced
`TempSeriesResult` evidence.

## Scope

`build_saxs_temperature_definitions()` will emit
`saxs.series.temperature.guinier` when a temperature result carries a frame
count and a `Rg_array`. Its data source will contain temperature, Rg, source
index, frame quality level, and frame reason codes. Non-finite Rg values are
serialized as `None`, preserving missing or unusable frames at their original
positions.

The figure is a single `plot_series` panel and is always assigned the
`diagnostic` publication role. It is a review surface, not a Main/SI
scientific conclusion.

## Safety and scientific boundaries

- The provider reads `Rg_array`, `guinier_level_array`, `temp_points`, and
  `guinier_sequence_evidence`; it never recalculates Guinier or changes a
  quality level.
- No interpolation, neighbor copying, frame deletion, phase decision, new
  threshold, rescue, AI call, or publication promotion is introduced.
- Source indices come from existing `TemperaturePointResult.source_index`.
  If they are unavailable, the diagnostic data uses `None` rather than
  inventing identity.
- The recipe records that missing values are preserved and interpolation is
  disabled. Existing Figure evidence provenance remains attached unchanged.

## Acceptance criteria

1. A temperature result with emitted Rg evidence produces the new diagnostic
   definition with finite and missing values represented safely.
2. The data source preserves frame order, source indices, levels, and reason
   codes without mutating the result.
3. The definition validates and remains V2-runtime ready.
4. A legacy result without Rg evidence keeps the existing figure set.
5. Existing temperature provider, SAXS matrix, structured verifier, storage
   dry-run, diff, and explicit allowlist checkpoint remain green.
