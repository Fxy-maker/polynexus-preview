---
task_id: 2026-08-30-elastomer-all-data-paper
kind: scientific
status: completed_review_required
date: 2026-08-30
title: Build an all-technique elastomer evidence package and paper draft
---

# All-Technique Elastomer Evidence and Paper Draft

## Goal

Use every relevant, traceable dataset in
`C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文` to build one current
DSC/IR/NMR/WAXS/SAXS evidence version and a Chinese manuscript draft about why
the even-nylon hard-segment elastomers show faster crystallization in the
current paired samples.

## Non-goals

- Do not overwrite raw data, `elastomer-ir-nmr-article-v001`,
  `elastomer-ir-nmr-article-v002`, or an existing manuscript.
- Do not treat all raw files as equally publication-ready or place every
  diagnostic figure in the main text.
- Do not infer composition, molecular weight, hard-segment length, calibration,
  hydrogen-bond populations, absolute crystallinity, or causality that the
  data do not directly establish.
- Do not change Core algorithms or scientific thresholds during this task.

## Shared objects and entry points

- Objects: project inventory, canonical experiment, `ComputeRun`, working
  evidence index, immutable evidence package, figure index, review ledger,
  manuscript source, and document export.
- Producers: existing project-workflow and Suite services only; prior analysis
  CSVs and manuscript drafts are comparison/context inputs, not alternate run
  contracts.
- Consumers: CLI/Codex, evidence-package view, ARS writing handoff, and the
  generated Markdown/DOCX/PDF draft.

## Affected boundaries

- External project derived data under `.polynexus/`.
- New versioned manuscript output under the external project's `manuscript/`
  directory.
- Repository task/spec/plan/memory/acceptance notes only; no provider source
  code is expected to change.

## Acceptance criteria

- [x] The raw-data audit maps the six paired samples across isothermal and
      non-isothermal DSC, temperature IR/2D-COS, solution/solid NMR, WAXS, and
      SAXS, with duplicates and missing modes recorded.
- [x] Each newly used source is represented by a validated persisted run or is
      explicitly excluded with a reason.
- [x] A new immutable package loads through `EvidencePackageView`, exposes all
      techniques that completed, and preserves package-relative run/figure
      references.
- [x] The claim-evidence matrix separates observations, comparisons,
      interpretations, alternative explanations, and unsupported claims.
- [x] The manuscript uses DSC as the direct rate evidence and IR/NMR/WAXS/SAXS
      as bounded mechanistic or structural evidence.
- [ ] Literature records contain independently online-verified bibliographic
      identifiers; local DOI/title/year metadata is retained, but online
      verification is still a required human action.
- [x] Markdown and DOCX outputs are new versions and pass structural/numerical
      checks; PDF rendering is visually checked when the runtime supports it.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_evidence_workspace.py tests/test_evidence_package_view.py tests/test_paper_pipeline.py
python -m pytest -p no:cacheprovider -q tests/test_all_data_manuscript_builder.py
python scripts/verify.py --task docs/agent/tasks/2026-08-30-elastomer-all-data-paper.md --changed --types
git diff --check
```

External-artifact verification additionally validates the new package view,
source hashes, run counts by technique, claim-to-source links, document
structure, and rendered-page integrity.

## Implementation plan

1. Audit the frozen all-technique evidence package, raw-source inventory, sample
   pairs, and approved derived tables; record duplicates, unsupported formats,
   review status, and DSC candidate discrepancies.
2. Generate a versioned data-audit ledger, claim-evidence-literature matrix,
   figure/table index, and supplementary-material index from those sources.
3. Draft `even-nylon-crystallization-v002` with DSC as the direct kinetic
   evidence and IR, NMR, WAXS, and SAXS assigned bounded supporting roles.
4. Export Markdown, JSON metadata, and editable DOCX; run structural checks and
   render the DOCX when the local Office/PDF runtime is available.
5. Run the focused repository tests, task-scoped verifier, and whitespace/diff
   checks; update memory and acceptance notes and create one explicit checkpoint.

## Completion evidence

- Exact commands and outcomes: see
  `docs/acceptance/2026-08-31-elastomer-all-data-paper.md`. The focused
  package/evidence/paper tests and task-scoped verifier are recorded there;
  the external artifact audit and DOCX visual QA are also recorded there.
- Evidence package and manuscript paths:
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\.polynexus\evidence\elastomer-all-data-paper-v001`
  and
  `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\manuscript\even-nylon-crystallization-v002-r10`.
- The ARS/Suite handoff command
  `python -m polynexus suite handoff --package <package>` returned
  `status=ready`, all five technique views, 7,619 metrics, and 62 pending
  human-review decisions. It points to package-relative
  `ars-writing-input.json`, `result-tables.json`, `writing-evidence.json`,
  `citation-metrics.json`, and `review-decision.json`.
- The r10 preflight records 11,533 Chinese body characters (11,537 total),
  `pass_with_human_review`, and a 21-page DOCX/PDF render with no observed
  layout defects.
- Scientific limitations and follow-up: package status remains
  `review_required`; all 62 human evidence decisions are pending; DOI/title
  metadata has local provenance but no online verification claim; composition,
  molecular-weight distribution, common thermodynamic supercooling, calibrated
  scattering, and independent batch replicates remain open.
- Pre-existing workspace changes left untouched: all unrelated modified and
  untracked repository files (including `active_run.json`, `runs/`, and
  `tests/_tmp_phase3/`) were preserved. The old evidence packages and
  manuscripts were not overwritten.
