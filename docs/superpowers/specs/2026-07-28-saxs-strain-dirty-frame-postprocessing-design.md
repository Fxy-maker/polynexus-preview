# SAXS Strain Dirty-Frame Post-Processing Design

Date: 2026-07-28
Status: approved working design

## Problem

`analyze_single()` already creates a deterministic sanitized q/I analysis copy
and retains the original input defects in `data_quality_report`. The strain
series path still sends the original arrays to its reference invariant,
per-frame invariant, strain-phase detector, and void detector. A recoverable
dirty frame can therefore have valid single-frame evidence while strain-series
post-processing sees NaN, non-positive, or unsorted observations.

## Decision

Reuse `sanitize_1d_profile()` at the strain-series boundary. Build one detached
sanitized profile for each aligned frame and use it only for the existing 1D
post-processing consumers:

- the reference `Q_ref` invariant;
- each frame's `Q_star` invariant;
- `detect_strain_phase()`;
- `detect_voids()`.

Keep the original q/I arrays as the arguments to `analyze_single()` so the
existing frame-level quality report continues to describe the caller's raw
input. Keep the existing sector-data path independent; Herman/orientation
analysis consumes 2D sector payloads and is outside this 1D boundary.

## Safety and scientific boundary

- No interpolation, neighboring-frame copying, duplicate-q aggregation,
  fabricated frame, new point-count rule, or new physical threshold.
- Existing phase-classification thresholds and void/physical calculations are
  unchanged; only their input profile is the existing deterministic surviving
  observation set.
- An empty sanitized profile remains empty. Existing helpers return unavailable
  numeric evidence where possible; no Q* or void metric is fabricated.
- Strain ordering, source-index alignment, sector/Herman evidence, and the
  legacy `SAXSResult` contract remain unchanged.

## Data flow

```text
original frame q/I
  -> analyze_single(original q/I)
       -> frame analysis + raw defect provenance
  -> sanitize_1d_profile(original q/I)
       -> Q_ref/Q_star + phase/void post-processing only
  -> existing StrainSeriesResult aggregation
```

## Acceptance evidence

Focused tests must prove that dirty surviving observations reach all four 1D
post-processing consumers, original arrays still reach `analyze_single()`,
quality actions remain attached, empty profiles remain fail-closed, and clean
strain/source alignment is unchanged. The exact SAXS matrix, task verifier,
strict diff check, and explicit allowlist checkpoint are required before
handoff. Real-data scientific interpretation remains a separate review gate.

Verification evidence (2026-07-29): focused strain/method matrix `9 passed`;
exact SAXS matrix `428 passed, 6 warnings`; task-scoped verifier passed; fresh
full/boundary verification passed `2869 passed, 17 skipped, 12 warnings` in
`1686.81s`, including a passing boundary audit.
