---
task_id: 2026-08-03-saxs-orientation-feature-tracking
kind: scientific
status: implemented_pending_real_replay
date: 2026-08-03
title: Track same SAXS orientation features across strain
---

## Goal

Build fail-closed cross-strain q-band identity and same-feature delta evidence
from Task 1 frame records.

## Scientific boundary

Do not choose ambiguous matches, fabricate zero strain, bridge feature
switches, promote local evidence, or assign material-vector semantics.

## Non-goals

- No detector reintegration, mask change, tensile-axis inference, or
  calibration subtraction.
- No singular primary-track selection when multiple tracks exist.
- No GUI, AI, physical assignment, monotonicity rule, or publication promotion.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_orientation_tracking.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/core/saxs.py`
- `polynexus/core/saxs_batch_helpers.py`
- `tests/test_saxs_orientation_feature_tracking.py`
- `tests/test_saxs_orientation_tracking_transport.py`
- `tests/test_saxs_real_orientation_tracking.py`
- This task card.

## Implementation plan

1. Add failing unique, ambiguous, split, gap, and zero-reference tests.
2. Implement immutable track and sequence evidence contracts.
3. Reaggregate exact common q support and implement mutual-unique matching plus
   conservative delta stability bounds.
4. Attach sequence evidence without redefining frame evidence.
5. Replay the real strain series and verify full SAXS boundaries.

## Acceptance criteria

- [x] Only mutually unique compatible q bands share a track ID.
- [x] Ambiguity, gaps, and feature switching split tracks explicitly.
- [x] Delta requires a unique zero frame and common reference semantics.
- [x] Delta uses the exact common q-bin set, additive terms, and policy digest.
- [x] All tracks are transported without selecting a primary track.
- [x] Suspected systematic harmonic remains diagnostic and unsubtracted.
- [x] Transport is strict-JSON-safe and backward compatible.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_orientation_feature_tracking.py tests/test_saxs_orientation_tracking_transport.py -q
python -m pytest -p no:cacheprovider tests/test_saxs_real_orientation_tracking.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-orientation-feature-tracking.md --changed --types
git diff --check
```

## Pre-existing workspace changes

Do not modify Task 1 semantics or unrelated staged, GUI, AI, calibration,
memory, data, output, or artifact files.

## Current Evidence

- Tracking, transport, batch, and strain focused slice: `65 passed`.
- Real-series acceptance: `1 skipped` because `POLYNEXUS_SAXS_REAL_ROOT` is not
  configured; no source frame is substituted for missing real evidence.
- Invalid and duplicate source-index mappings fail closed with explicit reason
  codes; list position is never used as provenance.
- Full SAXS matrix and task verifier are run after this checkpoint review.
