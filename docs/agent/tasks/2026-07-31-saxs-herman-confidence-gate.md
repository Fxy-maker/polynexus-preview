---
task_id: 2026-07-31-saxs-herman-confidence-gate
kind: scientific
status: completed
date: 2026-07-31
title: Gate unreliable SAXS Herman orientation values
---

# SAXS Herman Confidence Gate

## Goal

Stop blocked or statistically weak 2D SAXS profiles from publishing a numeric
Herman factor in the strain table, while retaining the raw value for diagnosis.

## Non-goals

- Do not force zero-strain orientation to zero.
- Do not change the 2D Herman convention, q* selection, detector calibration,
  GUI event handlers, or AI tuning behavior.
- Do not touch parallel AI advisor/memory changes, real EDF data, or generated
  test artifacts.

## Affected boundaries

- `polynexus/core/saxs_engine/config.py`: confidence-gate thresholds.
- `polynexus/core/saxs_engine/saxs_anisotropy.py`: azimuthal diagnostics,
  raw/effective Herman separation, and evidence fields.
- `polynexus/core/saxs_engine/saxs_strain.py`: apply aligned 1D hard quality
  blockers and transport raw/effective values.
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: preserve raw metric
  evidence and expose gate status/reasons in the existing orientation contract.
- Focused SAXS orientation and strain tests.

## Implementation plan

1. Add explicit orientation reliability thresholds and preserve raw versus
   effective Herman values in the anisotropy and evidence contracts.
2. Add azimuthal coverage, effective-bin, harmonic-significance, and split-axis
   stability diagnostics with fail-closed reason codes.
3. Apply aligned 1D hard quality blockers during strain transport while keeping
   raw Herman evidence available for diagnosis.
4. Run focused and complete SAXS regression matrices, then run the structured
   verifier and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Strong synthetic anisotropy remains finite and JSON-safe.
- [x] Weak/noisy, incomplete, or unstable profiles return an unavailable
  effective Herman factor with explicit reason codes.
- [x] 1D quality actions `invalid_pairs_dropped`, `low_q_truncated`, and hard
  nonfinite/nonpositive q/I reasons block the effective strain value.
- [x] Raw Herman values remain available in orientation evidence and are not
  shown as the effective table value.
- [x] Existing SAXS tests pass, and no parallel tracked/untracked changes are
  included in the checkpoint.

## Verification

The test root was directed to `C:\\PolyNexus-test-runs` with `review` retention
to avoid writing evidence into the nearly full D: volume.

```powershell
$env:POLYNEXUS_TEST_ROOT='C:\\PolyNexus-test-runs'
$env:POLYNEXUS_TEST_RETENTION='review'
python -m pytest -p no:cacheprovider tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_batch_parameters.py -q
python -m pytest -p no:cacheprovider (Get-ChildItem tests/test_saxs_*.py | ForEach-Object { $_.FullName }) -q
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-herman-confidence-gate.md --changed --types
git diff --check
```

Observed results:

- Focused matrix: `57 passed in 0.43s`, exit `0`.
- Complete SAXS matrix: `689 passed, 6 warnings in 503.60s`, exit `0`.
- The first verifier attempt was rejected by `task_check.py` because this card
  used noncanonical section headings; the card was corrected without changing
  production behavior and the verifier was rerun afterward.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/config.py`
- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_2d_detector_orientation_evidence.py`
- `tests/test_saxs_batch_parameters.py`
- `docs/superpowers/specs/2026-07-31-saxs-herman-confidence-gate-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-herman-confidence-gate.md`
- `docs/agent/tasks/2026-07-31-saxs-herman-confidence-gate.md`
- `docs/acceptance/2026-07-31-saxs-herman-confidence-gate.md`

## Pre-existing workspace changes

Parallel Advisor, memory edits, SAXS scratch/test-storage directories, real
datasets, and unrelated documentation remain outside this checkpoint.

## Checkpoint

The explicit allowlist checkpoint is created only after the corrected task
card passes the structured verifier. No push or merge is performed.
