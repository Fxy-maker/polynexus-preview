---
kind: task
status: completed
date: 2026-07-29
title: Preserve modern SAXS temperature Figure frames with dirty axis tokens
---

# Modern SAXS temperature Figure axis dirty-input guard

## Goal

Keep the modern SAXS temperature Figure provider usable when an individual
temperature-axis token is malformed, while preserving frame positions and
the existing scientific evidence boundaries.

## Non-goals

- Do not change SAXS analysis, `TempSeriesResult`, quality levels, physical
  thresholds, evidence roles, publication gates, AI, or rescue behavior.
- Do not delete, reorder, interpolate, pad, copy, or infer frames or
  temperatures.
- Do not modify q/I sanitization, detector/2D/orientation handling, GUI code,
  real datasets, generated outputs, or parallel workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_provider.py`: modern temperature-axis
  projection and its frame/waterfall/summary/heatmap consumers;
- `tests/test_saxs_temperature_figure_provider.py`: focused dirty-axis
  regression;
- this task card, design, plan, acceptance evidence, and durable active-work
  memory.

## Implementation plan

1. Add a focused RED regression for a malformed temperature token and record
   the existing whole-array conversion failure.
2. Project the temperature axis elementwise with the existing numeric
   coercion helper and reuse that projection across all modern temperature
   Figure definitions.
3. Run focused GREEN, the related Figure provider matrix, the exact SAXS
   matrix, the structured verifier, diff checks, and storage dry-runs.
4. Record exact evidence and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] A malformed temperature token becomes an explicit missing numeric value
      without raising from modern Figure construction.
- [x] Frame count, frame identity, and valid temperature order remain stable.
- [x] Per-frame, waterfall, parameter, and heatmap definitions use the same
      projected axis and remain valid under existing Figure contracts.
- [x] Clean input and frame-count mismatch behavior are unchanged.
- [x] No quality level, physical gate, publication role, AI/rescue behavior,
      or automatic repair policy changes.
- [x] TDD RED/GREEN, focused/SAXS/structured verification, storage dry-run,
      diff audit, and explicit allowlist checkpoint evidence are recorded.

## Verification evidence

- TDD RED: `1 failed, 12 deselected in 0.12s`; the malformed token raised from
  the pre-existing `np.asarray(..., dtype=float)` whole-axis conversion.
- Focused GREEN: `1 passed, 12 deselected in 0.12s`.
- Related Figure/provider/evidence matrix: `50 passed in 10.58s`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `290 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Exact SAXS matrix exited `0`: `589 passed, 6 warnings in 426.28s`. Warnings
  were the existing Arial glyph and EDF geometry-header warnings.
- `git diff --check` exited `0`.
- Storage report and clean were dry-run only: `54` artifacts, `6` eligible
  legacy entries, `48` retained, and `0` removed. The eligible entries were
  zero-byte legacy directories; no `test_storage.py --apply` was run.

## Known limitations

This task covers only the modern SAXS temperature Figure condition axis.
Invalid temperature values remain missing and do not gain scientific meaning;
quality levels, physical thresholds, sequence evidence, AI/rescue decisions,
detector/orientation semantics, and publication authorization remain governed
by their existing contracts and human review gates.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_modern_temperature_axis_dirty_focus'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k dirty_temperature_axis
python -m pytest -q tests/test_saxs_temperature_figure_provider.py tests/test_saxs_temperature_figure_panels.py tests/test_saxs_figure_evidence_binding.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix is a pass only with a complete pytest summary and exit
code `0`. `test_storage.py --apply` is forbidden for this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `docs/agent/tasks/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`
- `docs/superpowers/specs/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`
- `docs/acceptance/2026-07-29-saxs-modern-temperature-figure-axis-dirty-input.md`
- `docs/agent/memory/active-work.md`

`docs/agent/memory/current-state.md`, all existing scratch/test-storage
directories, GUI/editor drafts, and other parallel changes are outside this
checkpoint.
