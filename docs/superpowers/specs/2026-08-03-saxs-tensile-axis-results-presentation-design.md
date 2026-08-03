# SAXS Tensile Axis and Results Presentation Design

**Date:** 2026-08-03
**Status:** Approved for implementation planning
**Depends on:** q-resolved reliability and feature tracking

## Goal

Let a user explicitly provide the detector-plane tensile axis for an in-situ
SAXS run and present final, diagnostic, delta, q-feature, stability, and
reliability evidence without implementing scientific logic in GUI code.

## Coordinate convention

The public convention is `detector_image_clockwise_deg_v1`:

- zero degrees points from the beam center toward increasing detector-column
  index, visually right in an untransformed detector image;
- positive angles rotate toward increasing detector-row index, visually
  clockwise/down;
- values are normalized to `[0, 180)` because an axis has 180-degree symmetry;
- any image transform used for display must map the selected screen vector
  back into this detector coordinate convention before configuration binding.

The GUI must display the convention with the detector preview and persist both
the numeric angle and convention identifier. It must not derive the tensile
axis from a scattering maximum.

## Input design

Add a strain-only configuration field and a focused detector-axis selector.
The selector supports direct angle entry and click-drag axis placement through
the beam center. Clearing the field writes `None`, not zero. The existing SAXS
config binder validates finite values, normalizes modulo 180, and records
binding provenance.

Run configuration owns the axis. Recent calibration storage may not silently
apply a tensile axis to another run because the axis describes sample mounting,
not detector calibration. General run presets may persist it only with an
explicit visible value.

## Presentation contract

The results table consumes flattened DTO fields prepared by core/services:

- final `f_Herman` relative to the explicit tensile axis;
- `f_Herman_raw` labeled as principal-axis diagnostic;
- same-feature `delta_f_from_zero`;
- 95-percent stability interval;
- tracked q range and track ID;
- reliability status and reason summary.

Final and diagnostic values remain separate columns. A missing final value
renders unavailable and never falls back to the diagnostic value.

The detailed results surface may show q-resolved strength, tracked q bands,
axis evolution, and sensitivity ranges through existing FigureDefinition or
detached view-model contracts. GUI event handlers do not inspect support bins,
apply thresholds, or choose features.

## Failure behavior

- Missing axis leaves final Herman blank and diagnostic evidence visible.
- Invalid angle blocks configuration binding with a visible validation state.
- A stale or mismatched coordinate convention is rejected, not converted by
  guesswork.
- A transformed preview must prove round-trip detector coordinates before
  accepting a drag gesture.
- Results cannot show a final trend unless evidence is applicable, tensile-
  referenced, and finite.
- Diagnostic, artifact-sensitive, and unavailable states remain visible.

## Boundaries and tests

Core changes are limited to config binding and flattened service transport.
GUI changes cover the strain config schema, focused axis selector, i18n,
results table, and evidence figures. Tests cover coordinate round-trip,
None/zero distinction, modulo normalization, persistence scope, no auto-axis
inference, table labels, no fallback, transformed previews, strict DTO
consumption, and restarted-GUI behavior.

## Acceptance criteria

1. The user can explicitly set or clear the tensile axis with a visible
   detector-coordinate convention.
2. Core receives the exact normalized axis and provenance.
3. Final and diagnostic orientation values cannot be confused or substituted.
4. Same-feature delta and q-range evidence are readable in Results.
5. GUI code contains no SAXS feature, threshold, or quality-gate decisions.

## Non-goals

- No automatic tensile-axis inference.
- No detector calibration correction.
- No AI authority over the axis.
- No publication promotion.
