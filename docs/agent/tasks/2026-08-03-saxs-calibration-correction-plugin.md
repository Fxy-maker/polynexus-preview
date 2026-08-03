---
task_id: 2026-08-03-saxs-calibration-correction-plugin
kind: scientific
status: planned
date: 2026-08-03
title: Add a fail-closed SAXS detector correction plugin
---

## Goal

Implement disabled, candidate, and reviewed two-dimensional detector
correction contracts with provenance and double-correction guards.

## Scientific boundary

Synthetic tests prove software behavior only. Without reviewed calibration EDF
inputs, real correction remains unavailable and baseline pixels remain
authoritative.

## Non-goals

- No production dark/flat/background/polarization/solid-angle equation is
  activated before its formula and ownership receive scientific review.
- No zero-strain subtraction, automatic review approval, or calibration-file
  discovery.
- No GUI workflow, real-data validity claim, or publication promotion.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_detector_correction.py`
- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/io.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_detector_corrections.py`
- `tests/test_saxs_detector_correction_integration.py`
- `tests/test_saxs_edf_metadata_quality.py`
- This task card.

## Implementation plan

1. Add failing disabled, order, provenance, and mismatch tests.
2. Implement immutable correction requests, results, ledger, and a plugin
   protocol with no production numerical backend registered.
3. Add strict EDF/config compatibility and double-correction guards.
4. Integrate identity/candidate/rejected transport before chi-by-q integration;
   use a test-only synthetic backend to prove transaction ordering.
5. Verify production remains identity-preserving and record numerical equations
   plus real-data validation as open stop gates.

## Acceptance criteria

- [ ] Disabled mode preserves image and mask identity.
- [ ] Candidate/rejected corrections cannot feed final orientation.
- [ ] A test-only synthetic backend proves transaction ordering exactly once.
- [ ] Shape, detector, exposure, geometry, and provenance mismatches fail closed.
- [ ] Production reviewed mode remains unavailable without a registered,
  scientifically reviewed backend.
- [ ] Real calibration validity remains open without calibration EDF evidence.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_detector_corrections.py tests/test_saxs_detector_correction_integration.py tests/test_saxs_edf_metadata_quality.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-calibration-correction-plugin.md --changed --types
git diff --check
```

## Pre-existing workspace changes

Do not add calibration files, edit real EDF data, or touch unrelated staged,
GUI, AI, memory, output, or artifact changes.
