# SAXS q-Resolved Orientation Reliability Design

**Date:** 2026-08-03
**Status:** Approved for implementation planning
**Related task:**
`docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability-design.md`

## Goal

Establish a no-calibration, q-resolved reliability layer for two-dimensional
in-situ tensile SAXS orientation. The first implementation milestone must
determine whether the zero-strain and low-strain frames are being compared in
the same scattering band and whether the observed orientation ordering is
stable to beam-center, mask, q-window, angular-binning, and resampling
perturbations.

The milestone does not make orientation monotonic with strain. It makes the
comparison auditable and fails closed when instrumental and sample anisotropy
cannot be separated.

## Current Evidence and Root Cause

The current detector-plane orientation path already preserves raw-detector,
sector-map, annulus-support, reference-axis, and reliability evidence. It also
keeps the final tensile-axis Herman value unavailable when the tensile axis is
unknown. These safeguards remain authoritative.

The remaining comparison failure has three structural causes:

1. Orientation is selected from one narrow annulus around a radial one-
   dimensional q-star candidate. Stable anisotropy outside that annulus can be
   missed, and different frames may effectively represent different features.
2. The diagnostic raw Herman value is referenced to each frame's own principal
   scattering axis. It is an anisotropy-magnitude diagnostic, not a common-
   axis tensile orientation measurement.
3. The chi-by-q map is integrated from the detector image and mask before the
   existing one-dimensional background, polarization, normalization, and
   smoothing path. Current quality reports identify many risks but do not
   estimate and subtract an instrumental azimuthal harmonic.

The observed zero-strain value must therefore not be forced to zero, and a
five-percent value below zero-percent must not be interpreted as a physical
decrease until the same q feature and perturbation stability are established.

## Available Calibration Boundary

The current experiment has no independent dark, flat-field, empty-cell,
background, or isotropic-standard EDF frames. Under this condition:

- the zero-strain sample frame is not an instrument blank;
- a persistent second azimuthal harmonic may be either instrument response or
  genuine initial sample orientation;
- automatic subtraction of that harmonic is scientifically underdetermined;
- the system may automatically detect, quantify, and display artifact
  sensitivity, but it must not subtract a suspected systematic harmonic;
- later calibration inputs must attach through an explicit correction
  interface without redefining existing orientation fields.

## Considered Approaches

### Calibration-only correction

Waiting for dark, flat-field, background, and standard frames gives the
cleanest instrument correction, but it leaves the current data without better
q-feature or sensitivity evidence.

### Zero-strain subtraction

Treating the zero-strain frame as an instrumental baseline would make the
reported delta zero by construction. It would also remove real processing,
mounting, residual-stress, or film-formation orientation and is rejected.

### No-calibration reliability with pluggable correction

The selected approach computes q-resolved orientation, tracks all correction
provenance, runs non-destructive perturbation diagnostics, and exposes future
calibration hooks. Only explicit invalid pixels and already confirmed masks
affect the authoritative input. Suspected defects, alternate centers, and
systematic harmonics remain candidate evidence.

## Scientific Semantics

### Detector-plane second harmonic

For each supported q bin, calculate the normalized complex second harmonic:

```text
M2(q) = sum[I(q, chi) * exp(i * 2 * chi)] / sum[I(q, chi)]
```

The sum uses only finite, supported angular bins and the existing support-count
contract. The harmonic provides:

```text
principal_axis_deg(q) = 0.5 * arg(M2(q))
anisotropy_strength(q) = abs(M2(q))
f_principal_raw(q) = 0.25 + 0.75 * abs(M2(q))
f_reference(q, alpha) = 0.25 + 0.75 * Re[M2(q) * exp(-i * 2 * alpha)]
```

`alpha` is an explicit detector-plane reference axis. A final tensile Herman
value requires `alpha` to be the supplied tensile axis and all applicable
quality gates to pass. The preserved detector-plane convention has an
isotropic baseline of `0.25`; it is not the common three-dimensional random
baseline of zero.

### Orientation meaning

