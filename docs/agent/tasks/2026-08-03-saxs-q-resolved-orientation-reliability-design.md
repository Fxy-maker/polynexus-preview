---
task_id: 2026-08-03-saxs-q-resolved-orientation-reliability-design
kind: scientific
status: design_review
date: 2026-08-03
title: Design q-resolved SAXS orientation reliability without calibration data
---

## Goal

Define the first atomic scientific milestone for q-resolved SAXS orientation
and non-destructive artifact-sensitivity analysis when no independent detector
calibration frames are available.

## Scientific Boundary

The design must preserve genuine zero-strain orientation, keep the existing
detector-plane Herman convention explicit, and prohibit zero-strain or
suspected systematic-harmonic subtraction. Automatic behavior is limited to
q-resolved diagnostics, existing hard-invalid pixel handling, and bounded
sensitivity variants.

## Non-goals

- Do not implement the scientific core in this design checkpoint.
- Do not change GUI, AI, export, database, or publication behavior.
- Do not alter real EDF files, existing scalar orientation fields, or parallel
  workspace changes.
- Do not write the implementation plan before written-spec review.

## Affected boundaries

- `docs/superpowers/specs/2026-08-03-saxs-q-resolved-orientation-reliability-design.md`
- This design task card.

## Implementation plan

1. Record the approved no-calibration scientific boundary and considered
   alternatives.
2. Define the q-resolved harmonic, correction-ledger, sensitivity, reliability,
   transport, failure, and test contracts for the first atomic milestone.
3. Self-review the written specification and verify the explicit two-file
   design allowlist without touching parallel workspace changes.

## Acceptance criteria

- [x] The root cause and no-calibration identifiability limit are explicit.
- [x] The design defines M2 mathematics, detector-plane Herman semantics,
  correction provenance, q-band candidates, resampling stability, bounded
  sensitivity variants, reliability states, and failure behavior.
- [x] Zero-strain is a future paired delta reference, not an instrument blank.
- [x] The first implementation milestone is core-only and separated from
  tracking, GUI, calibration, and AI phases.
- [x] Synthetic and read-only real-EDF acceptance requirements are concrete.
- [x] The spec contains no unresolved placeholders or conflicting semantics.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability-design.md --changed --types
git diff --check -- docs/superpowers/specs/2026-08-03-saxs-q-resolved-orientation-reliability-design.md docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability-design.md
rg -n "T[B]D|T[O]DO|F[I]XME|P[L]ACEHOLDER" docs/superpowers/specs/2026-08-03-saxs-q-resolved-orientation-reliability-design.md docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability-design.md
```

## Explicit Changed-file Allowlist

- `docs/superpowers/specs/2026-08-03-saxs-q-resolved-orientation-reliability-design.md`
- `docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability-design.md`

## Pre-existing Workspace Changes

The existing staged, modified, deleted, and untracked files belong to user or
parallel work. They are excluded from this design checkpoint and must not be
unstaged, overwritten, cleaned, or committed with this task.
