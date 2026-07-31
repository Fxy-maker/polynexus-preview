# SAXS Herman Confidence Gate Design

## Goal

Prevent residual detector artifacts, invalid intensity pairs, and weak
azimuthal harmonics from appearing as quantitative per-frame Herman factors in
the in-situ strain result table, while retaining the raw diagnostic value and
its evidence for review.

## Problem

The SAXS anisotropy core currently calculates a finite Herman factor whenever
the second harmonic passes a simple strength threshold. The shared quality
contracts can mark the frame as diagnostic or blocked, but the strain adapter
still transports the raw value into `f_Herman`. This makes a blocked 0% frame
look like confirmed initial orientation.

## Scientific contract

- `f_herman_raw` is the deterministic value produced from the selected
  azimuthal profile and remains available only as diagnostic evidence.
- `f_herman` is the effective/display value. It is finite only when the
  azimuthal profile passes coverage, effective-bin, harmonic-significance, and
  split-axis-stability checks, and when supplied 1D input quality does not have
  a hard orientation blocker.
- A blocked value is represented as unavailable (`None` in table/export
  payloads, `NaN` in numerical DTOs) and is displayed as `—`; it is never
  replaced with zero.
- A finite 0% value remains possible when the sample has real pre-existing
  orientation and the evidence passes. No strain monotonicity assumption is
  introduced.
- The existing two-dimensional Herman convention and `f=0.25` uniform-ring
  reference are unchanged.

## Reliability checks

At the detector-plane azimuthal profile, report:

- finite/nonnegative bin count and effective weighted-bin count;
- circular angular coverage after accounting for the wrap-around gap;
- second-harmonic strength and a deterministic significance estimate
  `strength * sqrt(effective_bins)` (default acceptance threshold `2.0`);
- axis disagreement between even/odd profile bins, measured modulo 180 degrees.

Automatic axes require the configured minimum strength, minimum effective bins,
minimum coverage, minimum significance, and maximum split-axis drift. Existing
configured axes still use the configured direction, but the profile quality
gate controls whether the resulting Herman value is usable.

The strain adapter additionally blocks the effective value when the aligned 1D
quality report records unusable input, nonfinite/nonpositive intensity or q,
low-q truncation, or `invalid_pairs_dropped`. These are preserved as explicit
orientation reason codes.

## Data flow

```text
I(chi) + detector/1D quality
    -> raw axis and raw Herman calculation
    -> azimuth coverage/significance/stability evidence
    -> effective-value gate
    -> result DTO: f_herman_raw + optional f_herman
    -> table displays only effective f_herman
```

The GUI remains a consumer of the existing strain DTO/table contract. It does
not inspect SAXS algorithm state or implement quality rules.

## Failure behavior

- Insufficient or invalid input keeps both effective value and axis unavailable.
- A calculable but blocked profile keeps the raw value in orientation evidence,
  sets the effective value unavailable, and adds a machine-readable reason.
- JSON evidence remains strict-JSON safe and records the thresholds and derived
  diagnostics needed to reproduce the gate.

## Non-goals

- Do not force the 0% frame to zero.
- Do not tune thresholds to make Herman values monotonic with strain.
- Do not change the Herman mathematical convention, q* selection, detector
  calibration, or GUI event handlers.
- Do not modify real EDF data, parallel AI advisor work, memory files, or local
  test artifacts.

## Acceptance criteria

1. A strong synthetic anisotropic ring produces finite raw and effective values.
2. An isotropic or weak noisy ring produces a raw diagnostic result but no
   effective Herman value, with a reason explaining the failed gate.
3. A profile with poor angular coverage or unstable split axes is blocked.
4. A frame with hard 1D quality defects is blocked in the strain transport,
   while its raw Herman value remains in evidence.
5. The result table/dataframe emits an unavailable Herman cell for blocked
   frames and keeps finite values for accepted frames.
6. Existing explicit-axis, configured 2D baseline, missing-data, and JSON
   evidence tests remain valid.

## Review note

This is a conservative scientific usability gate, not a claim that a finite
value proves a three-dimensional tensile-axis orientation. Human review and
raw 2D inspection remain required for publication conclusions.
