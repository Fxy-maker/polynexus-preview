# SAXS Post-Review-Consumer Real Boundary Re-audit Design

## Context

The current HEAD now propagates configured `saxs.2d` reviewer evidence through
the SAXS result, authoritative quality-evidence bundle, and persisted Figure
consumers. A real-data re-audit is needed to verify that this consumer-only
change did not alter the existing PAD8 scientific acceptance boundary or the
static/temperature/strain lifecycle.

## Design

Use the existing read-only PAD8 scientific-acceptance regression and the
existing real published-run walkthrough. Inspect only their final pytest
summaries and assertions. Do not add an alternate audit rule or interpret
detector geometry, mask validity, orientation, temperature, or strain meaning.

The audit records two independent facts:

1. Existing PAD8 evidence remains diagnostic-only despite software validation
   succeeding and publication flags remaining conservative.
2. Existing static, temperature, and strain lifecycle routes remain executable
   with their existing publication roles and diagnostic limitations.

## Safety and failure handling

The real fixture is read-only. Pytest output uses external D: basetemps. A
timeout, collection-only output, or missing final summary is not a pass. No
production or real-data file is included in the checkpoint allowlist.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts='
python -m pytest -q tests/test_saxs_real_2d_scientific_acceptance.py -vv --basetemp D:\PolyNexus_saxs_post_review_real2d_focus
python -m pytest -q tests/test_real_published_run_walkthrough.py -k saxs -vv --basetemp D:\PolyNexus_saxs_post_review_walkthrough
```

The exact observed results are recorded in the task card and acceptance note.
