---
task_id: 2026-08-14-ars-selected-group-figure-candidates
kind: architecture
status: implementation_complete_review_required
date: 2026-08-14
title: Generate ARS-selected FTIR group figure candidates
---

# ARS-Selected Group Figure Candidates

## Goal

Let ARS select one or two FTIR candidate experiment groups before analysis,
then return at most two manuscript figure candidates with complete evidence
provenance.

## Non-goals

- Do not infer sample, batch, formulation, or publication acceptance.
- Do not change existing scientific numerical algorithms.
- Do not create DSC, SAXS, WAXS, or NMR group plotting in this task.
- Do not publish every single-file provider figure as a manuscript candidate.

## Affected boundaries

- Project workflow selection request and AI-facing summary.
- FTIR group-overlay and conservative metric-trend renderers.
- Project-local figure manifest and evidence package projection.
- CLI JSON request handling, tests, acceptance, and durable memory.

## Acceptance criteria

- [x] An ARS request selects one or two inventory candidate group IDs; the
  two-group comparison intent is accepted as a contract but fails closed before
  provider execution until a comparison renderer is implemented.
- [x] Invalid, stale, mixed-technique, or incompatible group selections block
  before provider execution.
- [x] Only selected FTIR group artifacts are analyzed.
- [x] A valid selected FTIR group with two spectra produces an overlay figure.
- [x] A trend figure appears only for a shared finite provider metric and a
  valid group condition axis.
- [x] The public result has no more than two `main_candidate` figures.
- [x] Single-file provider outputs remain internal evidence with provenance.
- [x] Candidate metadata is copied into the evidence package.

The first vertical slice implements one-group FTIR overlay/trend candidates.
`compare_groups` remains an explicit, provider-free omission with reason code
`group_comparison_not_implemented`; it is reserved for the next figure slice.

## Implementation plan

1. [x] Add JSON-safe ARS figure-selection and candidate-figure contracts.
2. [x] Render selected FTIR group overlays and strictly gated metric trends.
3. [x] Integrate selection, manifests, evidence packaging, and CLI JSON input.
4. [x] Verify synthetic and bounded read-only PA6 cases, record acceptance, and
   checkpoint the allowlisted task files.

## Verification

- `python -m pytest tests/test_ars_group_figure_candidates.py tests/test_ai_project_candidate_groups.py tests/test_ai_native_project_entrypoint.py -q`
- `python scripts/verify.py --task docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md --changed --types`
- `git diff --check`
