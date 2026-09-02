# First AI-Native Mixed-Technique Research Loop

Date: 2026-09-02
Status: implementation complete, review required

## Scope

The read-only replay used the explicit AI/Codex-selected paths below from
`D:\PolyNexus-pa6-loop-20260902-clean`:

- `raw/dsc/PA6-DWJJ.txt`
- `raw/ftir/PA6-JW-180.csv`
- `raw/saxs/PA6.edf`
- `raw/waxs/PA6.raw`

No NMR file was selected or present in this project. The workflow reports NMR
as missing rather than inventing an empty result.

## Entry point and result

Command:

```powershell
python -m polynexus project-workflow close-loop `
  --project-root D:\PolyNexus-pa6-loop-20260902-clean `
  --paths raw/dsc/PA6-DWJJ.txt raw/ftir/PA6-JW-180.csv raw/saxs/PA6.edf raw/waxs/PA6.raw `
  --question "Compare thermal and structural response of PA6" `
  --package-id pa6-first-ai-loop-v001
```

The command exited `0` and returned `status: completed` with one shared run:
`run-ceaa4a34f7eb5eab5265b9aa`. Each selected technique produced a finite
deterministic result and was retained as `review_required` evidence. The
evidence package remains `review_required` because scientific promotion and
interpretation are human/ARS decisions.

## Outputs

Evidence package:

`D:\PolyNexus-pa6-loop-20260902-clean\.polynexus\evidence\pa6-first-ai-loop-v001-v001`

- `manifest.json`: one run, four evidence items, nine SVG figures, four
  technique result tables, and source/template/conversion hashes.
- `figure-index.json`: nine package-relative SVG references.
- `result-tables.json`: DSC, IR, SAXS, and WAXS condition-scoped tables with
  source rows and deterministic statistics.
- `ars-writing-input.json`, `writing-input.md`, `writing-evidence.json`, and
  `review-decision.json`.
- SAXS contains 230 computed metric rows and 24 explicit `unavailable` rows;
  null metrics no longer cause provider-result construction to fail.

Manuscript exports:

`D:\PolyNexus-pa6-loop-20260902-clean\.polynexus\research\manuscripts\pa6-first-ai-loop-v001`

- `manuscript.json`
- `manuscript.md`
- `manuscript.pdf`
- `manuscript.docx`

The close-loop summary also contains the structural preflight DTO. The draft
is an evidence projection and does not recalculate raw data or fabricate
claims; its claims retain metric, figure, table, and evidence identifiers.

## Source integrity

SHA-256 values before and after replay were identical:

| Source | SHA-256 |
| --- | --- |
| `raw/dsc/PA6-DWJJ.txt` | `789531d03ee8d0da9652c7e0734e8fc40e907f282bd7771990e6948a59dd9db7` |
| `raw/ftir/PA6-JW-180.csv` | `a0d31d754342a491c7b9588c042e3d19eab26e52aea99a672c6c454c408cf562` |
| `raw/saxs/PA6.edf` | `3ad3b04feeae716902e5d5584336e7293b9dc10a7d2299292ce1c6908c2def40` |
| `raw/waxs/PA6.raw` | `6041e4fca7e28543581b27fa2be2364eff8c0c1f297daac0c3eeecc2016245eb` |

No repository fixture or real raw file was modified.

## Verification

- `python -m pytest -p no:cacheprovider -q tests/test_result_field_inventory.py tests/test_ai_platform_scientific_contracts.py tests/test_compute_service.py tests/test_project_workflow_cli.py tests/test_ai_native_project_entrypoint.py tests/test_first_ai_research_loop.py`
  -> `95 passed, 3 skipped`.
- `python -m pytest -p no:cacheprovider -q tests/test_project_workflow_package.py tests/test_project_writing_metrics.py tests/test_paper_source.py tests/test_paper_pipeline.py tests/test_paper_bundle.py tests/test_evidence_package_view.py tests/test_compute_run_projection.py tests/test_ai_platform_cross_entry.py`
  -> `110 passed`.
- The real close-loop command above -> exit `0`, four techniques completed,
  package and manuscript exports present.
- `python scripts/verify.py --task ... --changed --types` -> selected checks
  passed (`313` quality, `157` preprocessing, Ruff, compile, and memory
  checks).
- `python scripts/verify.py --changed --types --full --boundary` reached the
  full suite and reported `4752 passed, 38 failed, 25 skipped`; these are
  pre-existing GUI/figure, SAXS historical-boundary, IR bridge, and legacy
  TPAE failures outside this task. They prevent a release-green claim.
- `git diff --check` passed.

## Review boundary and follow-up

The package is not publication-ready. Human/ARS review is still required for
figure selection, metric eligibility, method interpretation, citations, and
cross-technique scientific claims. Open-source preparation is a separate next
task and is intentionally outside this acceptance record.
