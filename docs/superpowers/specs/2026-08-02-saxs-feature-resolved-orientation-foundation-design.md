# SAXS Feature-Resolved Orientation Foundation Design

**Date:** 2026-08-02
**Status:** Awaiting written-spec review
**Related task:** `docs/agent/tasks/2026-08-02-saxs-feature-resolved-orientation-foundation.md`

## Goal

Replace the current implicit "one Bragg q* represents the whole detector"
orientation assumption with an evidence-bearing foundation that can later
report feature-resolved SAXS orientation. The first implementation milestone
defines the physical axis contract, preserves detector-bin support during
azimuthal integration, and separates raw-detector, sector-map, annulus, and 1D
quality domains.

The strain result table will ultimately publish a Herman value only when its
reference is an explicitly supplied tensile axis. Automatic image-derived axes
remain useful diagnostics, but are not tensile-axis evidence.

## Observed failure mode

The four real EDF frames under `Desktop/edf/610` demonstrate that the current
failure is structural rather than a missing-EDF or simple threshold problem:

- the raw EDF images are two-dimensional and contain almost no unexpected
  nonpositive detector pixels;
- the integrated `chi x q` maps contain thousands of zero-valued bins because
  the current map stores intensity without the number of source pixels that
  contributed to each bin;
- `analyze_anisotropy()` rebuilds a detector-quality report from that processed
  map and treats empty integration bins as detector defects;
- the strain adapter also applies global 1D low-q and invalid-pair reasons to a
  two-dimensional annulus result;
- the single 1D-selected q* misses stable anisotropy in other q bands for the
  5% and 60% frames.

Consequently, tightening or loosening the Herman confidence threshold cannot
resolve the underlying ambiguity. The pipeline first needs to retain what was
measured, what was integrated, which physical feature was selected, and which
axis the reported quantity references.

## Approved scientific semantics

### Axis contract

The following quantities are distinct and must never be silently substituted:

- `principal_scattering_axis_deg`: the detector-plane direction of the selected
  scattering feature, measured modulo 180 degrees from the configured detector
  chi origin. It may be estimated from the image.
- `tensile_axis_deg`: the detector-plane projection of the experimental tensile
  axis. It must come from explicit run configuration or source metadata; it is
  never inferred from the same azimuthal profile used to calculate orientation.
- `reference_axis_deg`: the axis used by the reported orientation calculation.
  A table-level tensile Herman value requires this to equal `tensile_axis_deg`.
- `orientation_vector_kind`: the physical object represented by the angular
  distribution, such as `scattering_vector`, `lamellar_normal`,
  `chain_axis`, or `void_major_axis`. Unknown assignments remain `unknown`.

Automatic axis detection is therefore named and transported as principal
scattering-axis evidence. In the absence of a tensile axis, the analysis may
report anisotropy strength and principal scattering direction, but the final
tensile-axis Herman cell is unavailable.

### Herman convention

The existing detector-plane calculation and its random-ring baseline near
0.25 are preserved during the foundation milestone. Every orientation result
must carry an explicit convention identifier and isotropic baseline so it
cannot be confused with the common three-dimensional convention whose random
baseline is zero.

Changing the mathematical convention, converting a scattering-vector
orientation into a chain-axis orientation, or applying a 90-degree structural
offset requires a separate reviewed scientific task. No conversion is inferred
from the sign or magnitude alone.

### Feature contract

Orientation belongs to one identified scattering feature, not to an entire
detector image. The target contract is a detached, JSON-safe record equivalent
to:

```text
OrientationFeatureEvidence
  feature_id
  feature_kind
  q_range_nm1
  q_center_nm1
  q_width_nm1
  principal_scattering_axis_deg
  tensile_axis_deg
  reference_axis_kind
  reference_axis_deg
  orientation_vector_kind
  herman_convention
  isotropic_baseline
  f_herman_raw
  f_herman_effective
  harmonic_significance
  angular_coverage
  effective_bins
  support_fraction
  axis_drift_deg
  axis_source
  reliability_status
  reason_codes
```

`f_herman_raw` records a reproducible calculation under the stated convention
and reference. `f_herman_effective` is finite only after the feature assignment,
reference axis, annulus support, angular evidence, and applicable quality gates
pass. Legacy fields remain readable during migration but must carry enough
evidence to identify their old auto-axis semantics.

## Quality-domain separation

The pipeline will maintain four quality domains:

1. `raw_detector_quality` describes the original EDF pixels, mask, saturation,
   beam center, and geometry provenance.
2. `sector_map_quality` describes the integrated map shape and finite numerical
   representation. Empty bins are not detector defects.
3. `annulus_quality` describes support, coverage, and usable azimuthal evidence
   only for the q range used by one orientation feature.
4. `radial_1d_quality` describes the azimuthally averaged q/I curve and blocks
   only metrics that consume the affected points or ranges.

Global raw-detector failures such as an unreadable image, invalid geometry, or
an unusable mask may block all derived orientation. A global 1D
`low_q_truncated` flag or nonpositive values outside the selected annulus do not
automatically veto a supported two-dimensional feature. The evidence records
which quality domain caused each gate.

## Sector-map support contract

`integrate_chi_sectors()` currently returns only q, mean intensity, and chi.
The foundation milestone introduces an internal result object containing:

```text
SectorMapResult
  q_nm1
  chi_rad
  intensity
  support_count
  support_fraction
  empty_bin_mask
  integration_backend
```

`support_count` is the number of valid, unmasked raw-detector pixels
contributing to each `chi x q` bin. `empty_bin_mask` is derived from zero
support, not zero intensity. `support_fraction` is normalized against the
available detector sampling for the relevant radial position and is used for
annulus coverage checks.

