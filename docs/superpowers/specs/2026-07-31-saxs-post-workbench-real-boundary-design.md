---
title: Post-Workbench real SAXS boundary evidence refresh
date: 2026-07-31
status: approved
---

# Post-Workbench Real SAXS Boundary Evidence Refresh

## Decision

Re-run the existing PAD8 2D scientific-acceptance contract and the real SAXS
Static/Temperature/Strain lifecycle after the Workbench scientific-review
entry checkpoint. This task refreshes evidence only; it does not add a new
scientific rule or alter any result.

## Scope

- Use the existing read-only fixtures and public engine/lifecycle tests.
- Require a complete pytest summary and exit code `0` for each shard.
- Record quality, physical-gate, detector, orientation, and publication
  limitations exactly as emitted by the existing contracts.

## Safety boundaries

- No detector calibration, beam-center inference, mask interpretation,
  orientation assignment, threshold, rescue, AI call, interpolation, frame
  fabrication, or publication-role change.
- A passing test confirms software evidence transport and fail-closed
  behavior, not instrument-level scientific validity or release approval.
- No real fixture, generated output, D: test directory, or parallel memory
  file is modified. No storage `--apply` is run.
