---
kind: task
status: completed
date: 2026-07-28
title: Diagnose invalid SAXS Guinier sequence source mappings
---

# SAXS Guinier sequence source-index integrity

## Goal

Prevent duplicate, negative, or non-integral frame-to-source mappings from
being presented as a valid Guinier sequence trend, while preserving legitimate
temperature sorting and all existing Rg evidence.

## Non-goals

- Do not sort, interpolate, delete, impute, or rewrite temperature frames,
  source indices, or Rg values.
- Do not infer a missing source-index range or fabricate missing frames.
- Do not add physical thresholds, change Guinier fitting, continuity logic, or
  sequence evidence beyond provenance integrity.
- Do not change static/strain metrics, AI rescue, publication roles, GUI
  behavior, or Figure/Manifest/Export contracts.
- Do not edit `current-state.md`, real datasets, generated outputs, scratch, or
  parallel task files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`: immutable sequence
  DTO and source-index integrity builder logic.
- `tests/test_saxs_guinier_sequence_evidence.py`: duplicate, invalid, and
  reordered source-index regressions.
- Task/spec/plan and `docs/agent/memory/active-work.md`: durable evidence.

## Implementation plan

1. Add RED tests for duplicate, negative/non-integral, and legitimately
   reordered source-index mappings.
2. Add source-index diagnostic fields and reason codes to the existing strict
   JSON-safe sequence contract; do not infer gaps or alter frame positions.
3. Run the sequence/temperature propagation matrix, structured verifier, diff
   check, and test-storage dry-run with external basetemp.
4. Run the exact SAXS matrix if bounded execution permits, record timeout/no
   summary honestly, update durable memory, and create the allowlist checkpoint.

## Acceptance criteria

- [x] Duplicate source indices preserve all participating frame positions,
  emit `guinier_sequence_source_index_duplicate`, and force `Diagnostic`.
- [x] Negative/non-integral source indices preserve invalid positions, emit
  `guinier_sequence_source_index_invalid`, and force `Diagnostic`.
- [x] Valid reordered mappings such as `[1, 0]` remain `Trend` and expose
  `source_index_order_reordered=True` without an invalid reason.
- [x] Existing length mismatch, missing-frame, temperature-axis, and JSON
  round-trip behavior remains passing.
- [x] Focused tests, structured verifier, diff check, storage dry-run, exact
  SAXS result/limitation, and explicit checkpoint are recorded.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_index_red'
python -m pytest -q tests/test_saxs_guinier_sequence_evidence.py -k source_index

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_guinier_source_index_focus'
python -m pytest -q tests/test_saxs_guinier_sequence_evidence.py tests/test_saxs_temperature_guinier_evidence.py tests/test_saxs_temperature_invalid_axis_fail_closed.py tests/test_saxs_temperature_invalid_time_values_fail_closed.py tests/test_saxs_mode_evidence_propagation.py
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-guinier-source-index-integrity.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The exact SAXS matrix uses a PowerShell-expanded `test_saxs_*.py` file list and
an external basetemp; a timeout or missing pytest summary is not a pass.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_quality_contracts.py`
- `tests/test_saxs_guinier_sequence_evidence.py`
- `docs/agent/tasks/2026-07-28-saxs-guinier-source-index-integrity.md`
- `docs/superpowers/specs/2026-07-28-saxs-guinier-source-index-integrity-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-guinier-source-index-integrity.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, GUI/editor drafts, and other parallel files stay
outside this checkpoint.

## Verification evidence

- TDD RED: the corrected source-index selection ran `4 failed, 10
  deselected`; failures were the expected missing DTO fields and reordered
  metadata. An initial overly narrow `-k source_index` selection ran only one
  pre-existing test and is not used as RED evidence.
- TDD GREEN and propagation matrix: `25 passed in 0.89s`.
- Structured verifier: exit `0`; task card/memory, Ruff, compile, type
  baseline, quality `287 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- `git diff --check`: passed.
- Test-storage report: exit `0`, dry-run mode; `490` artifacts, `0` eligible,
  `490` protected, and `0` removed. No data was deleted or moved.
- Exact SAXS matrix: PowerShell-expanded file list attempted with an external
  basetemp; timed out after `124` seconds with no pytest summary (`exit 124`).
  Its exact matrix process was PID `43348` and was terminated after the timeout;
  the separate pre-existing full/boundary verifier was left untouched. The
  exact SAXS matrix is not claimed as passed.
- Explicit allowlist checkpoint: ready to create with the six listed files.
