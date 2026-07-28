# SAXS Guinier dirty-input guard design

**Date:** 2026-07-28
**Status:** approved working design for the SAXS quality goal

## Problem

The main `analyze_single()` path already creates a detached sanitized q/I
profile, but the public low-level `guinier_analysis()` helper is also exposed
through `polynexus.core.saxs_engine`. Direct callers can still supply strings,
non-finite values, non-positive observations, or an unsorted axis. The helper
then attempts NumPy operations on raw values or fits an order that is not the
physical q order.

## Goal

Make the public Guinier helper consume the same deterministic finite-positive
q/I survivors as the main SAXS path, while preserving its return shape,
Guinier fit, `q_min` behavior, and existing `qRg < 1.3` evidence boundary.

## Design

At the first line of `saxs_physical_helpers.guinier_analysis()`, call the
existing `sanitize_1d_profile(q, I)` and use only its detached q and intensity
arrays for the existing low-q selection and polynomial fit. The sanitizer
already defines aligned-prefix handling, per-item numeric coercion,
finite/positive filtering, stable q sorting, duplicate retention, and caller
immutability. No new cleanup policy is introduced.

The function keeps its current fail-closed result for fewer than ten usable
points: `(nan, nan, empty_q, empty_lnI)`. `q_min` is still applied after
sanitization, and all fit calculations remain unchanged. The public
`saxs_engine.guinier_analysis` export already resolves to this helper, so no
new interface is needed.

## Non-goals

- No new q window, fit-quality, `qRg`, or publication threshold.
- No interpolation, extrapolation, duplicate aggregation, frame fabrication,
  neighbor copying, rescue, or AI action.
- No changes to `GuinierEvidence`, sequence classification, or GUI consumers.
- No changes to raw data, real datasets, generated outputs, or parallel
  workspace files.

## Acceptance criteria

- Dirty numeric/string q/I input does not raise and the fitted q window is
  finite, positive, and monotonically ordered.
- Clean input produces the same Guinier result as before.
- Empty or wholly invalid input returns the existing NaN/empty shape.
- Caller-owned q/I values are unchanged.
- Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check, and
  an explicit allowlist checkpoint are recorded.
