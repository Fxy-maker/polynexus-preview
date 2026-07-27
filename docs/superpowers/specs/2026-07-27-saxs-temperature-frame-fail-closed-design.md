# SAXS Temperature Frame Fail-Closed Design

**Date:** 2026-07-27
**Status:** Implementation basis for the active SAXS quality goal

## Goal

Keep a malformed or unusable frame from aborting the rest of a temperature SAXS
sequence, while preserving the frame's original position and making the loss of
derived evidence explicit.

## Context

`analyze_temperature_series()` already isolates exceptions from
`analyze_single()`, so a frame can lose its Guinier evidence without stopping
later frames. Two adjacent sequence-level calculations are not isolated:
the initial `Q_solid`/`L_solid` reference calculations and each frame's
`scattering_invariant()` call. A malformed q/I pair can therefore escape the
existing frame boundary and terminate the complete series.

## Selected approach

Add small fail-closed guards at the existing temperature-analysis boundaries:

1. Compute the initial invariant and long-period references through guarded
   calls. If a reference is unavailable, retain `NaN` and record a stable
   diagnostic warning on the first source frame; do not choose another frame
   or synthesize a baseline.
2. Compute each frame's invariant independently. An exception or non-finite
   result leaves that frame's `Q_star`/`Xc` unavailable and records a stable
   warning; subsequent frames continue through the normal pipeline.
3. Preserve the existing temperature sort, `source_index`, frame count,
   missingness, Guinier sequence evidence, metric evidence, and physical
   thresholds. No frame is dropped, repaired, interpolated, copied from a
   neighbor, or automatically rescued.

The guard logs the original exception for diagnostics but exposes stable warning
codes through `TemperaturePointResult.warnings`, avoiding an exception string as
a contract. Existing `detect_temperature_phase()` behavior is not redefined in
this task; reference-dependent outputs remain unavailable when their reference
is non-finite, and the warning makes that limitation visible.

## Alternatives rejected

- **Pre-filter invalid frames:** loses the original frame position and hides
  which measurement failed.
- **Use the nearest valid frame as a baseline:** changes the physical reference
  semantics and behaves like implicit repair.
- **Wrap the entire series in one catch:** preserves availability poorly and
  gives no per-frame explanation.

## Boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: isolate reference and
  per-frame invariant calculations.
- `tests/test_saxs_temperature_guinier_evidence.py`: regression tests for
  middle-frame and first-frame failures.
- The existing quality contracts, GUI, Workbench, History, Export, and rescue
  contracts remain unchanged; they consume the preserved per-frame state.

## Scientific and data-safety invariants

- No new physical threshold or quality level is introduced.
- A failed calculation is not represented as zero, a neighboring value, or a
  fabricated Guinier result.
- The source temperature axis and original frame mapping remain intact.
- A sequence can retain valid evidence from unaffected frames while the failed
  frame remains Diagnostic/Unusable according to existing builders.
