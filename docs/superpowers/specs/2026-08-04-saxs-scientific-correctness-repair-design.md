# SAXS Scientific Correctness Repair Design

**Date:** 2026-08-04
**Scope:** Remaining physical, temperature, unit, geometry, 2D orientation,
and container-input defects after the SAXS correctness closure work.

## Goal

Make every repaired SAXS path physically explicit and fail closed when the
metadata or acquisition evidence cannot support a quantitative result.

## Architecture

The existing SAXS service boundaries remain intact. A small set of helpers will
own contracts rather than moving logic into the GUI: a declared-q-unit
normalizer, a uniform-q preparation path for Fourier operations, a finite
Guinier boundary extrapolator, and sequence endpoint/time gates. Result DTOs
retain legacy numeric fields for compatibility but add status/reason metadata;
GUI labels describe the convention instead of changing the mathematics.

## Data flow

1. Readers attach `q_unit` and provenance. Text files with no declaration are
   loadable but absolute metrics receive `unit_unavailable`.
2. Background correction operates on raw profiles using the measurement
   equation, then sample transmission/thickness normalization is applied.
3. Correlation/Porod consumers receive a sorted, deduplicated, uniformly
   sampled q view. The original signed profile remains available for quality
   reporting and positive-only fits use explicit masks.
4. Full profiles feed invariant, Porod, Guinier, and structure metrics. Sector
   profiles feed only orientation/anisotropy consumers.
5. Temperature analysis computes endpoint references and validity gates from
   the complete ordered sequence before deriving Xc or kinetic fits.

## Physical conventions

The documented invariant is `Q=integral(q^2 I(q) dq)=2*pi^2*drho^2*phi*(1-phi)`.
The Porod constant is `Kp=lim(q^4 I(q))=2*pi*drho^2*Sv`. For a lamellar period
`L` with two interfaces, `Sv=2/L`; therefore
`phi*(1-phi)=2*Q/(pi*Kp*L)`. Specific surface requires the phase factor:
`Sv=pi*phi*(1-phi)*Kp/Q`. These equations are independently tested with
synthetic `drho`, `phi`, and `L`, not by generating Q with the implementation
under test.

## Temperature gates

Cooling and isothermal Xc use fixed `Q_melt` and `Q_solid` references selected
from the complete sequence or explicit inputs. No point is assigned Xc merely
because it is the current running maximum. `times=None` produces an Avrami
payload with `valid=False` and reason `time_axis_required`; frame indices are
never labeled seconds. Gibbs-Thomson consumes only finite points marked inside
the melting window and requires `delta_Hf_Jm3` from configuration or the API.

## Input and orientation contracts

`extract_geometry_from_header()` returns a fresh config for each frame.
HDF5/Nexus selection is deterministic only when exactly one highest-priority
candidate exists; otherwise it raises `UnsupportedDatasetError`. The
detector-plane orientation value is labeled `projected_order_parameter_2d`
while `f_Herman` remains a compatibility alias with convention metadata.
Sector masks use wrapped angular distance so both sides of each axis contribute.

## Error handling and compatibility

No raw signed residual is clamped. Missing units, invalid geometry, absent
time, missing melting evidence, or ambiguous datasets return structured reason
codes rather than guessed numbers. Existing callers that only inspect legacy
fields continue to receive NaN/unavailable values instead of silently changed
units.

## Testing strategy

Every behavior starts with a focused failing pytest. Tests cover analytic
background scaling, finite Guinier boundary, independent Porod equations,
unit conversion and unitless blocking, sequence endpoint/time gates, fresh
frame configs, wrapped sectors, q-grid preparation, HDF5 ambiguity, and Q
confidence ordering. The focused suite is followed by the task verifier and
full/boundary verifier.

## Non-goals

This design does not implement Ruland stripe analysis, Vonk desmearing,
absolute detector calibration, contrast inference, or changes outside SAXS.
