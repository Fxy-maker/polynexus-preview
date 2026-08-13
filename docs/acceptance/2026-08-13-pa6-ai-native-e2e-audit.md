# PA6 AI-Native End-to-End Audit

## Goal audit

The requested PA6 evidence loop was exercised from real raw project junctions
through one `analyze-project` request, canonical replay, four technique
providers, immutable evidence package, citable metrics, ARS writing handoff,
and GUI-neutral package view.

## Fresh read-only replay

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Prepare PA6 DSC FTIR SAXS WAXS evidence" `
  --package-id final-pa6-e2e-audit
```

Fresh package:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\final-pa6-e2e-audit-v001
```

Verified facts:

| Requirement | Evidence |
| --- | --- |
| Four techniques in one package | `dsc`, `ir`, `saxs`, `waxs` in `manifest.json` and `techniques.json` |
| Canonical conversion provenance | Nonempty template and conversion hash sets in the package manifest |
| Citable metric provenance | 96 records in `citation-metrics.json`, each with source/run/method/unit/locator/status |
| Results/Discussion boundary | 42 Results candidate IDs, 54 diagnostic-only IDs in `ars-writing-input.json` |
| IR crystallinity safety | No FTIR `%` `Xc_pct` record; uncalibrated values are indices |
| SAXS/WAXS safety | All current SAXS/WAXS metrics are diagnostic-only |
| Human review boundary | Six explicit review actions; package is `review_required` |
| GUI consumer | `EvidencePackageView` loaded the package with four techniques, 96 metrics, and six review rows |

Raw data remained read-only and is not copied into the evidence package.

## Verification

Focused final matrix:

```text
python -m pytest -p no:cacheprovider -q tests/test_evidence_package_view.py tests/test_project_ars_writing_handoff.py tests/test_project_writing_metrics.py tests/test_project_workflow_package.py tests/test_project_workflow_adapters.py tests/test_ai_native_project_entrypoint.py tests/test_ai_project_candidate_groups.py tests/test_ars_group_figure_candidates.py
62 passed in 6.99s
```

Package-scope regression after audit repair:

```text
11 passed in 0.59s
```

Structured quality and preprocessing gates pass (`303` and `157`).  The full
boundary run reached `3907 passed, 31 failed, 21 skipped` in 2137.95 seconds.
The relevant stale project-workflow limitation assertion was updated in this
audit.  The remaining failures are pre-existing/unrelated GUI history, gallery,
sample browser, result template, and SAXS dirty-frame paths; they do not touch
the project workflow, citation, ARS handoff, or evidence-view modules changed
for this goal.  The full release boundary is therefore not claimed green.