The first milestone reports orientation of a measured scattering q band. It
does not infer that the band represents a chain axis, lamellar normal, void
major axis, or another material vector. Candidate features use neutral IDs and
`feature_kind="q_band"` until a separately reviewed assignment exists.

### Zero-strain delta

`delta_f_from_zero` is a descriptive paired comparison, not an artifact
correction. It is valid only when a later sequence-tracking milestone confirms
the same feature ID, q support, reference axis, and reliability policy. The
first milestone preserves the inputs required for that calculation but does
not publish sequence-level delta values.

### Stability interval

The first milestone reports a deterministic 95-percent resampling stability
interval from angular-bin block bootstrap. It is not labeled as a full
measurement confidence interval because detector counting statistics,
calibration uncertainty, and replicate variability are not available.

## Architecture

```text
raw EDF + header + confirmed mask
    -> immutable detector input and correction ledger
    -> support-aware chi x q integration
    -> q-resolved M2 map and resampling stability
    -> contiguous q-band candidates
    -> non-destructive sensitivity variants
    -> detached reliability evidence
    -> existing strain analysis transport
```

Scientific calculations remain in `polynexus/core/saxs_engine`. GUI code is
outside the first milestone and must later consume detached DTOs rather than
inspect algorithm internals.

## Component Design

### Correction ledger

Introduce a detached, strict-JSON-safe correction ledger. Each entry records:

```text
operation
status: applied | unavailable | not_requested | candidate_only
source
parameters
input_digest
output_digest
reason_codes
```

The ledger inventories existing behavior and prevents double correction. In
the first milestone:

- nonfinite pixels, explicit detector sentinels, explicit saturation, and an
  already confirmed mask may be excluded as currently authorized;
- statistical bad-pixel detection produces a candidate mask only;
- alternate beam centers are sensitivity candidates only;
- dark, flat-field, background, and isotropic-reference correction are
  recorded as unavailable when no explicit input exists;
- no image array or source path is serialized into the detached ledger.

### q-resolved orientation map

Add a focused core module responsible for harmonic calculation, bootstrap
stability, q-band candidate extraction, and detached serialization. It accepts
the existing chi-by-q intensity and support-count arrays and does not read EDF
files or GUI state.

Each q-bin record contains:

```text
q_bin_id
q_nm1
q_bin_width_nm1
harmonic_numerator_real
harmonic_numerator_imag
intensity_denominator
anisotropy_strength
principal_axis_deg
f_principal_raw
f_reference
reference_axis_deg
reference_axis_kind
effective_angular_bins
angular_coverage
support_fraction
harmonic_significance
stability_interval
level
reason_codes
```

`q_bin_id` is a deterministic identity derived from the canonical q-bin
bounds.  The harmonic numerator components and intensity denominator are
additive scalar statistics, not detector arrays; they are retained so a later
sequence task can reaggregate two frames over the exact same common q-bin set.
If any required additive term is unavailable, same-support delta calculation
must remain unavailable.

The module reuses existing configuration for minimum strength, effective bins,
angular coverage, harmonic significance, and axis drift. It does not introduce
a new publication threshold.

### q-band candidates

Candidate bands are contiguous q bins that pass the existing support and
harmonic-significance gates. Candidate-only smoothing may suppress isolated
single-bin changes, but reported M2 and Herman values always come from the
unsmoothed supported bins. One-bin gaps may be bridged only when both adjacent
segments pass and the gap itself has valid support. A candidate requires at
least three supported q bins; otherwise it remains a q-bin diagnostic.

Each candidate contains its q range, support-weighted center, integrated M2,
principal axis, stability interval, support summary, and neutral feature ID.
It also contains the ordered `supported_q_bin_ids` used for the aggregate. The
first milestone assigns frame-local IDs only. Cross-frame identity belongs to
the next atomic task.

### Resampling stability

Use a circular moving-block bootstrap over supported angular bins. The block
length is the larger of three angular bins and the number of bins spanning five
degrees. Use 256 deterministic replicates with a seed derived from stable
source evidence and the q-band bounds. Report the 2.5 and 97.5 percentiles for
anisotropy strength, principal-axis direction, and each applicable Herman
quantity.

