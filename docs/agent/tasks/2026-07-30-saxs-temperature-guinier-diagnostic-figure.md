---
task_id: 2026-07-30-saxs-temperature-guinier-diagnostic-figure
kind: scientific-figure-contract
status: completed
date: 2026-07-30
title: Expose temperature Guinier evidence as a diagnostic figure
---

# SAXS temperature Guinier diagnostic figure

## Goal

Expose the already-emitted temperature 1D Guinier Rg evidence as an auditable
diagnostic FigureDefinition without changing analysis or publication authority.

## Non-goals

- No Guinier recalculation, window selection, quality-level changes, or new
  physical thresholds.
- No interpolation, frame copying, frame deletion, phase decision, rescue, AI,
  or automatic publication promotion.
- No changes to static, strain, detector, orientation, or existing temperature
  parameter/heatmap semantics.
- Do not modify `current-state.md`, real datasets, generated outputs, scratch,
  or parallel NMR/Joint files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_provider.py`: diagnostic definition and
  nullable evidence projection.
- `tests/test_saxs_temperature_figure_provider.py`: focused Figure contract
  and backward-compatibility regressions.
- This task's spec, plan, acceptance note, and `active-work.md`.

## Acceptance criteria

- [x] A temperature result with Rg evidence emits
      `saxs.series.temperature.guinier` with `publication_role="diagnostic"`.
- [x] Finite values, missing values, source indices, frame levels, and reason
      codes are preserved in strict JSON-safe data without mutation.
- [x] The definition validates and is V2-runtime ready.
- [x] A legacy result without Rg evidence retains the existing figure set.
- [x] TDD RED/GREEN, structured verification, exact SAXS matrix, storage
      dry-run, diff, and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add RED tests for the new definition, missing-value preservation, metadata
   provenance, V2 readiness, and legacy compatibility.
2. Implement the smallest provider extension using existing FigureDefinition
   contracts and emitted `TempSeriesResult` evidence only.
3. Run focused GREEN, structured verification, the exact SAXS matrix, storage
   report/dry-run, and `git diff --check`.
4. Record acceptance evidence and update durable active-work state, then create
   one explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "guinier_diagnostic" -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-red
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "guinier_diagnostic or temperature_provider" -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-green
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

The exact SAXS matrix counts only a fresh complete pytest summary with exit
code `0`. Full/boundary release and human scientific review remain separate
gates. No `test_storage.py --apply` is authorized.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `docs/superpowers/specs/2026-07-30-saxs-temperature-guinier-diagnostic-figure-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`
- `docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`
- `docs/acceptance/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md`
- `docs/agent/memory/active-work.md`
