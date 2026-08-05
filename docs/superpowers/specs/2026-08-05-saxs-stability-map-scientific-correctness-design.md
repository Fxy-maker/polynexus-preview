# SAXS Stability Map and Scientific Correctness Design

## Context

The existing AI path already sanitizes prompts, creates candidate-only
preprocessing reports, and applies accepted configurations through
`PreprocessTransactionService`. It is intentionally small (`max_candidates=6`)
and is not a stability study. A stability map must answer a different question:
whether a connected neighborhood of preprocessing choices produces consistent
physical evidence.

## Alternatives

### Cartesian grid

Easy to reproduce but grows exponentially across q bounds, background, beam
center, mask dilation, fitting windows, and chi width. It spends most trials in
uninteresting corners and cannot adapt to a narrow valid plateau.

### Pure Bayesian optimization

Efficient for finding one high-scoring point, but a single optimum is not
evidence of a connected robust plateau. A surrogate can also over-trust noisy
quality scores near physical gates.

### Hybrid stability study (selected)

Use a deterministic Sobol-like low-discrepancy design for global coverage,
constrained Bayesian-style acquisition for local refinement around promising
regions, and a deterministic local grid for the final plateau confirmation.
The implementation keeps the acquisition dependency-free: a seeded Latin
hypercube is the global design, expected-improvement-like distance/score
selection is the active refinement, and the final neighborhood is an explicit
grid. Every evaluated point is cached by a canonical configuration hash.

## Architecture

`SAXSStabilityStudy` lives in the core/service boundary and accepts a baseline
configuration, bounded parameter domains, a trial evaluator, and a frame
selector. It returns an immutable `StabilityReport`. The evaluator is the
existing real SAXS rerun path; the study never mutates formal configuration.

The AI path supplies a bounded candidate and optional parameter priorities. It
does not choose acceptance. The study calculates:

- per-trial score and physical/quality gate status;
- a connected accepted plateau and per-parameter bounds;
- bootstrap confidence intervals for score and selected physical metrics;
- cross-frame median/MAD and continuity violations;
- a decision policy shared with the existing preprocessing UI decision model.

The default AI button requests `strict` mode. A later mode selector may request
`quick`, but both modes produce the same report contract and use the same
confirmation transaction.

## Data flow

```text
AI candidate/prior
  -> bounded StabilityStudyRequest
  -> deterministic global points
  -> active local points
  -> deterministic confirmation grid
  -> real SAXS trial results
  -> gates + bootstrap + continuity
  -> StabilityReport
  -> preprocess decision projection
  -> user confirmation
  -> PreprocessTransactionService apply/rerun/rollback
```

## Scientific corrections

- Preserve both quadratic roots of the invariant equation and select the upper
  root only when `crystallinity_gt_half` is true.
- Use signed corrected intensities for invariant/Fourier integrals. Positive
  filtering remains explicit for log-space fits.
- Return `NaN` plus support counts for bins with no detector observations.
- Pass an explicit Porod window into strain calculations and copy config before
  applying per-frame limits.
- Require a configurable slope tolerance around -4 and a robust `Iq4` plateau
  before Porod evidence is quantitative.
- Use wrapped angular distance for all chi masks and azimuthal interpolation.
- Publish `Kp` consistently from the static parameter object and normalize
  common q-unit spellings (`1/Å`, `A^-1`, `Å⁻¹`, `1/nm`).

## Failure and safety behavior

Invalid domains, missing q units, failed trial evaluation, non-finite metrics,
or disconnected accepted points yield `keep_original` or
`request_confirmation`; they never become an auto-apply decision. A cancelled
study returns a partial report marked incomplete. A report may be displayed and
persisted, but only the existing transaction can apply it.

## Testing strategy

Unit regressions cover each scientific correction with synthetic profiles and
detector sectors. Stability service tests use a deterministic evaluator and
assert cache reuse, plateau extraction, bootstrap determinism, continuity
gating, and all three decision outcomes. GUI tests assert that the AI entry
routes a stability report into the existing transaction boundary.
