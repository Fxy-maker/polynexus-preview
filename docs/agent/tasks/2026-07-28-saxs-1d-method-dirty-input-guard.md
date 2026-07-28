---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS 1D physical helpers against dirty q/I inputs
---

# SAXS 1D physical-helper dirty-input guard

## Goal

Make the existing scattering-invariant, Porod, and Kratky helper boundaries
consume the same deterministic finite positive q/I survivors as the main SAXS
path, so peripheral temperature/strain/batch callers do not receive polluted
or exceptional method outputs.

## Decision

Reuse `sanitize_1d_profile()` at each helper boundary. The helper already
defines aligned-pair filtering, stable q sorting, duplicate retention, and
detached arrays; this task adds no new threshold or repair policy. Normal
`analyze_single()` quality reports remain authoritative for provenance. Empty
Kratky input returns its existing result shape with empty arrays and a missing
peak rather than raising from a reduction on an empty array.

## Non-goals

- Do not change Guinier fitting, qRg rules, Porod slope interpretation,
  invariant integration bounds, Kratky peak semantics, or physical gates.
- Do not aggregate duplicate q values, interpolate, extrapolate, copy frames,
  fabricate observations, or invoke AI/rescue behavior.
- Do not change the `DataQualityReport` schema or silently promote evidence.
- Do not edit real datasets, generated outputs, GUI code, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/core.py`: invariant and Kratky helper input
  boundary;
- `polynexus/core/saxs_engine/saxs_physical_helpers.py`: Porod helper input
  boundary;
- `tests/test_saxs_1d_method_dirty_input.py`: dirty, empty, clean, and
  immutability regressions;
- this task card, design/spec, implementation plan, and durable memory.

## Implementation plan

1. Add RED tests with non-finite, non-positive, and unsorted q/I plus an empty
   Kratky profile; assert the current helper behavior fails or leaks invalid
   values.
2. Apply the existing sanitizer at the three helper boundaries and preserve
   the existing return keys, bounds, and method calculations.
3. Run focused GREEN, the exact SAXS matrix, task-scoped verifier, and diff
   check using external basetemps.
4. Record exact evidence and create one explicit allowlist checkpoint, leaving
   pre-existing current-state, GUI, and scratch changes untouched.

## Acceptance criteria

- [x] Invariant integration uses finite positive q/I survivors in stable q
  order and remains unavailable for an empty/insufficient survivor profile.
- [x] Porod `Kp`, q values, and Iq4 arrays are not contaminated by removed
  invalid pairs when the existing point-count gate is met.
- [x] Kratky arrays are finite for recoverable dirty input and empty input
  returns the legacy keys with empty arrays and no exception.
- [x] Clean inputs retain existing numeric outputs and caller-owned arrays are
  unchanged.
- [x] No new physical threshold, quality level, rescue action, or publication
  role is introduced.
- [x] TDD RED/GREEN, exact SAXS, task verifier, diff check, and checkpoint
  evidence are recorded with actual results.

## Verification

```powershell
python -m pytest -q tests/test_saxs_1d_method_dirty_input.py tests/test_saxs_1d_method_evidence.py --basetemp=D:\PolyNexus_saxs_1d_method_dirty_redgreen
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_1d_method_dirty_matrix
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_1d_method_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-1d-method-dirty-input-guard.md --changed --types
git diff --check
```

Full/boundary verification is not attributed to this atomic task unless a
fresh command returns a pytest summary and exit code 0.

## Verification evidence

- TDD RED: `3 failed`; failures exposed dirty invariant integration, unsorted
  Porod output, non-finite Kratky output, and the empty-Kratky reduction path.
- Focused GREEN: `8 passed in 0.37s`.
- Exact SAXS matrix: `484 passed, 6 warnings in 257.12s`. Warnings are the
  existing Arial CJK glyph and missing EDF geometry-header warnings.
- The first task verifier run stopped at changed-file Ruff because the touched
  legacy physical-helper module exposed existing `E741` findings. A narrow
  compatibility correction preserved the public parameter names and changed
  only the new local variable; the final verifier exited `0` with quality
  `287`, preprocessing `106`, task/memory, Ruff, compile, type baseline, and
  whitespace checks passing.
- No fresh full/boundary result is claimed for this slice. The separate
  full-boundary audit is recorded as a tool-level timeout and is not attributed
  to this change.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/core.py`
- `polynexus/core/saxs_engine/saxs_physical_helpers.py`
- `tests/test_saxs_1d_method_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-1d-method-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-1d-method-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-1d-method-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, full-boundary audit documents, GUI/editor
drafts, `.superpowers/`, and test-output directories are outside this task.

## Checkpoint

After verification, create one local checkpoint with `scripts/auto_commit.py`
and exactly the allowlist above. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
