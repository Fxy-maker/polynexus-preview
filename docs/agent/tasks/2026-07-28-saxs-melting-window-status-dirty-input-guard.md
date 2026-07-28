---
kind: task
status: completed
date: 2026-07-28
title: Guard SAXS melting-window status against dirty inputs
---

# SAXS melting-window status dirty-input guard

## Goal

Make `classify_melting_window_status()` safely degrade dirty temperatures and
melting-boundary values while preserving its existing status/reason contract.

## Non-goals

- Do not change margin floors, status names, reason codes, expected-melt soft
  hints, sequence branches, or physical thresholds.
- Do not infer or interpolate a melting window, fill/delete/reorder frames,
  invoke AI/rescue, or alter publication roles.
- Do not edit GUI code, real datasets, generated outputs, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_temperature.py`: margin helper and public
  status classifier.
- `tests/test_saxs_melting_window_status_dirty_input.py`: focused regression.
- This task's spec, plan, acceptance note, and durable active-work memory.

## Implementation plan

1. Write RED tests for dirty sequence/scalar input, margin equivalence,
   expected-melt hints, reason/status stability, and immutability.
2. Reuse existing numeric coercion at both the margin and classifier boundary,
   leaving classification branches unchanged.
3. Run focused and SAXS verification, record evidence and storage audit, then
   create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] Dirty temperature sequences and Tm scalars no longer raise.
- [x] Clean status/reason results remain equivalent.
- [x] Existing margin floors, statuses, reason codes, and soft hints remain.
- [x] No inference, interpolation, frame repair, rescue, or publication change
  is added.
- [x] TDD RED/GREEN, matrices, verifier, diff, storage audit, and checkpoint
  are recorded.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_melting_window_status_dirty_input.py --basetemp=D:\PolyNexus_saxs_melting_window_status_redgreen
$temperatureTests = Get-ChildItem -Path tests -Filter 'test_saxs_temperature*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $temperatureTests --basetemp=D:\PolyNexus_saxs_melting_window_status_temperature_matrix
$saxsTests = Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests --basetemp=D:\PolyNexus_saxs_melting_window_status_saxs_matrix
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-melting-window-status-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No fresh full/boundary result is attributed unless a fresh command returns a
pytest summary and exit code 0.

## Verification

The focused RED run showed the pre-fix raw coercion failures. GREEN and the
temperature/SAXS matrices returned exit code 0. The structured command is:

`python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-melting-window-status-dirty-input-guard.md --changed --types`

Test-storage cleanup remains dry-run unless explicitly authorized.

## Verification evidence

- RED: `4 failed, 1 passed`.
- GREEN: `5 passed in 0.26s`.
- Temperature matrix: `53 passed in 14.83s`.
- Exact SAXS matrix retry: `529 passed, 6 warnings in 218.57s`, exit code `0`.
- Structured verifier: exit code `0`; quality `287`, preprocessing `106`,
  Ruff/compile/type-baseline/task/memory/whitespace checks passed.
- Targeted Ruff/compile passed; `git diff --check` passed with only the
  existing CRLF normalization notice.
- Test-storage report and dry-run: `532` artifacts, `206` eligible,
  `0` removed. No `--apply` was executed in this task.

The first SAXS matrix invocation reached the tool's 120-second limit without
an output summary; its pytest process later exited naturally. It is not used
as evidence. The independent retry above is the authoritative SAXS matrix
result. No fresh full/boundary result is attributed to this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_temperature.py`
- `tests/test_saxs_melting_window_status_dirty_input.py`
- `docs/agent/tasks/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-28-saxs-melting-window-status-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`
- `docs/acceptance/2026-07-28-saxs-melting-window-status-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

Pre-existing `current-state.md`, `saxs_engine/io.py`, GUI/editor drafts,
`.superpowers/`, and external test-output directories are outside this task.

## Checkpoint

The explicit seven-file allowlist checkpoint is created after the documented
verification. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
