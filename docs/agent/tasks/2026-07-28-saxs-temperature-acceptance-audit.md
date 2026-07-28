---
kind: task
status: completed
date: 2026-07-28
title: Attach the existing scientific acceptance audit to SAXS temperature results
---

# SAXS temperature scientific acceptance audit

## Goal

Attach the existing read-only `scientific_acceptance_audit` to the SAXS
temperature parameter boundary so failed or diagnostic temperature evidence is
visible without changing any analysis decision.

## Evidence baseline

The real `D:\PolyNexus\测试数据\saxs\pa6变温` run has five ordered temperature
frames from 170--220 °C, `validation_passed=False`, existing
`qstar_contaminated` and `mask_truncated` quality flags, and an `Unusable` raw
detector/series evidence boundary. Its existing Guinier sequence evidence is
already `Unusable` with `guinier_sequence_no_valid_frames`.

## Non-goals

- Do not modify the audit builder, Guinier analysis, Q*, mask handling, physical
  thresholds, quality levels, publication roles, AI behavior, or rescue logic.
- Do not interpolate, fabricate, reorder, or automatically rescue frames.
- Do not add a temperature-specific scientific threshold.
- Do not edit `current-state.md`, real data, generated outputs, or scratch
  directories.

## Affected boundaries

- `polynexus/core/saxs.py`: temperature `get_parameters()` return boundary only;
- `tests/test_saxs_temperature_acceptance_audit.py`: synthetic and optional
  real-temperature regression evidence;
- this task card, the linked design/plan, acceptance record, and
  `docs/agent/memory/active-work.md`: durable workflow evidence only.

## Implementation plan

1. Add a temperature regression that fails when the audit key is absent and
   checks the existing sequence evidence and strict JSON boundary.
2. Attach the existing audit builder to the temperature payload after aligned
   batch rows are assembled, without changing any scientific calculation.
3. Run focused RED/GREEN, the exact SAXS matrix, the structured verifier, and
   diff checks; record evidence and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] Temperature parameters expose `scientific_acceptance_audit` built from
  the existing validation and evidence fields.
- [x] The audit remains `diagnostic_only` for the known failed real temperature
  run and preserves `publication_decision_changed=False`.
- [x] Existing Guinier sequence evidence and its reason codes remain unchanged;
  no frame is added, removed, interpolated, or reordered.
- [x] The new payload is strict-JSON serializable with `allow_nan=False`.
- [x] Focused RED/GREEN, exact SAXS matrix, structured verifier, diff check,
  and explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: `2 failed`; both failures were the expected missing
  `scientific_acceptance_audit` key, including the real five-frame PA6 run.
- Focused GREEN: `2 passed in 12.74s`.
- Exact SAXS matrix: `437 passed, 6 warnings in 67.14s`. Warnings were the
  existing Arial CJK glyph warnings and existing EDF geometry-default warnings.
- Real PA6 temperature run: five frames, 170--220 °C, final
  `validation_passed=False`, audit status `diagnostic_only`, existing Guinier
  sequence `Unusable` with `guinier_sequence_no_valid_frames`, and
  `publication_decision_changed=False`.
- Structured verifier: exit `0`; task card valid, memory check passed, Ruff,
  compile, and type baseline passed; quality `287 passed`, preprocessing `106
  passed`, and whitespace passed.
- `git diff --check` passed through the structured verifier.

## Known lifecycle limitation

The shared `BaseEngine.run_pipeline()` stores `get_parameters()` before its
post-analysis validation hook. Therefore the cached audit snapshot in a real
`result.parameters` payload can retain the validation value available at
parameter construction, while the final `result.validation_passed` is updated
afterward. This task intentionally does not change that shared lifecycle or
add a new validation rule; the final result flag and the audit's existing
evidence status must be read together. A future lifecycle-consistency task may
refresh the audit after final validation.

## Verification

```powershell
python -m pytest -q tests/test_saxs_temperature_acceptance_audit.py -vv --basetemp C:\Temp\PolyNexus_saxs_temperature_acceptance_redgreen
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName) --basetemp C:\Temp\PolyNexus_saxs_temperature_acceptance_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-temperature-acceptance-audit.md --changed --types
git diff --check
```

All pytest storage must remain outside the repository. A timeout, collection
only result, or historical process is not counted as a pass.

## Explicit changed-file allowlist

- `polynexus/core/saxs.py`
- `tests/test_saxs_temperature_acceptance_audit.py`
- this task card
- `docs/superpowers/specs/2026-07-28-saxs-temperature-acceptance-audit-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-temperature-acceptance-audit.md`
- `docs/acceptance/2026-07-28-saxs-temperature-acceptance-audit.md`
- `docs/agent/memory/active-work.md`

## Checkpoint

The explicit allowlist checkpoint is created after the verification record is
finalized. No push, merge, publication approval, or real-data write is part of
this task.
