---
kind: task
status: completed
date: 2026-07-29
title: Record temperature auxiliary 1D Figure provenance
---

# SAXS temperature auxiliary 1D Figure provenance

## Goal

Expose deterministic projection quality for the existing temperature Avrami,
Correlation, and IDF Figures.

## Non-goals

- No new SAXS analysis, threshold, physical gate, interpolation, padding,
  repair, rescue, AI action, or publication-role change.
- No change to source values, finite filtering, minimum-point rules, selection,
  static/strain Figures, real data, generated output, or memory files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_temperature.py`: detached recipe maps.
- `tests/test_saxs_temperature_figure_panels.py`: dirty and clean regressions.
- This task's spec and implementation plan.

## Contract

The Avrami recipe records `parameters.avrami_projection_quality`. Selected
temperature evidence recipes record `parameters.trace_projection_quality` with
`correlation` and/or `idf` entries. Each entry contains aligned-prefix pair
counts and `complete`/`partial_nonfinite` status using Python integers. Only
emitted Figure sources receive entries; no omitted trace metadata is invented.

## Acceptance criteria

- [x] Dirty and clean Avrami projection quality is recorded.
- [x] Dirty and clean Correlation/IDF projection quality is recorded.
- [x] Existing source values, omission rules, roles, and strict JSON behavior
      remain unchanged.
- [x] TDD RED/GREEN, structured/SAXS verification, storage dry-run, diff audit,
      and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add dirty and clean Figure regressions and verify the expected RED.
2. Add local detached counters beside the existing Avrami and trace projection
   boundaries, then verify GREEN and related temperature tests.
3. Run task-scoped/SAXS verification, storage dry-run, diff/allowlist audit,
   and create one atomic checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_temperature_auxiliary_focus'
python -m pytest -q tests/test_saxs_temperature_figure_panels.py -k auxiliary_provenance -vv
python -m pytest -q tests/test_saxs_temperature_figure_panels.py tests/test_saxs_temperature_figure_provider.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-temperature-auxiliary-1d-provenance.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix must use an external neutral basetemp and a final pytest
summary with exit code `0`. This task never runs `test_storage.py --apply`.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_temperature.py`
- `tests/test_saxs_temperature_figure_panels.py`
- `docs/agent/tasks/2026-07-29-saxs-temperature-auxiliary-1d-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-temperature-auxiliary-1d-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-temperature-auxiliary-1d-provenance.md`

## Verification evidence

- TDD RED: `2 failed, 6 deselected`, with the expected missing recipe fields.
- TDD GREEN: `2 passed, 6 deselected`; complete temperature Figure panel and
  provider slice: `17 passed`.
- Task-scoped verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `287 passed`, preprocessing `106 passed`, and whitespace
  all passed.
- Fresh PowerShell-expanded SAXS matrix exited `0`: `558 passed, 6 warnings`
  in `241.26s`. Warnings are the existing Arial CJK glyph and missing EDF
  geometry-header warnings.
- Storage report and clean were dry-run only: `14` artifacts,
  `13,935,155,317` bytes total, `6` eligible entries but `0` eligible bytes;
  no `--apply` command or removal was performed.
- `git diff --check` exited `0` as part of structured verification.

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical test/storage
directories, `.superpowers/`, scratch outputs, and all other untracked or
parallel files remain outside this checkpoint.
