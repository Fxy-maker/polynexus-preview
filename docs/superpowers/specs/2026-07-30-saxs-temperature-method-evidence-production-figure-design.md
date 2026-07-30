# SAXS Temperature Method Evidence Production Figure Design

## Goal

Carry the existing temperature-frame Porod, Kratky, invariant, and lamellar
evidence into the production temperature Figure provider.

## Scope

Extend `figure_temperature.build_temperature_figure_definitions()` with the
same diagnostic-only Figure id used by the portable provider:
`saxs.series.temperature.method_evidence`. The provider reads method evidence
from the existing `TempSeriesResult.temp_points`, binds it to frame views only
through a unique emitted `source_index`, and uses the existing condition axis.

## Safety and scientific boundaries

- No analysis, method calculation, quality classification, physical gate,
  rescue, AI, or publication decision is changed.
- Invalid, negative, missing, or duplicate source mappings do not get repaired
  positionally. Ambiguous frames remain absent from the method evidence plot
  and remain represented as nullable audit rows when their frame is known.
- Missing/non-finite method values are preserved as `None` in audit sources and
  omitted only from their finite renderer line. No interpolation or copying is
  allowed.
- The Figure is always `publication_role="diagnostic"` and does not alter the
  existing evolution Main Figure or its eligibility gates.
- Time-axis Figure calls are unchanged; this slice applies only when the
  existing condition axis is temperature.

## Acceptance criteria

1. A production temperature engine with existing method evidence emits the
   diagnostic Figure with four method audit/plot source pairs.
2. Audit sources preserve condition, value, source index, frame level, and
   reason codes; plot sources contain only finite existing pairs.
3. Duplicate or invalid source-index bindings fail closed without selecting a
   neighboring frame or changing the existing series evidence.
4. The Figure is strict JSON/V2 valid, detached, diagnostic-only, and does not
   change the existing Main evolution definition.
5. Focused production tests, structured verification, exact SAXS matrix,
   storage dry-run, diff check, and an explicit allowlist checkpoint are
   recorded.
