# SAXS Correctness Slice A Design

**Date:** 2026-08-03
**Status:** approved working scope from the SAXS review follow-up

## Goal

Remove deterministic SAXS correctness and contract defects without choosing a
new scientific model for Porod-invariant crystallinity, sector-derived
structure parameters, or negative-background residual treatment.

## Scope

This slice covers:

- one canonical corrected/normalized/unsmoothed intensity boundary for 2D
  single-frame and directory analysis;
- the azimuthally averaged horizontal-polarization factor with a unit small-q
  limit;
- explicit cooling-solid phase semantics and acquisition-order preservation
  for cooling/isothermal sequences;
- SI conversion and optional fixed-intercept behavior for Gibbs-Thomson;
- functional correlation-function extrapolation flags;
- consistent single-file extension handling and explicit batch truncation
  provenance;
- field-level geometry provenance instead of a non-empty-header shortcut.

The following remain outside this slice and must be represented as diagnostic
or design follow-up rather than silently changed:

- the Porod-invariant crystallinity equation and coefficient;
- whether equatorial sectors may feed directional versus total structural
  metrics;
- treatment of negative residual intensities and uncertainty propagation;
- publication-role policy beyond existing approved static gating.

## Decisions

### Intensity boundary

`preprocess_pipeline()` remains responsible for background, polarization,
transmission/thickness normalization, and sector production. The engine stores
`Iq_norm` as the analysis input for 2D frames. Smoothing remains inside
`analyze_single()` and therefore occurs once per analysis path. Raw, normalized,
and smoothed arrays remain available for provenance and plotting.

### Polarization

For a horizontal fully polarized source, use the azimuthal average

```text
P_factor = (1 - P) + P * (1 + cos(2 theta)^2) / 2
```

This is equivalent to `1 - P * sin(2 theta)^2 / 2`, gives one at `q=0`, and
reduces to no correction for `P=0`.

### Temperature sequence order

Heating uses stable ascending-temperature order for temperature trends.
Cooling and isothermal analyses preserve supplied acquisition order; when a
time axis exists, that order is the kinetic order. The solid reference is
selected by the minimum finite temperature rather than assuming position zero.

Cooling receives a dedicated `COOLING_SOLID` enum value. Existing
`HEATING_SOLID` remains valid for heating/unknown fallbacks.

### Gibbs-Thomson

Lamellar thickness is converted from nm to m before combining with the typical
`delta_Hf` value expressed in `J/m^3`. With no `Tm_inf`, the intercept is fitted
from the data. With `Tm_inf`, the documented Celsius input is converted to K and
held as the intercept while the slope is fitted; the returned `Tm_inf` records
the effective value used.

### Extrapolation flags

`extrapolate_q0=False` skips low-q prepending; `extrapolate_qinf=False` keeps
the measured high-q tail and skips Porod extension. The default behavior stays
the current high-q extension and measured low-q boundary unless a caller
explicitly requests a different mode.

### I/O and truncation

The single-file engine accepts the same 1D and 2D extension sets declared by
the I/O module. Directory scanning continues to use 2D inputs only, but emits
explicit sequence provenance when configured limits exclude files. The limits
remain unchanged in this slice to avoid an unbounded memory/performance change.

### Geometry provenance

Batch geometry source/confidence is derived from the existing field-level
provenance payload. A non-empty header is not sufficient for `header/0.95`.

## Data flow

```text
2D image
  -> preprocess_pipeline
  -> Iq_norm (analysis input), Iq_smooth (display/legacy evidence)
  -> analyze_single (one smoothing pass)
  -> result/evidence/export
```

## Testing

Each behavior change gets a focused RED/GREEN regression before production
code. The minimum matrix covers:

- polarization `q=0, P=1` and `P=0` identity;
- single/batch payload selection and one smoothing boundary;
- cooling-solid/melt labels and preserved time order;
- Gibbs nm-to-m conversion and fixed `Tm_inf` response;
- correlation flag output differences;
- `.xy` and declared 2D extension acceptance at the engine boundary;
- explicit truncation metadata and incomplete geometry confidence.

## Non-goals

No new invariant equation, sector physics interpretation, negative-intensity
repair, GUI redesign, publication authorization policy, or external data
deletion is included.
