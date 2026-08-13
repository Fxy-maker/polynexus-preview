# Writing Metric Provenance Acceptance

## Scope

This checkpoint adds a deterministic `citation-metrics.json` ledger to the
immutable project evidence package.  It projects only documented provider
outputs; it neither changes an analysis algorithm nor modifies raw data.

## External PA6 replay

Read-only replay completed on 2026-08-13:

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Prepare PA6 DSC FTIR SAXS WAXS evidence" `
  --package-id writing-metric-provenance-replay
```

The resulting immutable package is:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\writing-metric-provenance-replay-v002
```

It contains six evidence items, all four requested techniques, and
`citation-metrics.json`.  Metric projection counts were:

| Technique | Eligibility | Count |
| --- | --- | ---: |
| DSC | `results_candidate` | 42 |
| FTIR | `diagnostic_only` | 48 |
| SAXS | `diagnostic_only` | 4 |
| WAXS | `diagnostic_only` | 2 |

## Boundary evidence

- DSC segment values preserve `dsc.isothermal_avrami_fit`, source locators,
  raw source hashes, units, and `review_required` status.  Results candidate
  means candidate writing evidence, not automatic publication approval.
- FTIR `Xc_pct` is represented as `PA6_A1200_A1637` with unit `index`, method
  `PA6_A1200_A1637_uncalibrated`, and
  `absolute_crystallinity_not_supported`; it is not a percent crystallinity
  Results value.
- SAXS invariant, Kratky, lamellar, and Porod records remain diagnostic where
  provider applicability is unresolved.
- WAXS `Xc_pct` and `D_Scherrer_nm` remain diagnostic and retain the existing
  peak-support/amorphous-partition reason codes.  They are not publication
  claims.

## Verification

```text
python -m pytest -p no:cacheprovider -q tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
32 passed in 3.25s
```

Raw PA6 sources were read through existing junctions only.  No raw source was
copied into the package or modified.
