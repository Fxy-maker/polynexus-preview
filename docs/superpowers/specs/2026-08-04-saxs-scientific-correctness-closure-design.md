# SAXS Scientific Correctness Closure Design

**Date:** 2026-08-04
**Scope:** SAXS physical core, entry/I/O contracts, batch provenance, geometry/figure eligibility, and result-table semantics.

## Goal

Close the 14 known SAXS findings with either physically correct behavior or an explicit fail-closed result. No result may silently change meaning because of units, acquisition direction, entry point, sector selection, or hidden truncation.

## Decisions

1. **Signed residuals are preserved.** Background subtraction returns signed corrected intensity. Raw/corrected arrays and quality statistics retain negative finite residuals. Positive-only consumers (log fits, positive Porod regression, and display transforms) receive an explicit positive mask and never rewrite the source array.
2. **Invariant crystallinity is unit-invariant or unavailable.** The implementation will derive the dimensionless Porod-invariant term from one declared q-unit system, convert q and length values together, and add an nm/Angstrom equivalence test. If absolute contrast/normalization is unavailable for a physically dimensionless crystallinity estimate, the field is `NaN` with an evidence reason instead of a unit-dependent number.
3. **Cooling preserves acquisition order.** Temperature sorting is heating-only. Cooling phase labels use the low-temperature solid reference: high normalized invariant is solid, low normalized invariant is melt, and the intermediate interval is crystallization.
4. **Total and sector channels are separate.** Full isotropic intensity is the only source for invariant, Porod, Guinier, Kratky, long-period, and structure metrics. Equatorial/meridional channels are restricted to orientation and anisotropy consumers.
5. **Frame limits are explicit.** The default batch path has no hidden 10/48 frame truncation. Optional limits are configuration values and every omitted frame is recorded with a reason and limit in sequence QA/provenance.
6. **Publication eligibility is evidence-gated.** A non-empty header or `quality_flag=OK` is insufficient without the required geometry and physical checks. Missing evidence produces SI/diagnostic roles, never a main figure.

## Boundaries

### Physical core

- `polynexus/core/saxs_engine/saxs_physical_helpers.py`: unit-safe invariant/Porod terms.
- `polynexus/core/saxs_engine/saxs_temperature.py`: cooling phase semantics, sequence ordering, Gibbs/thermal parameter propagation.
- `polynexus/core/saxs_engine/core.py`: signed-profile boundary, positive-only consumer masks, q-min provenance.
- `polynexus/core/saxs_engine/saxs_strain.py` and `polynexus/core/saxs.py`: total-vs-sector channel routing.

### I/O and workflow

- `polynexus/core/saxs_engine/io.py` and `polynexus/core/saxs.py`: one extension/read contract, HDF5/Nexus selection, explicit batch limits.
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: signed residual statistics and truncation evidence.

### Presentation

- `polynexus/core/saxs_engine/figure_eligibility.py`: geometry/physical gate enforcement.
- `polynexus/gui/result_table_templates.py`: diagnostic versus primary field policy.

## Acceptance contract

- Unit probe: equivalent synthetic profiles expressed in nm^-1 and Angstrom^-1 produce the same dimensionless invariant result within tolerance, or both fail closed with the same reason.
- Cooling probe: normalized invariant `1.0` returns `COOLING_SOLID`; `0.1` returns `COOLING_MELT`; a monotonic cooling time axis remains acquisition ordered.
- Channel probe: changing only the equatorial sector changes orientation outputs but does not change full-channel invariant/Porod/Guinier/structure outputs.
- Signed-noise probe: a zero-mean negative residual remains in corrected/raw payload and does not become a positive floor; positive-only fits report masked coverage.
- I/O probe: every declared extension either loads through the single-file route or returns a typed, actionable unsupported-dataset error. Directory and single-file routes share the same processed intensity boundary.
- Truncation probe: configured limits create `skipped` records; unlimited mode loads all discovered frames subject only to read failures.
- Figure probe: incomplete geometry, invalid Q-star, or unavailable void fraction cannot become a main/publication figure.

## Non-goals

- No new detector calibration inference from incomplete headers.
- No automatic physical rescue, interpolation, or synthetic time generation.
- No rewriting of historical generated assets; regenerated outputs are required for new semantics.
- No push, merge, deployment, or deletion of user-owned data.
