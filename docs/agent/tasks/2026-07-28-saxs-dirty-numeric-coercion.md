---
kind: task
status: completed
date: 2026-07-28
title: Preserve valid SAXS points during dirty numeric coercion
---

# SAXS dirty numeric coercion

## Goal

Preserve individually convertible q/I observations when a dirty 1D input
contains a malformed numeric token. A malformed element must remain an
explicit invalid observation for the existing quality report and sanitizer,
while valid neighboring observations remain analyzable.

## Non-goals

- Do not interpolate, pad, copy, aggregate duplicate q values, or fabricate
  observations.
- Do not change existing positivity, finite-value, point-count, Guinier, or
  physical gates.
- Do not mutate caller-owned arrays or strings.
- Do not change rescue, AI, Figure, Manifest, Export, or publication behavior.
- Do not edit real datasets, generated outputs, or parallel GUI work.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: elementwise numeric
  coercion used by the existing 1D quality/sanitization contract.
- `tests/test_saxs_dirty_profile_sanitization.py`: malformed-token regression
  coverage and provenance assertions.

## Implementation plan

1. Add focused tests asserting that malformed q/I tokens are dropped at their
   original pair positions while neighboring valid pairs survive and report
   `invalid_pairs_dropped`.
2. Run the focused tests to capture the expected RED against whole-array
   conversion.
3. Change only `_as_1d_float_array()` to coerce elements independently,
   representing conversion failures as `NaN`.
4. Run focused tests, the exact SAXS matrix, task-scoped verification, and
   `git diff --check` with an isolated test root if required by Windows.
5. Update this card and durable memory, then invoke `scripts/auto_commit.py`
   with the explicit allowlist. Leave all pre-existing parallel files out.

## Acceptance criteria

- [x] A malformed element does not erase valid convertible elements in the same
      q or intensity axis.
- [x] The malformed pair is excluded by the existing sanitizer and recorded by
      the existing `invalid_pairs_dropped`/quality reason contract.
- [x] Length alignment, stable sorting, duplicate retention, and input
      immutability remain unchanged.
- [x] Empty or entirely malformed inputs still fail closed as `Unusable`.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, and explicit
      allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: `4 passed, 2 failed`; both failures showed that one malformed token
  erased the whole q/I axis.
- TDD GREEN: `6 passed`.
- Exact SAXS matrix: `430 passed, 6 warnings in 28.60s`; warnings are the
  existing Arial glyph and EDF geometry warnings.
- Structured verifier: exit `0`; quality gate `287 passed`, preprocessing gate
  `106 passed`, Ruff, compile, type baseline, memory/task, and whitespace all
  passed.
- `git diff --check` passed. The checkpoint is created with the explicit
  allowlist below; no parallel files are included.

## Known limitations

Elementwise coercion only accepts Python/NumPy values supported by `float()`;
malformed tokens become explicit invalid observations and are not repaired.
Scientific applicability, rescue acceptance, AI behavior, raw detector
calibration, GUI review, and publication approval remain unchanged and open.

## Verification

```powershell
python -m pytest -q tests/test_saxs_dirty_profile_sanitization.py
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-dirty-numeric-coercion.md --changed --types
git diff --check
```

## Changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_dirty_profile_sanitization.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-dirty-numeric-coercion-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-dirty-numeric-coercion.md`
- `docs/agent/memory/active-work.md`
- `docs/agent/memory/current-state.md`

## Pre-existing workspace changes

The current worktree contains an unrelated in-progress Results Review prefix
deduplication change, many historical pytest directories, and GUI/editor
drafts. They remain untouched and outside this task checkpoint.
