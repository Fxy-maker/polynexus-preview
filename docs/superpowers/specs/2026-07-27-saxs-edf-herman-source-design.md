# SAXS EDF Herman Orientation Source Design

**Date:** 2026-07-27
**Status:** Implemented locally; scientific review remains open
**Goal:** Make a real 2D EDF frame produce the azimuthal evidence required for a finite Herman orientation factor in the in-situ strain result table.

## Root cause

The previous transport checkpoint retained `sector_data` and passed it into
the strain analyzer, but the producer only emitted radial profiles:
`q`, `I_full`, `I_merid`, and `I_equat`. The existing Herman consumer expects
azimuthal `chi` samples or equivalent nested sector arrays. The existing
`integrate_chi_sectors()` and `analyze_anisotropy()` functions were not on the
EDF preprocessing path, so every transported payload was structurally
insufficient and the table correctly rendered `None` as an em dash.

## Selected approach

1. Extend `integrate_chi_sectors()` with a NumPy geometry fallback when pyFAI
   is unavailable. This keeps EDF orientation analysis available under the
   repository's default `use_pyfai_integration=False` configuration while
   preserving pyFAI as the preferred integration path.
2. Have `preprocess_pipeline()` run the 2D azimuthal integration for
   anisotropic image input and add a canonical payload containing `I_2d`,
   `q_2d`, and `chi_rad` alongside the existing radial fields.
3. Make the existing strain Herman adapter recognize that canonical payload
   and delegate the actual factor calculation to `analyze_anisotropy()`.
   Legacy nested sector payloads remain supported.
4. Keep GUI code unchanged. The existing core transport and result-table field
   consume the resulting finite `f_herman`; failures remain explicit as
   `None`/em dash with diagnostic evidence rather than a zero fallback.

## Alternatives rejected

- Deriving orientation from the filename or the presence of `.edf`: the
  extension proves only the input container, not a valid azimuthal signal.
- Recomputing orientation in the GUI: this violates the core/service boundary
  and makes results depend on GUI state.
- Enabling only pyFAI: the default project configuration uses the manual
  integrator, so that would leave ordinary EDF runs unavailable.

## Data contract

An anisotropic EDF preprocessing payload may contain:

```python
{
    "q": q_radial,
    "I_full": I_full_smooth,
    "I_merid": I_merid_smooth,
    "I_equat": I_equat_smooth,
    "I_2d": intensity_by_chi_and_q,
    "q_2d": q_axis,
    "chi_rad": chi_axis_in_radians,
}
```

The strain adapter calls `analyze_anisotropy(I_2d, q_2d, chi_rad, q, I_full)`
and copies its finite `f_herman` into the existing `StrainPointResult`.
Missing/invalid geometry, isotropic input, an unavailable 2D map, or an
insufficient azimuthal profile leaves the factor non-finite and preserves the
existing unavailable-cell behavior.

## Boundaries

- Modify `polynexus/core/saxs_engine/preprocess.py` for 2D integration and
  payload production.
- Modify `polynexus/core/saxs_engine/saxs_strain.py` for canonical payload
  consumption.
- Add focused regressions in `tests/test_saxs_preprocess.py` and
  `tests/test_saxs_batch_parameters.py`.
- Do not modify GUI production code, raw EDF fixtures, or parallel release-audit
  memory files.

## Acceptance criteria

1. A synthetic anisotropic image with valid manual geometry produces an
   `I_2d/q_2d/chi_rad` payload from `preprocess_pipeline()`.
2. The canonical payload produces a finite Herman factor through the existing
   strain analyzer.
3. The SAXS engine publishes that finite value in `_batch_params["f_Herman"]`
   and existing table rendering remains unchanged.
4. 1D, isotropic, invalid-geometry, and insufficient-data paths remain
   explicitly unavailable rather than inventing zero.
5. Focused tests, the complete SAXS matrix, and the structured verifier pass.
