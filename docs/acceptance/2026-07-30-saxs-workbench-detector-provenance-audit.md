---
kind: acceptance
status: accepted
date: 2026-07-30
title: SAXS Workbench detector provenance audit visibility
task: docs/agent/tasks/2026-07-30-saxs-workbench-detector-provenance-audit.md
---

# Acceptance Record

## Delivered

- Workbench presentation reads only the existing
  `scientific_acceptance_audit.detector_provenance_audit` payload.
- Valid records display status, level, geometry validity, mask validity, and
  at most five string reason codes.
- `review_required` and `unusable` records enter risk; every valid record,
  including `structurally_consistent`, appears as advisory next evidence.
- Next evidence states that structural provenance does not establish detector
  calibration or physical acceptance.
- Malformed or absent payloads are ignored, generic metric review remains
  separate, and the input mapping is not mutated.

## Verification Evidence

- RED returned `4 failed, 1 passed` before implementation.
- GREEN focused test run returned `5 passed`.
- Consumer matrix returned `26 passed`.
- `python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-workbench-detector-provenance-audit.md --changed --types` returned exit code `0`; quality gate `290 passed`, preprocessing gate `106 passed`, Ruff, compile, type baseline, memory, task, and whitespace checks passed.
- `git diff --check` passed as part of the verifier sequence.

## Boundaries and Limitations

This is presentation-only. It does not validate detector calibration, infer
mask or geometry quality, alter physical thresholds, change AI/rescue policy,
or change Figure/Manifest/Export publication behavior. Fresh full/boundary
verification after this change is not claimed; the known prior full/boundary
timeout remains a separate limitation.
