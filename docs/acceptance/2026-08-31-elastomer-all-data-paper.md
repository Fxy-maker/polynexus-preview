# All-technique elastomer paper draft acceptance — 2026-08-31

## Scope and deliverables

This checkpoint closes the reproducible build and audit of the Chinese working
manuscript on the current PA6/PA11/PA12 versus PA-50 crystallization response.
Raw files and earlier evidence/manuscript snapshots were not modified.

- Frozen evidence package:
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\.polynexus\evidence\elastomer-all-data-paper-v001`
- Manuscript output:
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\manuscript\even-nylon-crystallization-v002-r10`
- DOCX/PDF visual-QA output:
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\manuscript\even-nylon-crystallization-v002-r10\docx_render`

The manuscript is a review-required working draft, not a publication-ready
scientific acceptance. The `-50` suffix remains a nominal PTMG feed label.

## Independent external audit

The package loaded through `load_evidence_package_view` with:

| item | result |
|---|---:|
| package status | `review_required` |
| package runs | 52 |
| evidence items | 62 |
| metric records | 7,619 |
| indexed figures | 193 |
| indexed tables | 156 |
| artifact hashes checked | 1,568; 0 mismatches |
| package hash recomputation | matched `74c413473c0a9a139a662bbbacf34b9f7a4f96768a2edeae80674d8ebd38d52a` |

Technique views were DSC 18 runs/18 evidence, IR 6/6, NMR 26/26, WAXS
1/6, and SAXS 1/6. The raw audit reports 554 files across the six paired
samples, with duplicate export families and missing PA-50 solid-NMR sources
explicitly recorded.

The r10 `manuscript.json` round-tripped through the shared
`ManuscriptSource`, `ClaimRecord`, `FigurePlan`, `CitationRequest`, and
`FormulaRecord` contracts (21 claims, 8 figure plans, 27 citation requests,
and 3 formulas). `preflight.json` reports zero errors and shared-contract
checks `claims=passed`, `figures=passed`, `citations=passed`, and
`formulas=passed`. The manuscript contains the approved `69.9` value and no
`69.8` value. C07–C09 retain the complete paired DSC run provenance in the
claim-evidence matrix (4, 6, and 8 evidence references respectively).

The ARS/Suite handoff was executed against the same immutable package with
`python -m polynexus suite handoff --package <package>`: status=`ready`,
techniques=`dsc, ir, nmr, saxs, waxs`, metric count `7,619`, and
`human_review_count=62`. The handoff returns package-relative
`ars-writing-input.json`, `result-tables.json`, `writing-evidence.json`,
`citation-metrics.json`, and `review-decision.json`; no second scientific
result representation is created.

## Focused repository verification

Commands required by the task card:

```powershell
python -m pytest -p no:cacheprovider -q `
  tests/test_project_evidence_workspace.py `
  tests/test_evidence_package_view.py `
  tests/test_paper_pipeline.py

python scripts/verify.py `
  --task docs/agent/tasks/2026-08-30-elastomer-all-data-paper.md `
  --changed --types

git diff --check
```

Observed results:

- package/evidence/paper focused tests: **14 passed**;
- `test_all_data_manuscript_builder.py`: **25 passed**;
- task-scoped verifier: **selected checks passed** (Ruff, `py_compile`,
  quality gate **313 passed**, preprocessing gate **157 passed**, and
  whitespace check);
- `git diff --check`: clean.
- ARS/Suite package handoff: **ready** (`human_review_count=62`, all five
  technique views present).

These commands should be rerun before any future manuscript regeneration.

## DOCX/PDF visual QA

LibreOffice 26.2.4.2 converted `manuscript.docx` to a 21-page US-letter PDF.
The bundled document renderer then rasterized all 21 pages with PyMuPDF-backed
inspection. No empty page, clipped text, overlapping figure/caption, broken
table border, or replacement character was observed. Text extraction reported
21 non-empty pages and zero U+FFFD replacement characters. The preflight length
gate records 11,533 Chinese characters in the body (11,537 including the
reference heading), above the requested 10,000-character minimum.

The direct `soffice.exe` probe was not used as acceptance evidence because the
Windows GUI launcher exited abnormally; the successful `soffice.com` invocation
through the bundled renderer is the reproducible conversion path.

## Remaining human review boundaries

- All 62 package review decisions remain pending.
- Citation metadata has local matrix provenance; `citation_check=pending`, so
  no online DOI verification is claimed.
- No claim is made for measured composition, molecular-weight distribution,
  hard-segment length, common thermodynamic supercooling, intrinsic rate
  multipliers, unique hydrogen-bond species, absolute scattering, crystallinity,
  or causal uniqueness.
- Solid NMR covers only the three neat PA samples; NMR remains audit/supporting
  evidence rather than quantitative composition or phase-fraction evidence.
- Independent batch replicates and calibrated/background-corrected scattering
  are still needed before submission.

## Preserved pre-existing state

The repository's pre-existing modified/untracked files were left untouched.
The prior evidence packages and manuscript versions remain immutable. The
earlier r8 and r9 outputs remain unchanged for comparison. The r10
`docx_render` directory is the acceptance output for the current manuscript;
older `render_r8_qa*` and `render_r9_qa` directories remain local diagnostics.
