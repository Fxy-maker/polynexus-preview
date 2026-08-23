---
task_id: 2026-08-23-six-sample-paper-replay
kind: scientific
status: active
date: 2026-08-23
title: Six-sample paper evidence replay and direct-AI comparison
---

# Six-sample paper evidence replay and direct-AI comparison

## Goal

Create one new, reproducible, source-hashed PolyNexus evidence replay for
PA6, PA6-50, PA11, PA11-50, PA12, and PA12-50; then compare its auditable
evidence boundaries with the existing direct-AI manuscript without using that
manuscript or any prior package as an analysis input.

## Confirmed scientific context (2026-08-23)

- `PAx-50` denotes 50% soft-segment content.
- `JW` and `SW` denote cooling and heating FTIR series, respectively.
- The `for N min` groups are isothermal holds at the preceding filename
  temperature.
- The requested narrative tests, rather than assumes, this chain: hard-segment
  sequence geometry and hydrogen-bond aggregation are modified by soft-segment
  effects on hard-segment continuity, amorphous relaxation, and phase-interface
  constraint; the measurable response is the competition among ordering drive,
  segmental mobility, and interfacial constraint.
- The direct-AI comparator is the v47 manuscript named in Task 5. It remains
  read-only and strictly post-package.

## Non-goals

- Do not modify the source directory or reuse its existing analysis outputs,
  packages, manuscript figures, or numerical results.
- Do not generate or revise a final paper.
- Do not treat user-confirmed meanings of `-50`, `JW`, `SW`, and isothermal
  holds as independently measured instrument metadata.
- Do not promote single-file SAXS/WAXS observations to replicated statistics.

## Shared objects and entry points

- Objects: new project, source snapshot, deterministic runs, figures, evidence
  package, figure index, citation metrics, ARS writing input, PaperBrief, and
  ManuscriptPlan.
- AI/Codex/CLI: creates and validates the new project through the public
  project-workflow contracts and reads the immutable package for planning.
- GUI: unchanged; it remains a consumer of the same project/run/evidence
  DTOs and receives no private analysis representation.
- Cross-entry rule: every output is written only below the new project root;
  the source snapshot and all package artifacts retain source hashes.

## Affected boundaries

- Producer: the existing `ProjectWorkflowService` and registered DSC/IR/SAXS/
  WAXS deterministic routes create the new project-local run manifests and
  immutable evidence package.
- Consumers: the CLI and ARS/ManuscriptPlan read the same immutable package;
  no GUI or source-contract implementation changes occur.
- Scientific boundary: blocked DSC routes, FTIR template/material assignment,
  and single-file scattering limits are recorded as review limits, never
  rewritten as paper conclusions.

## Context and output budget

- Read first: project-workflow, package, ARS, and ManuscriptPlan contracts;
  source data only in the six selected technique directories.
- Search scope: the new project root and the selected manuscript comparator.
- Expand only for scientific-review warnings, reader/provider failures, or
  comparison evidence that cannot be tied to a cited source location.
- Report only final package paths, exact commands/results, review limits, and
  untouched pre-existing workspace changes.

## Acceptance criteria

- [x] A fresh project at `D:\PA6-paper-replay-20260823` contains a frozen,
  hashed source snapshot for the six selected samples and no old package is
  used as a result.
- [x] DSC, FTIR CSV, SAXS, and WAXS deterministic runs are recorded through
  the shared project/run contracts; blocked or review-bound inputs remain so.
- [x] A new evidence package includes `figure-index.json`,
  `citation-metrics.json`, and `ars-writing-input.json`.
- [x] A PaperBrief-derived ManuscriptPlan references only the new immutable
  package and does not draft a manuscript.
- [x] The direct-AI manuscript comparison is retrospective and source-cited;
  it cannot modify or supply values to the replay.
- [x] The final report separates Results candidates, Discussion-only evidence,
  figure roles, human-review items, and the comparison findings.

## Implementation plan

1. Freeze the approved six-sample raw inputs into a new external project and
   verify each copied source hash.
2. Run the supported project-workflow routes and retain blocked results as
   explicit manifests rather than substituting older analyses.
3. Package only the new review-bound runs; validate evidence, figure, metric,
   and ARS writing artifacts.
4. Generate a package-pinned PaperBrief and ManuscriptPlan without drafting a
   manuscript or promoting any figure automatically.
5. Hash and inspect the direct-AI manuscript only after package freeze, then
   record a retrospective claim-boundary comparison and evidence review.
6. Run focused regression and structured documentation verification, then
   create the allowlisted local checkpoint.

## Verification

```powershell
python -m pytest -p no:cacheprovider -q tests/test_project_workflow*.py tests/test_ars*.py tests/test_manuscript_plan.py
python scripts/verify.py --task docs/agent/tasks/2026-08-23-six-sample-paper-replay.md --changed --types
git diff --check
```

## Checkpoint allowlist

```powershell
python scripts/auto_commit.py `
  --message "docs(replay): record six-sample evidence replay" `
  --files docs/agent/tasks/2026-08-23-six-sample-paper-replay.md docs/superpowers/plans/2026-08-23-six-sample-paper-replay.md
```

## Completion evidence

- Exact commands and outcomes: 270 raw files were hash-verified; 42 runs were
  scheduled; 33 review-required runs were packaged at
  `D:\PA6-paper-replay-20260823\.polynexus\evidence\six-sample-paper-replay-v001`
  (package hash `8a465b1c468155fa459f8ecb4f608e1706ebf7925bcd50b04f65e8b64ee31327`).
  `python -m pytest -p no:cacheprovider -q ...` passed `102 passed, 1 skipped`.
  `python scripts/verify.py --task ... --changed --types` passed, including
  quality `304 passed` and preprocessing `157 passed`; `git diff --check` passed.
- Known limitations or follow-up: all six thermal-cycle DSC inputs plus three
  isothermal DSC inputs are blocked by the registered DSC route; FTIR material
  assignment/mapping is not reliable for PA11/PA12; SAXS/WAXS remain single-file
  diagnostic structural context. The direct-AI v47 comparison is frozen at
  SHA-256 `1d42a6a1e0233412561884d34f8f5cade66e563c5b9c64b0a055eb284b02c97f`.
- Pre-existing changes left untouched: `.superpowers/`, the 2026-08-21 task and
  plan, `ftir_group_overlay_review.png`, `tests/_tmp_phase3/`, and
  `tests/test_evidence_review_loop.py`.