Bootstrap failure does not erase the raw result. It records
`orientation_resampling_unavailable` and keeps the result diagnostic.

### Sensitivity runner

The reliability service evaluates the baseline result and bounded variants:

- beam center: the configured/header center plus a 3-by-3 grid of one-pixel
  x/y offsets;
- mask: the confirmed mask plus one-pixel and two-pixel beamstop-edge dilation
  variants, without changing unrelated mask regions;
- suspected bad pixels: one candidate-mask variant, never authoritative;
- q aggregation: baseline candidate bounds and 0.75/1.25 width variants;
- angular resolution: baseline chi bins and half/double resolution where the
  support contract remains valid.

Variant execution is bounded and may be disabled only through an explicit
configuration value recorded in the ledger. Inputs remain immutable.

Every sensitivity observation retains a stable `variant_id`, operation kind,
candidate ID, ordered q-bin identities, q range, orientation summaries,
eligibility, and reason codes. Aggregate min/max ranges alone are not enough
to establish whether a later frame still represents the same q feature.

No new absolute delta-f threshold defines `artifact_sensitive`. A candidate is
artifact-sensitive when a bounded variant changes an existing eligibility
decision, removes the candidate, changes its q-band identity, or violates the
existing axis-drift gate. Continuous ranges of f, axis, q bounds, and support
are always retained for review.

### Suspected systematic harmonic

The first milestone records per-frame and per-q complex M2 values but does not
classify or subtract a sequence-wide systematic harmonic. A later tracking
task may mark `systematic_harmonic_suspected` when a broad q component is
stable in detector coordinates across frames. That label remains diagnostic
without an independent calibration frame.

## Reliability States

The q-resolved evidence uses the existing evidence levels plus an explicit
reliability status:

- `usable`: all existing local gates pass, an explicit tensile reference is
  available where required, and sensitivity variants do not change
  eligibility;
- `diagnostic`: a numeric result exists but calibration, reference, or
  resampling evidence is incomplete;
- `artifact_sensitive`: bounded variants change existing eligibility, q-band
  identity, or axis-stability status;
- `unavailable`: inputs, support, or finite harmonic evidence are absent.

No-calibration status alone does not erase q-resolved diagnostics. It prevents
instrument-harmonic subtraction and quantitative publication promotion.

## Failure Behavior

- Missing tensile axis leaves final `f_reference` unavailable while retaining
  principal-axis diagnostics.
- Missing calibration inputs record unavailable corrections and never trigger
  zero-strain subtraction.
- Missing or incoherent support fails closed for affected q bins and bands.
- A masked wedge cannot be interpreted as zero-intensity scattering.
- A sensitivity variant cannot overwrite baseline geometry or mask state.
- Candidate-mask generation failure leaves the baseline analysis intact.
- If no q band passes, the q-resolved map and reason codes remain available.
- If the zero-strain frame is genuinely oriented, its absolute diagnostic is
  preserved.
- A five-percent result below zero-percent is permitted; the system reports
  whether the ordering is stable rather than forcing a monotonic trend.
- AI advice cannot change corrections, geometry, axes, gates, or values.

## DTO and Transport Boundary

The first milestone adds detached data equivalent to:

```text
QResolvedOrientationEvidence
  convention
  isotropic_baseline
  reference_axis_deg
  reference_axis_kind
  reliability_policy_digest
  correction_ledger
  q_bins
  q_band_candidates
  sensitivity_summary
  reliability_status
reason_codes
```

The policy digest is computed from the normalized reliability settings that
affect support, candidate eligibility, resampling, and axis drift. Later
same-feature comparisons require identical policy digests.

Existing scalar `f_herman`, `f_herman_raw`, detector reports, orientation
evidence, and table behavior remain backward compatible. The new evidence is
append-only. GUI and export projection are deferred.

## First Milestone File Boundaries

The implementation plan may change only core and focused test boundaries:

- create `polynexus/core/saxs_engine/saxs_orientation_reliability.py` for M2,
  q-band, bootstrap, ledger, and sensitivity contracts;
