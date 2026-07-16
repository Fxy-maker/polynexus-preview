# SAXS closed-loop mainline migration

## Goal

Rebuild the SAXS closed-loop reliability and export slices on top of the
current `origin/main` without importing the divergent WAXS/DSC/editor branch.

## Scope

- Explicit SAXS panel/config binding and diagnostics.
- Canonical processed-profile and sequence-QA projections.
- Stable SAXS result/evidence contract.
- Unified static/temperature/strain export bundle.
- Focused GUI/engine wiring required by those contracts.

## Non-goals

- No reactive editor migration; that is already on mainline.
- No WAXS/DSC refactors or broad GUI cleanup.
- No scientific threshold changes without a separate decision and regression.

## Migration order

1. Configuration adapter and panel wiring.
2. Canonical processed profile and sequence QA.
3. Result/evidence contract.
4. Export bundle and compatibility writers.
5. GUI review/export payload wiring.

## Acceptance

- Each slice has focused regression tests and an atomic commit.
- Static, temperature, and strain SAXS paths preserve existing behavior.
- Export and review consumers read stable payloads rather than private engine
  state.
- The branch can be rebased or merged into `origin/main` without unrelated
  subsystem conflicts.

## Current baseline

- Base: `origin/main` at `9712e3ca`.
- The previous runtime-unified branch is intentionally not merged: it contains
  162 commits not in main and overlapping GUI/figure/table implementations.
- Prior local SAXS cards were not present in any remote commit and are being
  reconstructed here with tests first.

## Progress

- [x] Configuration adapter and panel wiring (`75a2e4c`).
- [x] Canonical processed profiles and sequence QA.
- [x] Result/evidence contract with defensive write diagnostics.
- [x] Static/temperature/strain export bundle and legacy export compatibility.
- [x] GUI total-export hook for the SAXS bundle.
- [ ] Final full-suite verification and push of the dedicated branch.
