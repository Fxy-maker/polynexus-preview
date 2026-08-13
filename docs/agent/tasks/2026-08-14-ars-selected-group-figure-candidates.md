---
task_id: 2026-08-14-ars-selected-group-figure-candidates
kind: architecture
status: planned
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

- [ ] An ARS request selects one or two inventory candidate group IDs.
- [ ] Invalid, stale, mixed-technique, or incompatible group selections block
  before provider execution.
- [ ] Only selected FTIR group artifacts are analyzed.
- [ ] A valid selected FTIR group with two spectra produces an overlay figure.
- [ ] A trend figure appears only for a shared finite provider metric and a
  valid group condition axis.
- [ ] The public result has no more than two `main_candidate` figures.
- [ ] Single-file provider outputs remain internal evidence with provenance.
- [ ] Candidate metadata is copied into the evidence package.

## Implementation plan

1. Add JSON-safe ARS figure-selection and candidate-figure contracts.
2. Render selected FTIR group overlays and strictly gated metric trends.
3. Integrate selection, manifests, evidence packaging, and CLI JSON input.
4. Verify synthetic and bounded read-only PA6 cases, record acceptance, and
   checkpoint the allowlisted task files.

## Verification

- `python -m pytest tests/test_ars_group_figure_candidates.py tests/test_ai_project_candidate_groups.py tests/test_ai_native_project_entrypoint.py -q`
- `python scripts/verify.py --task docs/agent/tasks/2026-08-14-ars-selected-group-figure-candidates.md --changed --types`
- `git diff --check`