- modify `polynexus/core/saxs_engine/config.py` for bounded diagnostic settings;
- modify `polynexus/core/saxs_engine/preprocess.py` only to expose immutable
  integration inputs or execute approved sensitivity variants;
- modify `polynexus/core/saxs_engine/saxs_anisotropy.py` to attach the new
  evidence without redefining legacy fields;
- modify `polynexus/core/saxs_engine/saxs_quality_contracts.py` only if the
  existing evidence container cannot serialize the append-only DTO;
- modify `polynexus/core/saxs_engine/saxs_strain.py` only to transport detached
  frame evidence;
- add focused synthetic and read-only real-EDF tests.

No GUI, AI, database, export, memory, real-data, or publication-role file is in
the first milestone.

## Test Design

Synthetic tests cover:

- isotropic rings yielding the detector-plane 0.25 baseline;
- known second-harmonic rings with expected magnitude and axis;
- explicit tensile-axis projection distinct from the principal-axis value;
- multiple separated anisotropic q bands;
- a narrow q-star miss while another supported q band remains anisotropic;
- masked wedges and zero-support bins;
- one-pixel center offsets that change eligibility;
- beamstop-edge mask dilation variants;
- persistent single-pixel candidates that remain candidate-only;
- deterministic bootstrap output and unavailable-bootstrap failure behavior;
- strict JSON serialization and input immutability;
- backward compatibility of existing scalar orientation evidence.

Read-only real-data acceptance uses the available in-situ tensile EDF series.
It must record, without editing source files:

- q-resolved maps for zero and five percent;
- candidate q ranges and overlap;
- baseline and sensitivity-variant values;
- support, axis, and resampling evidence;
- whether the observed ordering survives the approved variants;
- an explicit statement that the result is diagnostic without calibration and
  a tensile-axis reference.

Real-data acceptance must not assert that orientation should increase
monotonically or that a particular q band is a molecular-chain feature.

## Acceptance Criteria

1. Every supported q bin exposes M2 magnitude, axis, support, stability, and
   convention evidence.
2. Multiple q bands can be detected without replacing the existing scalar
   orientation path.
3. Zero and five percent can be compared over explicitly reported overlapping
   q ranges.
4. Beam-center, mask, q-window, angular-resolution, and bootstrap sensitivity
   are machine-readable and non-mutating.
5. No calibration input, zero-strain frame, suspected bad-pixel mask, or
   systematic harmonic is silently used as a correction.
6. Existing axis, support, detector, and publication gates remain fail-closed.
7. Existing scalar fields and consumers remain backward compatible.
8. Synthetic tests, read-only real-EDF diagnostics, the complete SAXS matrix,
   and the structured verifier pass before implementation checkpoint.

## Phased Roadmap

1. q-resolved orientation and no-calibration sensitivity core: this spec.
2. Cross-strain feature tracking and same-feature delta-f evidence.
3. Explicit tensile-axis GUI input and detached results presentation.
4. Pluggable dark, flat-field, background, and standard-frame correction.
5. AI advisory ranking and explanation with no authority over calculations.

Each phase is a separate scientific or cross-module task with its own review
and checkpoint.

## Non-goals

- Do not force zero-percent orientation to zero.
- Do not force orientation to increase with strain.
- Do not treat zero-percent as instrument background.
- Do not subtract a suspected instrumental harmonic without calibration.
- Do not infer the tensile axis from the same scattering profile.
- Do not assign chain, lamellar, or void semantics to an unreviewed q band.
- Do not implement sequence feature identity, GUI, AI, or calibration
  correction in the first milestone.
- Do not modify real EDF files or unrelated workspace changes.

## Spec Self-review

- Placeholder scan: no unresolved marker or deferred decision is required for
  the first milestone.
- Consistency: all final tensile-axis values require an explicit tensile axis;
  diagnostic principal-axis values remain separate.
- Scope: the first milestone is core-only; sequence tracking, GUI, calibration,
  and AI are separate tasks.
- Ambiguity: no-calibration operation permits detection and sensitivity only,
  never zero-strain or systematic-harmonic subtraction.
- Testability: every output, failure state, perturbation class, and mutation
  boundary has focused synthetic or real-data acceptance evidence.
