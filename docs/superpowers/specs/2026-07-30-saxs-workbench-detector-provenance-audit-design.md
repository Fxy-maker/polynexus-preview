---
title: SAXS Workbench detector provenance audit visibility
date: 2026-07-30
status: implemented
---

# SAXS Workbench Detector Provenance Audit Visibility

## Goal

Make the existing raw-detector provenance structural audit visible in SAXS
Workbench review text so a user can see geometry/mask status and reasons.

## Scope

The presentation layer reads only the detached
`scientific_acceptance_audit.detector_provenance_audit` payload. It displays
the audit status, level, geometry validity, mask validity, and bounded reason
codes. Review-required and unusable records appear in the risk channel; all
records add a next-step advisory that structural evidence is not calibration
or physical acceptance.

Malformed or absent audit payloads remain invisible, preserving the existing
presentation behavior. The input mapping is never mutated, 1D metric text is
not changed, and no Figure, Manifest, Export, algorithm, threshold, rescue,
or publication decision is recalculated.

## Non-goals

- No detector calibration, mask validation, beam-center inference, or
  orientation interpretation.
- No new quality level or publication gate.
- No raw array display or new GUI algorithm state.

## Verification

Focused tests cover review-required and structurally-consistent records,
malformed input, strict separation from generic 1D metric text, and input
immutability. The existing SAXS Workbench and full SAXS matrices remain
required.
