# Project Technique Series V3 Acceptance

Date: 2026-08-13

V3 adds `project.technique.series.v1` for same-technique multi-file inputs.
Paths are ordered deterministically, each provider step records an
`artifact_index`, and source hashes are checked before execution. Mixed
techniques and one-file series requests remain blocked.

## Real PA6 read-only replay

- External source: `C:\Users\Fan Xuyi\Desktop\文件夹\弹性体\弹性体中文\insu-FTIR\PA6`.
- Project raw path is a junction; no raw bytes were copied or modified.
- Inputs: `PA6-JW-100.csv`, `PA6-JW-110.csv`, `PA6-JW-120.csv`.
- Project workspace: `D:\PolyNexus-pa6-v3-ftir-series-20260812`.
- Plan: `ready`; run: `review_required`; package: `review_required`.
- Evidence package: `.polynexus/evidence/pa6-ftir-series-v001`.
- Three IR provider steps completed; provider-reported Xc values remain
  review-bound evidence, not manuscript conclusions.

## Relations boundary

Packages now include an explicit `run_part_of_request` relation for each run
when callers do not supply relations. This identifies workflow membership only;
sample, batch, formulation, and cross-technique identity remain unknown unless
Codex/ARS supplies explicit context.

## Verification

- Focused project matrix: `24 passed`.
- Real PA6 series smoke: three IR steps, `review_required` run/package.
- Structured verifier is required before checkpoint.
