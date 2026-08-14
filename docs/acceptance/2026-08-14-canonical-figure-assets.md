# Canonical Figure Assets Acceptance

## Delivered behavior

New normal Figure Pipeline runs write SVG evidence assets only.  A Chart Editor
working revision may create a private preview for interaction, while the
explicit publish action creates the `paper_complete` SVG/PNG/PDF asset group.

Evidence packages write `figure-index.json`.  When an asset directory contains
an SVG plus `figure.png` or `preview.png`, packaging keeps only the SVG and
writes one logical index entry plus metadata.  Candidate manifests are rewritten
to package-relative SVG paths.  Existing packages without the index remain
readable through the legacy adapter.

`EvidencePackageView.figure_views` and the GUI gallery adapter consume the same
index DTO.  A direct ARS SVG is static; a valid Figure Project document remains
the required condition for object-level editing. Index v1 does not carry a
capability report, so package-gallery entries fail closed to static viewing;
Quick Analysis run-manifest entries retain their existing object editor route.

## Verification

```text
python -m pytest -p no:cacheprovider -q tests/test_run_figure_manifest.py tests/test_reactive_figure_matplotlib_renderer.py tests/test_project_workflow_package.py tests/test_ars_group_figure_candidates.py tests/test_evidence_package_view.py tests/test_ai_native_project_entrypoint.py tests/test_plot_gallery_service.py tests/test_figure_window_service.py tests/test_chart_editor_save_mixin.py
93 passed in 9.12s
```

## Real PA6 Replay

The following command used the existing read-only PA6 raw junctions:

```powershell
python -m polynexus project-workflow analyze-project `
  --project-root D:\PolyNexus-pa6-four-technique-smoke-20260814 `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-100.csv raw/ftir/PA6-JW-110.csv raw/ftir/PA6-JW-120.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Prepare PA6 DSC FTIR SAXS WAXS evidence" `
  --package-id canonical-figure-assets-pa6
```

Fresh package:

```text
D:\PolyNexus-pa6-four-technique-smoke-20260814\.polynexus\evidence\canonical-figure-assets-pa6-v002
```

Observed package facts: status `review_required`; techniques `dsc`, `ir`,
`saxs`, `waxs`; 112 logical index entries and 112 SVG files; zero PNG/PDF
files under package `figures/`; every indexed SVG and metadata file exists;
`ars-writing-input.json` exists.  Raw inputs were not copied or modified.

## Limits

This validates asset/provenance organization, not new scientific conclusions.
The package remains review-required. Direct ARS group figures remain static
until their generators can emit genuine Figure Project object documents.
Package-index capability promotion remains a separate follow-up.
