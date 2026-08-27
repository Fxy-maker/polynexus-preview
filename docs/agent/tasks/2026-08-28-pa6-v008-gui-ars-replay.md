---
task_id: 2026-08-28-pa6-v008-gui-ars-replay
kind: integration
status: implementation_complete_review_required
date: 2026-08-28
title: Replay six-sample project through GUI and ARS package
---

# Replay six-sample project through GUI and ARS package

## Goal

Validate the updated shared route, capability projection, review ledger, and
GUI evidence gallery against the real six-sample project.

## Non-goals

- Do not edit raw inputs or relax provider quality gates.
- Do not decide manuscript Results/Discussion promotion automatically.

## Affected boundaries

- External replay project and its derived `.polynexus` directory.
- Evidence package, `EvidencePackageView`, and `EvidencePackageDialog` readback.

## Implementation plan

1. Run the approved six-sample replay script.
2. Package successful/review-required manifests into a new evidence snapshot.
3. Load the package twice through the GUI dialog and exercise a technique
   filter.
4. Record counts, failure boundaries, and raw-hash invariants.

## Acceptance criteria

- [x] 42 runs are accounted for without raw-data changes.
- [x] New package includes capability provenance and review-decision ledger.
- [x] GUI reload produces identical figure entries and filtering works.
- [x] Scientific and release limitations remain explicit.

## Verification

Recorded in `docs/acceptance/2026-08-28-pa6-v008-gui-ars-replay.md`.
