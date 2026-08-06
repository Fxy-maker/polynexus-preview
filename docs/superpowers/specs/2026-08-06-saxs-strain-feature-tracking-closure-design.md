# SAXS Strain Feature Tracking Closure Design

**Date:** 2026-08-06
**Status:** Approved for implementation
**Approval source:** User request "按你说的修复" after review of the EDF 8 diagnosis
**Related task:** `docs/agent/tasks/2026-08-06-saxs-strain-feature-tracking-closure.md`

## Goal

Make one tracked lamellar feature the authoritative source for strain-series
long period and feature-local orientation. Expose total and orthogonal-sector
peak positions without inferring a tensile axis or silently switching features.

## Observed failure

The five-frame `Desktop/edf/8` sequence contains a strong two-dimensional
transition from a near-circular pattern to a pronounced directional streak.
The current scalar output hides or misstates that transition because:

- `analyze_strain_series()` and `SAXSAnalyzer._run_strain_pipeline()` each run
  a separate single-frame analysis and choose different long-period values;
- `analyze_anisotropy()` independently selects a Bragg candidate per frame,
  so orientation is not guaranteed to use the same feature as long period;
- sequence orientation tracking receives no source indices from the normal GUI
  route and fails with `source_index_mapping_invalid`;
- the strain table stores the scattering invariant under `Q_star` names;
- the detector preview includes sentinel-like log values in its automatic
  color range and visually suppresses real anisotropy.

## Chosen approach

Use the existing core contracts and close the missing sequence data flow.
`analyze_strain_series()` owns the one authoritative per-frame `SAXSResult`.
The first valid total-profile lamellar peak seeds a sequential q anchor. Each
later frame must select a candidate continuously from the previous accepted
peak. A missing credible candidate produces `tracking_lost`; the implementation
does not substitute an unrelated peak merely to keep a smooth curve.

The accepted total-profile q peak is passed explicitly to the orientation
annulus. Orthogonal sector peaks are measured against the same feature anchor
and reported as diagnostic directional values. Their names remain detector
coordinate based (`meridional` and `equatorial`) until an explicit tensile axis
maps them to parallel/perpendicular semantics.

The engine reuses the series-owned `SAXSResult` when building GUI rows and
figures. It does not rerun `analyze_single()` or replace `L_best` with a second
`L_bragg` choice.

## Data contract

Each strain point carries:

- `analysis_result`: the authoritative core result, excluded from detached
  serialization;
- `q_peak_total_nm1` and `L_nm`;
- `q_peak_meridional_nm1`, `L_meridional_nm`;
- `q_peak_equatorial_nm1`, `L_equatorial_nm`;
- `feature_tracking_status`, `feature_tracking_reason_codes`, and the previous
  accepted q reference;
- feature-local orientation evidence whose `q_star_candidate` equals the
  accepted total-profile q peak;
- `invariant_Q` and `invariant_Q_rel` for the scattering invariant.

Legacy `Q_star` aliases may remain in detached compatibility readers, but new
strain rows, figures, and table columns must use invariant names. A reciprocal
length named `q_peak_*` is always in `nm^-1`.

## Axis and interpretation boundary

`tensile_axis_deg` remains explicit configuration. When absent, final
`f_Herman` remains unavailable and the detector-plane projected raw diagnostic
remains visibly diagnostic. Principal scattering axes are never promoted to a
tensile axis. Meridional/equatorial labels are detector coordinates, not
parallel/perpendicular material assignments.

## Failure behavior

- Invalid or duplicate source-index mappings fail closed with existing reason
  codes; the normal GUI route supplies deterministic loaded-frame indices.
- A lost total-profile feature yields unavailable tracked q/L and orientation
  for that frame, with `tracking_lost`; it does not restart automatically.
- Missing sector profiles leave directional q/L unavailable without blocking
  the valid total-profile result.
- Missing tensile-axis evidence leaves final Herman unavailable.
- Detector preview scaling excludes nonfinite/nonpositive display sentinels
  from percentile limits while retaining the underlying evidence unchanged.

## Acceptance criteria

1. One `analyze_single()` call per retained strain frame owns total-profile
   long period, structure, quality, and figure inputs.
2. GUI `L_nm` equals the corresponding series `L_array` value.
3. Orientation annulus q equals the tracked total-profile q for every valid
   frame and never independently switches candidate.
4. Normal GUI series tracking has deterministic source indices and no
   `source_index_mapping_invalid` result.
5. Synthetic competing-peak and missing-peak tests prove continuity and
   fail-closed tracking loss.
6. Detector-coordinate sector q/L values are emitted with explicit names.
7. New output uses `invariant_Q` names and no strain table presents an
   invariant value as reciprocal-length q star.
8. The EDF 8 read-only regression shows the 5% orientation annulus follows the
   tracked lamellar feature and the 200%/400% GUI L values equal core results.

## Non-goals

- Do not infer the tensile axis, chain axis, lamellar normal, or void axis.
- Do not force a monotonic orientation or long-period trend.
- Do not identify low-q streaks as lamellar scattering without review.
- Do not change the detector-plane Herman convention.
- Do not modify raw EDF files, publication authorization, or AI authority.

## Verification

Focused synthetic tests cover peak continuity, tracking loss, shared annulus,
sector projection, invariant naming, source-index transport, and single-source
GUI rows. The external EDF 8 test is read-only and skips explicitly when the
dataset is unavailable. Final handoff requires the structured task verifier.

## Spec self-review

- No placeholder or unresolved scientific choice remains.
- The design preserves the existing explicit-axis contract and q-resolved
  orientation foundation.
- The scope is limited to the strain sequence and its immediate consumers.
- Detector-coordinate and material-coordinate meanings are explicitly
  separated.
