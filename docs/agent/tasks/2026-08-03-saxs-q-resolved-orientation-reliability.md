---
task_id: 2026-08-03-saxs-q-resolved-orientation-reliability
kind: scientific
status: planned
date: 2026-08-03
title: Implement q-resolved SAXS orientation reliability
---

## Goal

Implement q-resolved detector-plane orientation, neutral q-band candidates,
resampling stability, correction provenance, and non-mutating sensitivity
evidence so zero and five-percent frames can be compared over explicit q
ranges.

## Scientific boundary

Do not force zero strain or monotonic trends, infer a tensile axis, assign a
material vector, or subtract a suspected instrument harmonic.

## Non-goals

- No cross-frame feature identity or delta publication.
- No GUI, AI, calibration activation, physical feature assignment, or
  publication promotion.
- No real EDF mutation or silent use of zero strain as baseline correction.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_orientation_reliability.py`
- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_q_resolved_orientation_reliability.py`
- `tests/test_saxs_real_q_resolved_orientation.py`
- This task card.

## Implementation plan

1. Add failing synthetic contract tests and immutable DTOs.
2. Implement M2, q-bin evidence, q-band candidates, and bootstrap stability.
3. Add correction ledger and bounded sensitivity variants.
4. Attach append-only evidence to anisotropy and strain results.
5. Replay real zero/five-percent EDFs and verify all SAXS boundaries.

## Acceptance criteria

- [ ] Supported q bins expose M2, axis, support, stability, and convention.
- [ ] Q bins retain stable IDs, additive harmonic terms, and a policy digest.
- [ ] NumPy and pyFAI azimuths share the detector-image clockwise convention.
- [ ] Multiple neutral q bands are retained without replacing scalar Herman.
- [ ] Sensitivity variants are bounded, deterministic, and non-mutating.
- [ ] Every variant retains stable candidate and q-support identity.
- [ ] No calibration input or candidate mask is silently applied.
- [ ] Real zero/five-percent evidence states whether ordering is stable.
- [ ] Existing final Herman and publication gates remain fail-closed.

## Verification

```powershell
python -m pytest -p no:cacheprovider tests/test_saxs_q_resolved_orientation_reliability.py tests/test_saxs_feature_orientation_foundation.py tests/test_saxs_2d_detector_orientation_evidence.py -q
python -m pytest -p no:cacheprovider tests/test_saxs_real_q_resolved_orientation.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-08-03-saxs-q-resolved-orientation-reliability.md --changed --types
git diff --check
```

## Pre-existing workspace changes

Use the exact task allowlist. Do not touch current staged/parallel memory, GUI,
AI, data, output, or test-artifact changes.
