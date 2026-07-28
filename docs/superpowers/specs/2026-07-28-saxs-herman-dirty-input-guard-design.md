# SAXS Herman dirty-input guard design

**Date:** 2026-07-28
**Status:** approved working design for the SAXS quality goal

## Problem

The public `herman_orientation_factor()` function performs arithmetic directly
on caller-provided sector arrays. An object/string intensity can raise a
`TypeError`, and an angle/intensity length mismatch can index with an
incompatible mask. That bypasses the existing fail-closed orientation evidence
path used by higher-level 2D analysis.

## Design

Add one private preparation helper beside the Herman calculation. It uses the
existing elementwise numeric coercion policy from the SAXS quality contracts,
aligns each supplied angle/intensity pair to the shorter length, removes only
non-finite pairs, and stably sorts by angle. If no angle is supplied, it keeps
the current generated angular grid. It returns detached arrays; finite negative
intensities remain because this function has no established positivity gate.

The existing meridional/equatorial windows, trapezoidal weighting, minimum
point checks, return keys, and NaN defaults remain unchanged. A profile with too
few surviving points naturally follows the current `method="none"` path.

## Safety and scientific limits

This is input hygiene, not orientation validation. It does not infer an axis,
detector geometry, mask, saturation, material orientation, or applicability.
It does not change `orientation_evidence`, rescue/AI behavior, or publication
eligibility. Any surviving finite negative values are passed to the existing
formula and may still yield a diagnostic/non-finite result.

## Verification contract

Focused tests must prove dirty input no longer raises, clean survivors retain
the clean result, mismatch and empty input fail closed, finite negative values
are not dropped by a new rule, and caller arrays are unchanged. The exact SAXS
matrix, task verifier, diff check, and explicit allowlist checkpoint are
required before closure.
