# SAXS Review Warning Reduction Design

**Date:** 2026-07-31
**Status:** approved by user for implementation

## Problem

The `610` four-frame series is labeled with repeated review warnings. Some
warnings are valid conservative gates, but the current output conflates
directory/sample identifiers with the confirmed filename strain axis, counts a
declared EDF background floor as an unexpected defect, and repeats the same
detector audit text across four frame reports and two presentation fields.

## Design

The condition parser will apply semantic pattern scoping: patterns prefixed
`strain_` are considered only for `experiment_type="strain"`, and `temp_`
patterns only for `experiment_type="temperature"`. Within strain patterns,
`strain_dash_S_suffix` is evaluated before `strain_directory_code`, so the
confirmed `000/005/060/200` filename values win over the directory's `610`
sample code. Explicit context/header values retain priority over paths.

The raw detector report will keep raw counts, including total nonpositive,
background-floor, masked-sentinel, and unexpected-negative counts. A new
unexpected-nonpositive count excludes the declared floor and the configured
mask. Only unexpected nonpositive values and invalid mask shape remain defect
reasons; expected floor and shape-matched configured mask exclusions remain
visible but do not independently downgrade the frame.

Geometry provenance will use a structural status for a complete EDF metadata
set. This status is accepted by the provenance audit as evidence that the
fields are present and internally sourced from EDF; it does not assert that a
standard sample calibration or physical acceptance review has occurred. A
configured mask with matching detector shape receives the analogous structural
status, while an absent or mismatched mask remains conservative.

The GUI detector audit formatter will deduplicate identical serialized audit
details within each presentation field. It will preserve one audit record per
distinct report, but will not multiply the same text merely because four frame
reports have identical structural state.

## Boundaries

No q formula, pyFAI integration selection, detector pixel values, mask pixel
selection, saturation threshold inference, or scientific publication gate is
changed. `Saturation=0` remains an explicit unavailable upper limit and stays
advisory. The geometry status remains structural metadata evidence, not a
replacement for an experimental standard-sample check.

## Test strategy

Add RED tests for filename-vs-directory strain precedence, static pattern
scoping, expected floor/mask classification, complete-EDF structural status,
and duplicate audit formatting. Preserve existing tests for missing metadata,
invalid geometry, explicit saturation, and source-kind separation. Run the
focused SAXS tests and the repository structured verifier.
