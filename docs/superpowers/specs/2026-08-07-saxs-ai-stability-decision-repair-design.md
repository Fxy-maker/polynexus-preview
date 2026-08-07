# SAXS AI Tuning and Stability Decision Repair Design

## Goal

Repair the scientific decision path that connects SAXS AI tuning, the
parameter-stability study, and the existing confirmation transaction. A valid
candidate must be rejected only for evidence that the candidate can influence,
and sequence validation must preserve real temperature/strain evolution while
detecting unsupported or discontinuous results.

## Scope

This phase repairs symptom routing, sequence-mode propagation, active
perturbation domains, orientation evidence, cross-frame continuity, plateau
semantics, interval labeling, and SAXS-specific GUI evidence. It preserves the
current seeded Latin-hypercube plus bounded local-refinement sampler.

The later optimization phase may replace or augment that sampler with
constrained Bayesian optimization. That algorithm change is deliberately out
of scope so scientific-gate repairs can be validated independently.

## Non-goals

- No unattended SAXS auto-application.
- No inference of missing tensile-axis, detector-saturation, geometry, or
  absolute-calibration metadata.
- No weakening of physical or quality gates merely to enable the Apply button.
- No replacement of the existing confirmation, hash-check, rerun, rollback,
  audit, or Undo transaction.
- No publication promotion or retrospective regeneration of historical runs.

## Decision Architecture

The workflow remains sequential:

1. AI tuning proposes bounded actions and retains the best accepted engine
   configuration.
2. The stability study starts from that configuration and constructs only
   perturbations that are active for the loaded data and selected processing
   mode.
3. Each trial runs through a typed cloned `SAXSConfig` and the actual
   `static`, `temperature`, or `strain` analysis path.
4. Scientific gates evaluate candidate-influenceable evidence separately from
   immutable or missing acquisition metadata.
5. A connected stable platform can produce `request_confirmation`; all other
   outcomes retain the original configuration with explicit reason codes.
6. User confirmation continues through `PreprocessTransactionService`, which
   reruns the selected configuration and rolls back on identity or gate failure.

AI advice is therefore a proposal/prior, not scientific acceptance authority.

## Symptom Ownership and Routing

`condition_axis_unstable` and `condition_axis_missing` belong to condition
metadata recovery. They must not authorize q-window changes. `adjust_q_crop`
remains available only for low-q contamination, q-window, invariant, lamellar,
or thickness-chain evidence with a direct causal relationship to the q range.

A complete recovered axis is not unstable merely because its values came from
filenames. When every frame has a finite condition value, the order is unique,
and continuity is acceptable, source confidence is retained as provenance and
manual-review context rather than promoted to an instability symptom. Missing,
duplicate, ambiguous, or discontinuous values remain fail-closed.

Candidate plans bind their target symptom to the action that generated them.
An action may resolve one of its declared target symptoms; it must not inherit
an unrelated global lead symptom and then be rejected for failing to change it.

## Mode Propagation

The stability evaluator derives the scientific mode from the active SAXS
configuration/submodule and normalizes it to `static`, `temperature`, or
`strain`. The same mode is used for:

- trial assessment;
- frame-value extraction;
- confirmation-contract projection;
- confirmed-rerun validation and audit.

Unsupported or conflicting modes yield `keep_original` with a typed reason;
they do not silently fall back to `static`.

## Active Perturbation Domains

Every requested parameter dimension must pass an activity check before it is
included in the study:

- `bg_scale_value` is active only when a background is present and the scale
  method consumes the manual coefficient.
- Beam-center perturbations are represented as offsets from the per-frame EDF
  header center so the header cannot overwrite the trial. Header absence uses
  the configured center with explicit provenance.
- `orientation_mask_dilation_px` remains a tuple of positive dilation radii;
  candidate values never change the configuration field to a scalar.
- Orientation-only parameters require detector/sector evidence.
- Guinier, Porod, correlation, and q-crop dimensions require the corresponding
  consumer and enforce coupled `minimum < maximum` constraints.

