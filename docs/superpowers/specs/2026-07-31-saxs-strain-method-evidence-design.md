# SAXS Strain Method Evidence Diagnostic Figure Design

## Goal

Expose existing strain per-frame Porod, Kratky, invariant, and lamellar
`MetricEvidence` as one auditable diagnostic Figure.

## Scope

Extend the strain SAXS Figure provider with
`saxs.strain.method_evidence`. The Figure consumes only
`SAXSFrameView.analysis.metric_evidence` and the existing frame condition
(`strain_pct`). It does not consume or derive a new strain model.

## Scientific and safety boundaries

- Do not recalculate any metric, normalize values, or infer a strain phase.
- Do not interpolate, fabricate, reorder, repair, or delete frames.
- Preserve nullable values, frame index, strain condition, source path, quality
  level, and reason codes in each audit source.
- Renderer sources contain only existing finite strain/value pairs. A method
  with fewer than two finite pairs remains audit-only so the existing V2 line
  binding contract cannot create an invalid or empty renderer scene.
- The Figure is always `publication_role="diagnostic"` and cannot affect
  quality levels, physical gates, AI/rescue state, or publication roles of
  existing Figures.
- Existing strain Figure IDs, evidence attachment, Manifest, and Export
  contracts remain unchanged.

## Figure contract

The Figure ID is `saxs.strain.method_evidence`, with `scope="series"` and four
panels (`porod`, `kratky`, `invariant`, `lamellar`). Every supported method
with any existing payload gets an audit source:

- `strain-method-evidence-{method}` contains `strain_pct`, `value`,
  `frame_index`, `source_path`, `frame_level`, and `frame_reason_codes`;
- `strain-method-evidence-{method}-plot` is emitted only for at least two
  finite existing pairs and contains `strain_pct` and `value`.

The recipe records `figure_kind="method_evidence_diagnostic"`,
`condition_axis="strain_pct"`, `missing_values_preserved=True`,
`interpolation=False`, `reclassification=False`, and
`renderer_minimum_pairs=2`.

## Acceptance criteria

1. Existing strain method evidence emits the diagnostic Figure with all four
   audit sources, including methods missing on some frames.
2. Audit values remain nullable and preserve frame identity, strain values,
   paths, levels, and reason codes without mutating input mappings.
3. Plot sources contain only finite existing pairs and never contain an empty
   or one-point V2 line source.
4. The Figure is strict-JSON-safe, V2-ready when renderable, and diagnostic.
5. Legacy strain Figure output is unchanged when no method evidence exists.
