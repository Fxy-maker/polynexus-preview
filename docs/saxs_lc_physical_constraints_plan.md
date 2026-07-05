# SAXS `lc` Physical Constraints Strengthening Plan

## Background

Current SAXS temperature-series outputs can still produce a numeric `lc` even when the frame has already become structurally unstable for lamellar-thickness extraction. This is most visible in PA6 high-temperature frames such as around 185 C:

- the result may show a very small `lc` or `Xc`
- the user may reasonably interpret that as "sample is melting"
- but the actual issue may be "the extraction chain is no longer physically constrained enough"

This document defines the boundary for strengthening SAXS `lc` physical constraints, especially for temperature-series workflows.

## Goals

- Make SAXS `lc` outputs physically honest rather than numerically eager.
- Prevent unstable high-temperature frames from being presented as normal, usable lamellar thickness results.
- Keep `raw`, `calibrated`, and `diagnostic-only` outputs clearly separated.
- Let temperature-series melting evidence and `lc` reliability evidence work together without being conflated.
- Keep the final decision with the user, while allowing AI to explain and review the evidence.

## Advancement Principles

- Add hard gates before refining soft confidence scoring.
- Prefer suppressing false confidence over forcing a result for every frame.
- Keep physics-grounded rules deterministic in `core`.
- Preserve traceability: every downgrade must leave an explicit status and reason.
- Keep temperature-series scope first; avoid broad cross-mode refactors in the first pass.
- Allow AI to explain and recommend, but not to override physical hard constraints.

## Priority

1. Stop unstable high-temperature frames from being shown as normal `lc`.
2. Connect melting-window evidence to temperature-series `lc` reliability judgment.
3. Surface explicit status and reason fields in outputs and GUI.
4. Improve structured downgrade reasons for later AI review and user inspection.
5. Refine confidence scoring after the hard-boundary behavior is stable.

## Phase Scope

### Phase 1: Stabilize `lc` Output

Scope:

- Add hard downgrade logic around existing `lc` extraction results.
- Distinguish usable vs low-confidence vs diagnostic-only outputs.
- Preserve raw values for traceability, but do not present them as equally trustworthy.

Expected output fields:

- `lc_reliability_status`
- `lc_reliability_reason`
- `lc_reliability_score` if needed
- existing `lc_confidence`
- existing raw snapshots and raw structural fields

Suggested status values:

- `usable`
- `low_confidence`
- `diagnostic_only`

Example downgrade triggers:

- only one method remains and the thickness is implausibly thin
- tangent / IDF / gamma-min estimates conflict strongly
- minority phase fraction is too small to support reliable interpretation
- `Q_invariant` is clearly abnormal
- frame-level continuity breaks sharply inside a temperature sequence

### Phase 2: Physical Coupling with Melting-Window Evidence

Scope:

- connect `Tm_onset`, `Tm_peak`, and `Tm_end` from temperature-series SAXS analysis to frame-level `lc` usability judgment
- distinguish "close to melting" from "cannot reliably extract `lc`"
- avoid treating all high-temperature weak frames as melted

Core boundary:

- "melting-window status" and "`lc` reliability status" are separate judgments
- a frame may be outside the melting window but still be unreliable for `lc`
- a frame may be near the melting window without being fully melted

Suggested melting-window status values:

- `outside_window`
- `near_onset`
- `within_window`
- `post_end`
- `undetermined`

### Phase 3: Output and GUI Governance

Scope:

- expose status and reasons in batch tables, result cards, and exported summaries
- make `raw`, `calibrated`, and `diagnostic-only` behavior visible
- prevent users from seeing only a numeric `lc` without context

### Phase 4: AI-Linked Review

Scope:

- let AI consume deterministic evidence fields and convert them into human-readable review text
- keep AI in a recommendation and explanation role
- retain user confirmation as the final acceptance boundary

AI should be able to explain:

- whether the frame is near a melting window
- whether the `lc` result is reliable enough to interpret physically
- why a frame was downgraded
- what the next review step should be

AI must not:

- directly override hard physical downgrades
- silently convert diagnostic-only values into accepted physical results
- inject hidden reference crystallinity defaults

## How to Determine "Near Melting Window"