The report records excluded dimensions and reason codes. A study cannot claim
multi-dimensional stability from inactive or overwritten parameters.

## Cross-frame Continuity

Continuity is not a limit on physical response magnitude. For temperature and
strain sequences, a large monotonic or smoothly curved change is allowed. The
gate detects isolated jumps and trend breaks using robust local increments:

- finite aligned values are required for each evaluated metric;
- first differences are compared with the median and median absolute
  deviation of neighboring differences;
- a sign reversal is not a failure by itself, but an isolated increment well
  outside robust local support is;
- short sequences that cannot support robust jump detection remain explicit
  `insufficient` evidence rather than being treated as stable by default;
- static results use availability/quality evidence and do not fabricate
  cross-frame continuity.

The study-level continuity decision is calculated from the selected plateau,
not from every rejected parameter trial.

## Orientation Stability Evidence

Strain stability includes, when available:

- effective and raw Herman factors with their status;
- orientation axis and wrapped angular drift;
- harmonic amplitude/significance or equivalent orientation strength;
- orientation interval width and valid-frame coverage;
- tensile-axis provenance.

Missing tensile-axis evidence keeps the effective Herman factor diagnostic and
prevents orientation-specific acceptance claims. It does not make unrelated q
or Porod candidates responsible for repairing the metadata. Orientation
parameters require orientation evidence to be observed before they can belong
to a stable platform.

## Platform and Interval Semantics

Platform membership requires all of the following:

- physical and quality gates pass in the active mode;
- required metrics for each active dimension are observed;
- candidate-level sequence continuity is not failed;
- normalized parameter distance satisfies a dimension-aware neighborhood;
- the component has both the configured minimum point count and nonzero spread
  in more than one active numeric dimension when the study is multi-dimensional.

The existing resampling over accepted parameter trials is labeled a
`perturbation interval`. It describes robustness across explored settings and
is not presented as an experimental, frame-bootstrap, or fit-parameter
confidence interval. Experimental uncertainty estimation remains separate.

## GUI Decision Evidence

The AI tuning dialog displays SAXS-specific rows for:

- active and excluded perturbation dimensions;
- platform size, coverage, and parameter bounds;
- perturbation intervals;
- physical and quality gates;
- sequence continuity and frame count;
- orientation coverage/status when relevant;
- the reason an Apply action is unavailable.

The generic `protected metrics available` count is not used as the SAXS
evidence summary. `keep_original` continues to disable Apply;
`request_confirmation` enables the existing confirmation path.

## Failure and Safety Behavior

Trial exceptions, invalid coupled windows, missing consumers, mode conflicts,
and absent required evidence are serialized as reason codes. They never select
a configuration through score alone. A `keep_original` report may retain a
diagnostic highest-score trial for inspection, but the confirmation contract
does not expose that trial as applicable.

No stability trial mutates the live engine. Only the confirmed transaction may
apply a selected subset, and the post-rerun mode, configuration hash, physical
gate, and quality gate must all agree before persistence.

## Verification Strategy

Test-driven regressions will cover:

1. complete filename-derived condition axes do not trigger an unresolvable
   condition symptom;
2. q actions never target condition-axis symptoms, and per-action symptom
   binding does not inherit an unrelated global symptom;
3. strain and temperature stability trials use their actual modes;
4. background, beam-center, mask-dilation, and orientation domains are included
   only when their perturbations are active and preserve typed contracts;
5. smooth large strain evolution passes continuity while an isolated jump
   fails;
6. orientation metrics participate in strain stability and missing tensile-axis
   evidence remains diagnostic;
7. plateau selection excludes inactive dimensions and reports perturbation
   intervals accurately;
8. SAXS GUI evidence replaces the misleading generic zero-metric summary;
9. confirmation identity, rerun validation, rollback, and Undo regressions stay
   green.

Focused tests run before the structured task verifier. Scientific behavior
changes remain subject to human review before merge.