The NumPy fallback already computes `pixel_count`; it will retain and return
that array. The pyFAI adapter must obtain equivalent bin counts from the
integration result or an equivalent geometry-aligned support integration. If
support cannot be established, the result remains diagnostic with
`sector_support_unavailable`; it is not fabricated from intensity values.

During migration, existing tuple consumers may use a narrow adapter, but new
core analysis consumes the named result. GUI code never inspects occupancy or
implements SAXS gates.

## Data flow

```text
raw EDF + header + explicit tensile axis
    -> raw detector report + geometry/mask provenance
    -> chi x q integration + support_count
    -> sector-map numerical report
    -> feature candidate q range
    -> annulus support and azimuthal evidence
    -> principal scattering axis
    -> Herman calculation against explicit reference axis
    -> raw/effective feature evidence
    -> strain DTO and table projection
```

The first milestone ends after the support-aware annulus and physical-axis
contract are available. It does not yet scan or classify multiple q bands.

## Phased roadmap

1. Physical orientation contract and sector support foundation.
2. Annulus-local quality gates and removal of unrelated 1D blockers.
3. q-peak candidate evidence and validated q* selection.
4. Continuous q-band detection and feature-resolved orientation.
5. Tensile-axis configuration/metadata transport and explicit structural-axis
   conversion policies.
6. Strain-sequence feature tracking, feature switching, and axis-rotation
   diagnostics.
7. Results, dataframe, export, and review-context projection of feature-level
   evidence.
8. AI advisory integration that may rank candidate windows or suggest review
   parameters but may not invent axes, override gates, or rewrite results.

Each phase is an atomic scientific or cross-module task with focused real-data
acceptance. Later phases consume the contracts established here rather than
adding GUI-side algorithm branches.

## First milestone boundaries

The first implementation milestone may change:

- `polynexus/core/saxs_engine/preprocess.py` for the named sector-map result and
  support arrays;
- `polynexus/core/saxs_engine/saxs_anisotropy.py` for support-aware annulus and
  explicit axis/convention evidence;
- `polynexus/core/saxs_engine/saxs_quality_contracts.py` for detached quality
  and feature-evidence serialization;
- `polynexus/core/saxs_engine/saxs_strain.py` only as needed to transport the
  new evidence without adding scientific logic to consumers;
- focused SAXS tests and real-EDF acceptance diagnostics.

The GUI, AI advisor, publication roles, multi-q feature detector, and existing
real EDF files are outside the first milestone.

## Failure behavior

- Missing tensile-axis evidence makes the table-level tensile Herman value
  unavailable and records `tensile_axis_unknown`; it does not become zero.
- Missing sector support records `sector_support_unavailable` and keeps the
  orientation diagnostic-only.
- Empty integration bins are excluded by support and do not produce
  `nonpositive_pixels` detector reasons.
- A selected annulus with insufficient support records an annulus-local reason.
- A valid raw detector is not downgraded because a processed sector map contains
  empty bins.
- Legacy results remain readable, but legacy auto-axis values are not promoted
  to the new tensile-axis meaning.

## Verification strategy

Focused synthetic coverage will include isotropic rings, strong anisotropic
rings, masked wedges, empty sector bins, background-corrected negative values,
explicit and absent tensile axes, and support unavailable from an integration
backend.

Real-data acceptance will use the four `610` EDF frames as read-only external
inputs. It will verify raw-detector defect counts, sector support, annulus-local
reasons, and preservation of currently observed q* evidence. The foundation
milestone must not claim that 5% or 60% has lamellar orientation merely because
another q band is anisotropic; that conclusion belongs to the later
feature-resolved task.

The existing complete SAXS matrix and the task-scoped verifier remain required.
Scientific acceptance must compare machine-readable evidence rather than assert
that orientation increases monotonically with strain.

## Non-goals

- Do not tune confidence thresholds to force desired strain trends.
- Do not force the zero-strain frame to have zero orientation.
- Do not infer a tensile axis from the observed scattering maximum.
- Do not equate low-q void/domain anisotropy with lamellar or chain orientation.
- Do not change the detector-plane Herman formula in the foundation milestone.
- Do not add AI-controlled physical calculations or GUI-side SAXS logic.
- Do not modify real EDF files, parallel memory edits, or generated test output.

## Acceptance criteria

1. Every orientation result identifies its feature, convention, reference-axis
   kind, axis source, and quality-domain reason codes.
2. A final tensile-axis Herman value is unavailable when the tensile axis is
   absent, while principal scattering-axis diagnostics remain available.
3. Sector integration preserves per-bin source-pixel support for both supported
   backends or fails closed with an explicit reason.
4. Empty `chi x q` bins are distinguishable from measured zero/nonpositive
   intensity and no longer masquerade as raw detector defects.
5. Annulus-local support can be evaluated without applying unrelated global 1D
   low-q defects.
6. Existing raw/effective Herman evidence remains backward readable and is not
   silently redefined.
7. Synthetic and real-EDF acceptance tests pass without mutating source data.

## Spec self-review

- Completion scan: no unresolved marker or unspecified implementation decision
  is required for the first milestone.
- Consistency: the table contract, axis contract, failure behavior, and phased
  boundaries all require an explicit tensile axis for final Herman output.
- Scope: multi-q detection, feature classification, GUI projection, and AI
  behavior are explicitly deferred into separate atomic tasks.
- Ambiguity: the current 2D Herman convention is preserved and labeled; no
  scattering-to-chain conversion is implied.
