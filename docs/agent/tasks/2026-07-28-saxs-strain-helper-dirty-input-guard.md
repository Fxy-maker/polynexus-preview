---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS strain helpers against dirty q/I inputs
---

# SAXS strain-helper dirty-input guard

## Goal

Make the public `detect_strain_phase()` and `detect_voids()` 1D boundaries
consume the same deterministic finite-positive q/I survivors as the main SAXS
path, so malformed strain-series post-processing inputs do not raise or leak
invalid observations into their existing calculations.

## Confirmed baseline

The read-only probe on the current checkout reproduced `TypeError` for an
object q array containing a non-numeric token and `IndexError` for mismatched
q/I lengths in both helpers. Empty arrays currently return their legacy shapes
and classifications; that behavior is not changed.

## Decision

Call `sanitize_1d_profile(q, I)` at the beginning of both helpers and use its
detached `q` and intensity survivors for the existing calculations. This uses
the approved policy of aligned-prefix selection, numeric coercion, dropping
non-finite or non-positive pairs, stable q sorting, and duplicate retention.

## Non-goals

- Do not change phase thresholds, Q-star scalar semantics, Porod windows,
  point-count gates, void calculations, or return keys.
- Do not add interpolation, extrapolation, duplicate aggregation, frame
  copying, fabricated observations, new quality levels, or AI/rescue behavior.
- Do not change `DataQualityReport`, publication eligibility, GUI code, real
  datasets, generated outputs, or parallel workspace changes.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_strain.py`: two public 1D helper inputs;
- `tests/test_saxs_strain_helper_dirty_input.py`: dirty, mismatch, empty, and
  immutability regressions;
- this task card, design/spec, implementation plan, acceptance note, and
  durable memory.

## Implementation plan

1. Write a RED regression with malformed object q/I, mismatched lengths,
   explicit sanitized-survivor references, empty input, and immutability
   assertions.
2. Bind both public helper entrances to `sanitize_1d_profile()` and leave all
   existing calculations, thresholds, and return structures unchanged.
3. Run focused GREEN, strain and exact SAXS matrices, the structured verifier,
   diff/storage checks, then record evidence and create the explicit checkpoint.

## Acceptance criteria

- [x] Dirty object q/I input produces the same phase and void evidence as its
  finite-positive, stably q-sorted survivors without raising.
- [x] Mismatched q/I lengths use the existing aligned-prefix policy without
  padding or indexing errors.
- [x] Empty input retains the existing result shape and scalar classification;
  no metric is fabricated.
- [x] Clean outputs remain numerically compatible and caller-owned arrays remain
  unchanged.
- [x] No new physical threshold, quality level, rescue action, or publication role
  is introduced.
- [x] TDD RED/GREEN, focused strain matrix, exact SAXS matrix, structured verifier,
  diff check, test-storage report, and explicit allowlist checkpoint are
  recorded with actual outcomes.

## Verification

```powershell
python -m pytest -q tests/test_saxs_strain_helper_dirty_input.py --basetemp=D:\PolyNexus_saxs_strain_helper_dirty_redgreen
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_strain_helper_dirty_matrix
$env:PYTEST_ADDOPTS='--basetemp=D:\PolyNexus_saxs_strain_helper_dirty_verify'
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-strain-helper-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

Full/boundary verification is not attributed to this atomic task unless a
fresh command returns a pytest summary and exit code 0.

## Verification evidence

- Read-only baseline probe reproduced `TypeError` for a malformed object q
  token and `IndexError` for mismatched q/I lengths in both helpers.
- TDD RED: `2 failed, 1 passed`.
- Focused GREEN: `3 passed in 0.12s`.
- Strain matrix: `11 passed in 0.33s`, exit code `0`.
- Exact SAXS matrix: `497 passed, 6 warnings in 193.07s`, exit code `0`.
  Warnings were the existing Arial CJK glyph and EDF geometry-header warnings.
- Task verifier: exit code `0`; task/memory checks, Ruff, compile, type
  baseline, quality `287`, preprocessing `106`, and whitespace all passed.
- `git diff --check`: exit code `0` with only Git's CRLF normalization notice.
- Test-storage report and cleanup dry-run: `505` artifacts, `175` eligible,
  `330` protected, `0` removed. No test data was deleted.
- No fresh full/boundary result is attributed to this atomic task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_strain.py`
- `tests/test_saxs_strain_helper_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-strain-helper-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-strain-helper-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-strain-helper-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-strain-helper-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, GUI/editor drafts, `.superpowers/`, and
external test-output directories are outside this task.

## Checkpoint

After fresh verification, create one local checkpoint with
`scripts/auto_commit.py` and exactly the allowlist above. No push, merge,
deployment, data deletion, or scientific/publication approval is part of this
task.
