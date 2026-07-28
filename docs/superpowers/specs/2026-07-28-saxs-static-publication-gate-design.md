# SAXS Static publication gate binding design

Date: 2026-07-28
Status: approved working design

## Problem

The real Static bundle currently contains a rendered `saxs.static.sample`
figure with `publication_role="main"` and manifest `status="ready"`, while its
Guinier, Porod, Kratky, invariant, and lamellar evidence are Diagnostic. The
provider currently treats `quality_flag="OK"` as sufficient frame eligibility.
That conflates artifact generation with scientific publication authorization.

## Decision

Reuse the existing emitted publication candidate and reliability fields. A
Static frame is Main only when it has explicit `paper_figure_candidate=True`
and is not rejected by the existing error/reliability vetoes. Missing
authorization fails closed to SI. This changes only the role decision; it does
not calculate a new gate or reinterpret any metric.

The provider retains all available profile, supplementary, and diagnostic
definitions. When no definition is Main, the provider records
`no_publication_ready_figure` and the deterministic reason in recipe metadata
so the downgrade is visible in the Manifest/Workbench evidence boundary.

## Data flow

```text
SAXSResult / final_parameters
  -> SAXSFrameView
  -> existing publication candidate + reliability vetoes
  -> FigureEligibilityDecision
  -> Static FigureDefinition role
  -> Manifest/Gallery role and recipe downgrade reason
```

## Failure policy

- `ERROR:*` stays Diagnostic.
- Explicit candidate false stays Diagnostic.
- Candidate missing stays SI.
- Existing reliability vetoes remain effective.
- A renderable curve is preserved as evidence; it is never promoted merely
  because the renderer succeeds.

## Testing

Use real provider fixtures, not mocks of the decision helper, to prove the
behavior at the FigureDefinition boundary. Cover explicit approval, missing
authorization, explicit rejection, and preservation of diagnostic figures and
strict JSON-safe evidence. Existing temperature and strain role behavior is a
regression boundary and must remain unchanged.
