# Unified Canonical Evidence Provenance Acceptance

Date: 2026-08-13

## Delivered boundary

The project workflow now requires a replayable canonical template before a
registered DSC, IR, SAXS, or WAXS provider route can execute.  DSC retains its
existing Mettler isothermal converter.  IR, SAXS, and WAXS use a deterministic
raw-file envelope converter that records the source-content identity without
changing any scientific algorithm.  IR directory sources remain supported by a
deterministic directory content hash.

Recipe validation and execution replay the registered template before a
provider runs.  Removing or changing its template makes the recipe invalid;
changing the raw source makes replay fail closed.

Evidence packages now retain workflow-wide limits at package level.  A
technique evidence item retains only its step-specific limits and the explicit
`human_review_required` boundary.  This prevents a SAXS/WAXS or generic
workflow limit from being represented as a DSC or FTIR observation.

## Focused verification

```text
python -m pytest -p no:cacheprovider -q \
  tests/test_project_workflow_package.py \
  tests/test_project_workflow_adapters.py \
  tests/test_ai_native_project_entrypoint.py \
  tests/test_tpae_golden_workflow.py \
  tests/test_agent_workflow_cli.py \
  tests/test_canonical_converter_registry.py \
  tests/test_canonical_experiment_templates.py \
  tests/test_dsc_canonical_isothermal_conversion.py

63 passed in 3.82s
```

The matrix covers registry conversion/replay, missing-template recipe blocking,
existing DSC compatibility, package-level versus item-level limitation
isolation, and project entrypoint packaging.

## External PA6 four-technique replay

The replay used a project-local read-only raw scope under:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814
```

Command:

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Prepare PA6 DSC FTIR SAXS WAXS evidence" `
  --package-id canonical-provenance-replay
```

Output package:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\canonical-provenance-replay-v001
```

All four technique entries are present and `review_required`:

| Technique | Converter | Template hash |
| --- | --- | --- |
| DSC | `mettler.dsc-isothermal.v1` | `29659c6757fd98454e678cb4202739a2e2f95cb59c54e64592ab38f8a182331f` |
| FTIR | `raw-file-envelope.ir.v1` | `228515179bd82d52cbc966013c2a30aac118642411a56d8ee46130cec2e524ed` |
| SAXS | `raw-file-envelope.saxs.v1` | `9014aceb96e1c38e244dd4492e94d751ddaca83f12618cc72b73aef5f701049c` |
| WAXS | `raw-file-envelope.waxs.v1` | `669a9acf19f369fdd2781c9a042c0ae79e0c5c2956ed6c1284a384c04d18775c` |

`limitations.json` retains the workflow-wide boundaries:
`unique_hydrogen_bond_species` and
`absolute_scattering_quantity_without_background`.  The DSC, FTIR, SAXS, and
WAXS writing evidence items instead retain `human_review_required` and no
unrelated item limitation.

## Scientific limits

This confirms provenance and workflow behavior, not publication conclusions.
The PA6 output remains review-required: DSC segmented multi-program fitting,
FTIR calibration/assignment, SAXS background treatment, WAXS model support,
cross-technique sample identity, manuscript interpretation, and final figure
selection all remain subject to expert review.
