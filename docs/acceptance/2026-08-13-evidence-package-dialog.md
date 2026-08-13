# Evidence Package Dialog Acceptance

## Scope

`EvidencePackageDialog` is a read-only Qt inspector over the public
`EvidencePackageView` DTO. It provides four tabs: Overview, Evidence, Metrics,
and Review. It does not invoke analysis, mutate package data, select figures,
or read technique-provider internals.

## Real PA6 smoke

The immutable package below opened successfully in the Qt dialog:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\final-pa6-e2e-audit-v001
```

Observed dialog state:

- package: `final-pa6-e2e-audit`
- tabs: `Overview`, `Evidence`, `Metrics`, `Review`
- techniques: `dsc`, `ir`, `saxs`, `waxs`
- metric rows: `96`
- review rows: `6`

## Boundary checks

- Metric rows show value, unit, method, source locator, writing eligibility,
  and reason codes; the evidence/run provenance is present as a tooltip.
- Evidence rows retain Results and Discussion metric counts separately.
- Review rows and package-level limitations remain visible.
- Tables use `NoEditTriggers`; the only dialog command is Close.

## Verification

```text
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py
4 passed in 0.26s
```

The structured verifier and final checkpoint are recorded with this task.
