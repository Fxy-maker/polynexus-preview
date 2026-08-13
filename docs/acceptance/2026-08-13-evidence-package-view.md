# Evidence Package View Acceptance

## Scope

The GUI now has a technique-neutral `EvidencePackageView` and a small adapter
that consumes it.  It reads only immutable package JSON; it does not inspect
DSC, FTIR, SAXS, or WAXS provider internals and cannot modify the package.

## Real PA6 package load

The following package was loaded read-only:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\ars-writing-handoff-replay-v001
```

The view reports `review_required`, four techniques (`dsc`, `ir`, `saxs`,
`waxs`), six evidence items, 96 metric rows, and six human-review actions.
Both `results_candidate` and `diagnostic_only` metric eligibility are retained.

## Contract boundaries

- The loader verifies all writing-evidence metric IDs against the citation
  ledger and requires the ARS Results/Discussion split to cover exactly that
  set.
- A diagnostic metric cannot be projected into Results; a Results candidate
  cannot be silently recast as a diagnostic item.
- GUI summary data comes from the DTO only, with no technique-specific
  algorithm branch and no automatic figure/claim promotion.

## Verification

```text
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_project_ars_writing_handoff.py tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py
37 passed in 3.64s
```
