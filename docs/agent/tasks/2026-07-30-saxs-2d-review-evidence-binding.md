---
task_id: 2026-07-30-saxs-2d-review-evidence-binding
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Bind SAXS 2D reviewer evidence to detector and orientation Figures
---

# SAXS 2D reviewer evidence binding

## Goal

Complete the reviewer-evidence transport gap for `saxs.2d` at the existing
Figure provenance boundary.

## Non-goals

- No new detector/orientation algorithm, threshold, mask, geometry inference,
  quality level, physical gate, publication decision, AI/rescue action, or
  source/frame repair.
- No GUI, Workbench, Manifest, Export, raw dataset, or storage cleanup change.
- No replacement of the existing `saxs.1d` evidence contract.

## Affected boundaries

- Shared SAXS Figure evidence projection and attachment.
- Existing static, temperature, and strain providers through that shared
  attachment boundary.
- Focused regression tests plus task/spec/plan and durable memory.

## Acceptance criteria

- [x] Matching accepted `saxs.2d` evidence is attached to detector/2D/
      orientation Figures.
- [x] Ordinary 1D Figures expect `saxs.1d`; a `saxs.2d` record is visibly
      `scope_mismatch` there and cannot be interpreted as 1D approval.
- [x] Missing, malformed, pending, wrong-scope, and partial-source records
      remain fail-closed and strict JSON-safe.
- [x] Existing 1D evidence, Figure roles, source ordering, detector/orientation
      values, physical gates, and AI/rescue behavior are unchanged.
- [x] TDD RED/GREEN, focused/SAXS/task verification, storage dry-run, diff,
      and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add shared-attachment RED tests for accepted `saxs.2d`, ordinary-1D scope
   mismatch, and partial-source fail-closed behavior.
2. Generalize the existing reviewer projection to an explicit expected scope;
   select `saxs.2d` only for existing detector/2D/orientation Figure recipes.
3. Run focused regressions, the structured verifier, the exact SAXS matrix,
   storage dry-run, and diff hygiene; then create the allowlist checkpoint.

## Verification

Verification commands:

```powershell
python -m pytest -q tests/test_saxs_2d_review_evidence_binding.py tests/test_saxs_1d_review_evidence_binding.py -o addopts= --basetemp=D:\PolyNexus_saxs_2d_review_red
python -m pytest -q tests/test_saxs_2d_review_evidence_binding.py tests/test_saxs_1d_review_evidence_binding.py tests/test_saxs_figure_evidence_binding.py -o addopts= --basetemp=D:\PolyNexus_saxs_2d_review_green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-2d-review-evidence-binding.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix is counted only from a fresh pytest summary and exit
code `0`. No `test_storage.py --apply` is authorized by this task.

## Evidence

- TDD RED was `2 failed, 7 passed`; both failures were the expected
  scope-selection gap: accepted `saxs.2d` was still judged against
  `saxs.1d`, producing `scope_mismatch`.
- GREEN plus existing 1D review and Figure evidence tests passed `38` tests in
  `8.96s`; the adjacent detector/2D/static/strain matrix passed `55 passed, 2
  warnings in 24.83s`.
- Task-scoped verifier exited `0`: quality `290`, preprocessing `106`, task /
  memory, Ruff, compile, type baseline, and whitespace checks passed.
- Fresh exact SAXS matrix exited `0`: `584 passed, 6 warnings in 421.73s`.
- `git diff --check`, targeted Ruff, and targeted compile exited `0`.
- Storage report/clean remained dry-run: `45` artifacts, `0` eligible bytes,
  `0` removed. No `test_storage.py --apply` was run.

## Current limitations

This task transports reviewer evidence only. It does not establish scientific
meaning for geometry, mask, saturation, or orientation applicability, and it
does not change publication roles or release authorization. Human scientific
and restarted-GUI review remain separate gates.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_2d_review_evidence_binding.py`
- `docs/superpowers/specs/2026-07-30-saxs-2d-review-evidence-binding-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-2d-review-evidence-binding.md`
- `docs/agent/tasks/2026-07-30-saxs-2d-review-evidence-binding.md`
- `docs/agent/memory/active-work.md`

## Known limitations

This task transports reviewer evidence only. Scientific interpretation of
geometry, mask, saturation, orientation applicability, restarted-GUI review,
and final publication authorization remain separate human gates.
