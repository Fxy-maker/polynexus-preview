 # SAXS Static Method Evidence Diagnostic Figure Design

 ## Goal

 Expose existing static per-frame Porod, Kratky, invariant, and lamellar
 `MetricEvidence` as one auditable diagnostic Figure definition.

 ## Scope

 Extend the static SAXS Figure provider with
 `saxs.static.method_evidence`. The Figure consumes the already-emitted
 per-frame `metric_evidence` mappings on `SAXSFrameView.analysis` and uses
 `frame_index` as the static sequence axis. It emits one nullable audit source
 and one finite-value plot source for each supported method that has at least
 one finite pair.

 ## Scientific and safety boundaries

 - Do not recalculate Porod, Kratky, invariant, or lamellar values.
 - Do not interpolate, fabricate, reorder, or repair frames or source paths.
 - Preserve nullable values, frame index, source path, quality level, and reason
   codes in the audit source. Malformed or non-finite values become `None`.
 - The plot source omits only pairs whose existing frame index or metric value
   is not finite; it does not change the audit source.
 - Use the existing metric units: Porod and invariant `a.u.`, Kratky `nm^-1`,
   and lamellar `nm`.
 - The Figure is always `publication_role="diagnostic"` and cannot promote a
   publication Figure or alter physical, quality, AI, or rescue gates.
 - Existing Figure IDs, evidence attachment, Manifest, and Export contracts
   remain unchanged.

 ## Figure contract

 The Figure has ID `saxs.static.method_evidence`, `scope="series"`, and four
 panels (`porod`, `kratky`, `invariant`, `lamellar`). For each method it emits:

 - `static-method-evidence-{method}` with columns `frame_index`, `value`,
   `source_path`, `frame_level`, and `frame_reason_codes`;
- `static-method-evidence-{method}-plot` with only finite `frame_index` and
  `value` pairs, emitted only when such pairs exist. An audit-only method has
  no empty renderer source.

 The recipe records `figure_kind="method_evidence_diagnostic"`,
 `missing_values_preserved=True`, `interpolation=False`, and
 `reclassification=False`. An empty or entirely absent metric collection does
 not emit an empty Figure.

 ## Acceptance criteria

 1. A static engine with any supported per-frame method evidence emits the
    Figure with all four audit sources, including methods that are absent on
    particular frames.
 2. Audit sources preserve frame positions and source paths, retain missing or
    non-finite values as `None`, and preserve level/reason metadata.
 3. Plot sources contain only finite pairs and do not mutate the input analysis
    or metric mappings.
 4. The Figure is strict-JSON-safe, passes the existing Figure v2 validator,
    and remains diagnostic.
 5. Existing static Figure ordering and legacy consumers remain unchanged when
    no method evidence is present.
