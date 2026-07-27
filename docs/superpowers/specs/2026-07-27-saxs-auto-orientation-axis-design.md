# SAXS Automatic In-Plane Orientation Axis Design

## Context

The current SAXS strain path now receives EDF-derived `I(chi)` maps, but the
Herman consumer uses a fixed zero-degree reference and a polar-angle weight.
That makes the result unsuitable for arbitrary in-plane sample directions and
can suppress detector-plane orientation peaks. A single 2D detector image also
cannot prove the three-dimensional tensile/chain assignment.

## Design

Add an optional finite `SAXSConfig.orientation_axis_deg`. A finite value is the
explicit in-plane reference and always wins. When it is absent, the
anisotropy core extracts the dominant second-harmonic axis from the selected
azimuthal profile. The detector's 180-degree symmetry is handled by the
second-harmonic representation, so 0° and 180° are equivalent.

The detector-plane Herman calculation uses baseline-subtracted intensity as
the integration weight and computes the angle relative to the selected axis.
The polar `abs(sin(chi))` factor is not applied. The selected q* remains the
existing structural q*; this task does not optimize q for maximum anisotropy.

The result DTO retains the numeric factor and adds axis provenance:
`orientation_axis_deg`, `orientation_axis_source`, `orientation_axis_strength`,
and `orientation_axis_confidence`. Orientation evidence publishes those
values in the existing JSON-safe fit evidence dictionary. If automatic strength or valid-bin
requirements fail, the factor remains unavailable and evidence records a
diagnostic reason.

## Data flow

```text
EDF -> preprocess I_2d/q_2d/chi -> strain consumer
     -> analyze_anisotropy(cfg)
        -> q* profile -> explicit axis OR second-harmonic axis
        -> detector-plane Herman factor + axis evidence
     -> existing strain result/table transport
```

The GUI remains a consumer of existing result/evidence DTOs and does not branch
on the detection algorithm.

## Alternatives considered

1. Keep a hard-coded 90° axis. This preserves one mounting geometry but fails
   for rotated in-plane experiments.
2. Search all q bins and report the strongest orientation. This can select
   beamstop, void, or low-q artifacts and changes structural q semantics.
3. Use the second-harmonic axis at the existing q*. This is the chosen design:
   it generalizes the in-plane geometry without changing q selection, and it
   fails closed when the profile is too weak.

## Error handling and scientific limits

Non-finite profiles, insufficient bins, zero weight, or weak second harmonic
produce an unavailable axis/factor. Auto detection reports a principal
scattering axis only; assigning it to tensile, chain, or lamellar-normal
directions requires experiment metadata and may involve a 90° interpretation.
Out-of-plane/titled geometries are outside this task.

## Testing

- Synthetic anisotropic rings verify explicit-axis precedence and arbitrary
  auto-detected axes.
- Isotropic/weak profiles verify unavailable auto results.
- Existing EDF-shaped preprocessing, strain transport, table, and evidence
  tests remain green.
- JSON serialization is checked with `allow_nan=False` for finite evidence.