This must not be determined by polymer handbook temperature alone.

Use a three-layer evidence model:

### Layer 1: Sequence-Intrinsic SAXS Evidence

Primary basis:

- `Tm_onset`: first sustained Bragg-peak intensity decrease below the onset threshold
- `Tm_peak`: approximate midpoint of peak-intensity loss
- `Tm_end`: near disappearance of the tracked peak

Interpretation:

- before `Tm_onset`: usually `outside_window`
- around `Tm_onset`: `near_onset`
- between `Tm_onset` and `Tm_end`: `within_window`
- after `Tm_end`: `post_end`

This is the preferred basis because it comes from the current dataset rather than a generic material expectation.

### Layer 2: Material Prior as Soft Prior Only

`T_melt_expected` may be provided as a soft prior or warning hint, but it is optional.

It may support statements like:

- "temperature is approaching the expected melting region"

It must not alone trigger:

- forced melting classification
- automatic invalidation of `lc`

### Layer 3: Structural-Extraction Stability

Even when a frame is not in the melting window, `lc` can still be unreliable if the extraction constraints collapse.

Typical signs:

- low `lc_confidence`
- severe disagreement between tangent / IDF / gamma-min constraints
- implausible minority fraction
- `Q_invariant` anomaly
- sudden continuity break in `L`, `q*`, or peak tracking

When this happens, the correct conclusion is:

- not necessarily "melting"
- but "insufficiently reliable for `lc` interpretation"

## AI Collaboration Boundary

AI linkage is recommended, but with explicit authority boundaries.

### `core` Responsibilities

`core` should produce deterministic evidence and status:

- `melting_window_status`
- `lc_reliability_status`
- `lc_reliability_reason`
- `Tm_onset_C`, `Tm_peak_C`, `Tm_end_C`
- structured frame evidence and sequence evidence

### AI Responsibilities

AI should:

- translate status and evidence into user-facing reasoning
- explain why a frame is downgraded
- distinguish melting evidence from extraction instability
- recommend next checks such as 2D SAXS image review, WAXS, or DSC reference

AI should not:

- act as the source of physical truth
- bypass deterministic status fields
- hide uncertainty

### User Final Authority

Final acceptance remains with the user.

The system should preserve this boundary through:

- explicit confirm/apply behavior for AI tuning
- result confirmation state in history and current-run review
- visible separation between suggested interpretation and accepted result

## Out of Scope

- full rewrite of `gamma(r)` / IDF / tangent extraction algorithms
- simultaneous refactor of temperature, strain, and static pipelines
- polymer-specific hard-coded thresholds in the first implementation
- hidden default crystallinity or silent calibration fallbacks
- letting AI directly edit physical outputs without deterministic evidence support

## Acceptance Criteria

- PA6 high-temperature frames such as around 185 C are no longer presented as normal usable `lc` by default when evidence is weak.
- The system can explicitly say either:
  - "near melting window"
  - or "not enough evidence for reliable `lc` extraction"
  - without conflating the two.
- `raw`, `calibrated`, and `diagnostic-only` outputs are clearly distinguishable.
- Missing reference crystallinity does not trigger hidden calibration.
- Downgrade reasons are present in exported tables and review surfaces.
- Existing stable low-temperature frames are not unnecessarily downgraded.

## Risks

- Hard gates may become too strict and suppress borderline-but-usable frames.
- Using sequence-derived windows may fail when peak tracking itself is poor.
- A generic implementation may not fit all polymers equally well.
- New status fields may require downstream export or GUI compatibility updates.
- If the UI still emphasizes the numeric value over the status label, user misunderstanding may persist.

## Recommended First Implementation Boundary

- temperature-series SAXS only
- deterministic status fields first
- no material-specific hard-coding in v1
- no AI override of physical status
- tests added before broad UI polish

## Recommended First Deliverables

1. Add `melting_window_status` and `lc_reliability_status` to temperature-series SAXS results.
2. Add explicit downgrade reasons for unstable `lc` frames.
3. Surface these fields in batch output and GUI review text.
4. Feed these fields into the existing AI review / evidence pipeline.
5. Keep user confirmation as the final acceptance step.
