---
task_id: 2026-07-30-saxs-manual-mask-confirmed-rerun
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Add a fail-closed SAXS manual mask candidate and confirmed rerun boundary
---

# SAXS manual mask candidate and confirmed rerun

## Goal

Allow an explicitly edited detector mask to reach existing SAXS preprocessing
only after confirmation, while preserving the raw image and all existing
quality/physical gates.

## Non-goals

- No GUI drawing surface or new mask-editing interaction in this slice.
- No automatic mask inference, interpolation, morphology, or AI call.
- No new scientific threshold, physical gate, publication rule, or rescue
  acceptance rule.
- No edits to real datasets, generated outputs, or parallel worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_mask_edit.py`: strict candidate contract.
- `polynexus/core/saxs_engine/preprocess.py`: confirmed-mask integration and
  existing detector provenance.
- `polynexus/core/saxs_engine/__init__.py`: public SAXS mask-edit exports.
- `tests/test_saxs_manual_mask_confirmed_rerun.py`: RED/GREEN regression.

## Implementation plan

1. Add RED tests for strict candidate serialization, pending no-op behavior,
   digest mismatch rejection, and confirmed isotropic/anisotropic propagation.
2. Implement the pure candidate build/confirm/apply contract with explicit
   pixel operations and shape-bound digests.
3. Thread a confirmed candidate through full, sector, and azimuthal
   preprocessing while preserving the existing no-candidate payload.
4. Run task verification, the exact SAXS matrix, storage dry-run, and diff
   checks, then create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Candidate is detached strict JSON and contains only explicit changed
      pixel operations plus provenance digests.
- [x] Pending candidates are visible as candidate-only provenance and do not
      affect numerical preprocessing.
- [x] Invalid or unconfirmed candidates fail closed without mutating the base
      mask.
- [x] Confirmed candidates are applied consistently to full, sector, and
      azimuthal integration paths.
- [x] Existing detector quality report and downstream physical gates remain
      authoritative.

## Verification

```powershell
python -m pytest -q tests/test_saxs_manual_mask_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-manual-mask-red
python -m pytest -q tests/test_saxs_manual_mask_confirmed_rerun.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-manual-mask-green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-manual-mask-confirmed-rerun.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

Actual evidence on 2026-07-30:

- Focused RED had already failed at collection before the new module existed;
  focused GREEN and the task verifier passed before this final matrix.
- Exact SAXS matrix command using all current `tests/test_saxs_*.py` files:
  `636 passed, 6 warnings` in `540.67s`, exit code `0`.
- `python scripts/test_storage.py report --json`: `54` artifacts,
  `15802078628` total bytes, `emergency=false`, `eligible_bytes=0`, and no
  report failures.
- `python scripts/test_storage.py clean --older-than-hours 24`: dry-run,
  `Eligible: 0 bytes`, `Cleanup failures: 0`; no artifact was removed.
- `git diff --check`: passed.

Full/boundary verification is not claimed for this task; the release-level
full run remains governed by its separate documented evidence.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_mask_edit.py`
- `polynexus/core/saxs_engine/preprocess.py`
- `polynexus/core/saxs_engine/__init__.py`
- `tests/test_saxs_manual_mask_confirmed_rerun.py`
- `docs/superpowers/specs/2026-07-30-saxs-manual-mask-confirmed-rerun-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-manual-mask-confirmed-rerun.md`
- `docs/agent/tasks/2026-07-30-saxs-manual-mask-confirmed-rerun.md`
- `docs/acceptance/2026-07-30-saxs-manual-mask-confirmed-rerun.md`
- `docs/agent/memory/active-work.md`
