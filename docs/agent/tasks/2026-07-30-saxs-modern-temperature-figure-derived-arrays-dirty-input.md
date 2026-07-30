---
kind: task
status: completed
date: 2026-07-30
title: Preserve modern SAXS temperature Figures with dirty derived arrays
---

# Modern SAXS temperature Figure derived-array dirty-input guard

## Goal

Keep modern SAXS temperature parameter, waterfall, and heatmap Figure
construction usable when individual derived metric tokens are malformed,
without changing scientific interpretation or frame identity.

## Non-goals

- Do not change SAXS analysis, `TempSeriesResult`, quality levels, physical
  thresholds, evidence/publication roles, AI, or rescue behavior.
- Do not interpolate, pad, copy, sort, aggregate, infer, delete frames, or
  create new fallback semantics.
- Do not modify q/I, temperature-axis, detector/2D/orientation, GUI, real
  datasets, generated outputs, or parallel workspace files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_provider.py`: `_series_values()` input
  projection used by modern temperature parameter definitions;
- `tests/test_saxs_temperature_figure_provider.py`: derived-array regression;
- this task card, design, plan, acceptance evidence, and durable active-work
  memory.

## Implementation plan

1. Add and run the focused malformed-derived-array RED regression.
2. Apply the existing elementwise coercion at `_series_values()` only, keeping
   required/optional and length-mismatch behavior unchanged.
3. Run focused, related SAXS, structured verifier, diff, and storage dry-run
   checks with exact summaries and exit codes.
4. Record evidence and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] A malformed required derived-array token becomes `NaN` without
      aborting modern temperature Figure construction.
- [x] Valid neighboring values, frame count, and source positions remain.
- [x] `lc_effective_array` retains the existing raw `lc_array` fallback.
- [x] Missing required arrays and length mismatches retain existing errors.
- [x] Clean inputs and all scientific/publication semantics are unchanged.
- [x] TDD RED/GREEN, focused/SAXS/structured verification, storage dry-run,
      diff audit, and explicit allowlist checkpoint evidence are recorded.

## Verification evidence

- TDD RED: `1 failed, 13 deselected`; the malformed `L_array` token raised
  from the pre-existing whole-array conversion in `_series_values()`.
- Focused GREEN: `1 passed, 13 deselected in 0.10s`.
- Related temperature Figure/provider/evidence matrix: `51 passed in 9.70s`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `290 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Exact SAXS matrix exited `0`: `590 passed, 6 warnings in 388.51s`. Warnings
  were the existing Arial glyph and EDF geometry-header warnings.
- `git diff --check` exited `0`.
- Storage report and clean were dry-run only: `54` artifacts, `6` eligible
  legacy entries, `48` retained, and `0` removed. No `test_storage.py --apply`
  was run.
- Explicit allowlist implementation checkpoint: `bb0048c`; no push or merge
  was performed.

## Known limitations

This task covers modern temperature Figure derived metric arrays only. Invalid
metrics remain explicit missing values and do not gain scientific meaning;
quality levels, physical thresholds, sequence evidence, AI/rescue decisions,
detector/orientation semantics, and publication authorization remain governed
by existing contracts and human review gates.

## Verification

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k dirty_derived_arrays --basetemp=D:\PolyNexus_saxs_modern_temperature_derived_dirty_red
python -m pytest -q tests/test_saxs_temperature_figure_provider.py tests/test_saxs_temperature_figure_panels.py tests/test_saxs_figure_evidence_binding.py --basetemp=D:\PolyNexus_saxs_modern_temperature_derived_dirty_related
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix is a pass only with a complete pytest summary and exit
code `0`. `test_storage.py --apply` is forbidden for this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `docs/agent/tasks/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`
- `docs/superpowers/specs/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`
- `docs/acceptance/2026-07-30-saxs-modern-temperature-figure-derived-arrays-dirty-input.md`
- `docs/agent/memory/active-work.md`

`docs/agent/memory/current-state.md`, GUI/editor changes, all scratch and
test-storage paths, and other parallel files remain outside this task.
