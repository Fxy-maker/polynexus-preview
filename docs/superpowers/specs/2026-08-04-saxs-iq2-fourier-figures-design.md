# SAXS Iq2 and Fourier Figures Design

## Goal

Expose the existing complete `I(q)q^2` curves beside the existing Fourier
correlation `gamma(r)` evidence for ordinary, temperature, and strain SAXS
figure routes.

## Scientific contract

- `I(q)q^2` is projected from the already-emitted `analysis.kratky` payload;
  figure providers do not recompute or smooth intensity.
- The Fourier correlation plot remains `gamma(r)`, normalized by `Q*` and by
  its zero-distance value in the existing core. It may be captioned as the
  normalized `K(z)`-equivalent, but its stored/public name remains `gamma(r)`.
- The horizontal axis for correlation is `r`/`z` in nm. The horizontal axis
  for Kratky is `q` in nm^-1.
- Nonfinite or length-mismatched pairs are filtered in the provider with a
  projection-quality record; no interpolation or scientific reclassification
  is introduced.

## User-visible scope

- Ordinary/static SAXS: retain current diagnostic `Kratky vs q`; add complete
  `I(q)q^2` trace to the representative profile figure and static comparison
  where profile curves are available.
- Temperature/time SAXS: add `I(q)q^2` traces to selected-frame evidence and
  add an all-frame Kratky waterfall, parallel to the existing intensity
  waterfall.
- Strain SAXS: add a complete all-frame Kratky waterfall/overlay diagnostic;
  retain the existing scalar method-evidence panel for trend values.
- Existing correlation/IDF figure IDs and data contracts remain compatible.

## Out of scope

- No change to `kratky_analysis`, Fourier integration, normalization, or core
  physical calculations.
- No change to Porod-invariant, negative-intensity policy, or publication
  eligibility semantics beyond adding trace evidence.
- No GUI event-handler branching; figures remain `FigureDefinition` data.

## Acceptance criteria

- Every ordinary/static route with valid `analysis.kratky.q/kratky` exposes an
  editable `I(q)q^2` trace with q in nm^-1 and intensity_q2 in a.u. nm^-2.
- Temperature selected-frame evidence contains correlation and Kratky panels;
  temperature full-series output contains an all-frame Kratky trace figure.
- Strain output contains an all-frame Kratky trace figure when at least one
  valid frame exists, without replacing scalar method evidence.
- Correlation panels use `r_nm` and do not label the x-axis as q.
- Missing/invalid curves fail closed and preserve explicit projection quality.
- Focused tests cover all three providers and the existing figure document
  export contract.
