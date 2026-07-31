---
kind: acceptance
status: accepted-automated
date: 2026-07-31
title: SAXS strain method evidence diagnostic Figure
---

# SAXS Strain Method Evidence Diagnostic Figure Acceptance

## Scope

The strain SAXS Figure provider now projects existing per-frame Porod, Kratky,
invariant, and lamellar `MetricEvidence` into
`saxs.strain.method_evidence`. Audit sources preserve strain, frame identity,
source path, nullable value, quality level, and reason codes. Plot sources are
created only from existing finite pairs and require at least two points for the
existing V2 line-binding contract.

The Figure is always diagnostic. It does not recalculate, interpolate,
reclassify, repair, promote, or invoke AI/rescue behavior.

## Evidence

- TDD RED: `1 failed, 1 passed`; the missing Figure definition produced the
  expected `StopIteration`.
- Focused GREEN: `2 passed in 0.41s`.
- Strain/evidence regression: `50 passed in 14.20s`.
- Task verifier exited `0`; quality `297 passed`, preprocessing `106 passed`,
  and Ruff/compile/type baseline/task-memory/whitespace checks passed.
- Exact SAXS matrix exited `0`: `669 passed, 6 warnings in 532.41s`.
- Storage report exited `0` with `64` artifacts and `eligible_bytes=0` while
  pytest was active. The clean dry-run later exited `0` with `Eligible: 7873
  bytes`, `Cleanup failures: 0`, and `removed=0`. No storage apply or data
  movement occurred.

## Release boundaries

This is automated evidence projection only. Method agreement, detector
calibration, orientation meaning, AI rescue, GUI review, human scientific
review, and final publication authorization remain open gates.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_strain_method_evidence.py`
- `docs/superpowers/specs/2026-07-31-saxs-strain-method-evidence-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-strain-method-evidence.md`
- `docs/agent/tasks/2026-07-31-saxs-strain-method-evidence.md`
- `docs/acceptance/2026-07-31-saxs-strain-method-evidence.md`
