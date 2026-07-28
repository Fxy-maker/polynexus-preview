---
kind: task
status: completed
date: 2026-07-28
title: Fail closed on mismatched SAXS 2D anisotropy axes
---

# SAXS 2D input shape fail-closed

## Goal

Prevent malformed 2D sector-map inputs from reaching boolean indexing and
raising an exception. When the intensity matrix and q/χ axes are structurally
incompatible, return the existing empty `AnisotropyResult` with explicit
`Unusable` orientation evidence and a reason code.

## Non-goals

- Do not transpose, reshape, crop, interpolate, or pad detector/sector data.
- Do not infer q/χ axes, beam center, geometry, masks, saturation, or material
  orientation.
- Do not change valid Herman, peak, pattern, or automatic-axis calculations.
- Do not change quality thresholds, rescue, AI, Figure, Manifest, Export, or
  publication behavior.
- Do not edit real datasets or parallel worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_anisotropy.py`: validate and normalize the
  existing 2D matrix and axes before analysis; preserve the detector evidence
  projection.
- `tests/test_saxs_2d_detector_orientation_evidence.py`: shape mismatch and
  strict evidence regression.

## Implementation plan

1. Add a RED regression using a matrix whose q-axis length differs from the
   matrix width and assert the current `IndexError`.
2. Normalize numeric array-like inputs without mutating them and fail closed
   when matrix/axis dimensionality or lengths are incompatible.
3. Reuse the existing detector/orientation evidence builder with an empty
   metric payload so the result is `Unusable`; add only an explicit structural
   reason code.
4. Run focused 2D tests, the exact SAXS matrix, task verifier, and diff checks.
5. Update durable memory and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Mismatched matrix/axis shapes never raise from `analyze_anisotropy()`.
- [x] Invalid shapes return `Unusable` orientation evidence with an explicit
      reason code and strict JSON-safe detector evidence.
- [x] Valid configured/auto orientation paths remain unchanged.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, and checkpoint
      evidence are recorded.

## Verification evidence

- TDD RED: `9 passed, 1 failed`; the failure was the expected boolean-indexing
  `IndexError` for a q-axis/matrix-width mismatch.
- TDD GREEN: `10 passed`.
- Exact SAXS matrix: `431 passed, 6 warnings in 29.12s`; warnings are the
  existing Arial glyph and EDF geometry warnings.
- Structured verifier: exit `0`; quality gate `287 passed`, preprocessing gate
  `106 passed`, Ruff, compile, type baseline, memory/task, and whitespace all
  passed.
- `git diff --check` passed. Full/boundary verification was not run for this
  scoped task and is not claimed.

## Verification

```powershell
python -m pytest -q tests/test_saxs_2d_detector_orientation_evidence.py
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-2d-input-shape-fail-closed.md --changed --types
git diff --check
```

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_anisotropy.py`
- `tests/test_saxs_2d_detector_orientation_evidence.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-2d-input-shape-fail-closed-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-2d-input-shape-fail-closed.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The shared worktree contains a modified `current-state.md`, historical pytest
directories, GUI/editor drafts, and other task files. They remain outside this
checkpoint.
