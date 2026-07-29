---
kind: task
status: completed
date: 2026-07-29
title: Degrade legacy SAXS temperature Figures when a frame is unplottable
---

# SAXS legacy temperature Figure partial-frame degradation

## Goal

Keep the legacy/compatibility temperature Figure provider usable when one or
more retained analysis frames contain no plottable q/I pair, while preserving
the original frame indices and making the omitted-frame reason explicit.

## Non-goals

- No change to temperature analysis, Guinier/Porod/Kratky/invariant/lamellar
  calculations, DataQualityReport, QualityLevel, physical gates, or rescue.
- No interpolation, padding, frame fabrication, neighbor copying, condition
  inference, automatic rescue, or AI behavior.
- No change to modern temperature Figures, static/strain Figures, detector or
  orientation projections, GUI behavior, or publication eligibility rules.
- Structural input-count mismatches between temperature, q, and intensity
  sequences remain `ValueError` contracts.
- Do not edit real datasets, generated output, `current-state.md`, scratch,
  or parallel worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_provider.py`: legacy temperature frame
  projection and evidence/index bookkeeping.
- `tests/test_saxs_temperature_figure_provider.py`: regression for a partially
  unavailable temperature series.
- This task's task/spec/plan/acceptance documents only.

## Design invariants

- A frame with at least two finite, positive q/I pairs keeps its original
  one-based Figure id and remains available to waterfall/summary projections.
- A frame with no plottable pair is omitted from Figure data sources; it is not
  replaced by a synthetic curve or a neighboring frame.
- `included_frame_indices`, `omitted_frame_indices`, and
  `omission_reasons` use the original zero-based source frame indices.
- An unavailable frame is recorded with the stable reason
  `figure_profile_unavailable`; the existing analysis evidence remains the
  source of scientific quality and publication decisions.
- Clean and partially-invalid-but-plottable legacy inputs retain their current
  definitions, roles, source ids, and strict-JSON-safe recipes.

## Acceptance criteria

- [x] RED reproduces the current whole-series failure for one fully invalid
      legacy temperature frame.
- [x] GREEN emits valid-frame Figures and summary projections without raising.
- [x] The invalid frame is omitted from data sources and explicitly listed in
      recipe evidence with its original index and stable reason.
- [x] Existing clean legacy lifecycle and dirty-valid-pair regressions remain
      green.
- [x] TDD, focused tests, exact SAXS matrix, structured verification, storage
      dry-run, diff audit, and explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: `1 failed, 10 deselected`; the failure was the expected
  `temperature frame has no plottable data: 2` from the old provider.
- TDD GREEN: `1 passed, 10 deselected`; the complete legacy provider file
  returned `11 passed in 4.74s`.
- Related temperature Figure consumers: `30 passed, 25 deselected in 5.25s`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, quality
  `287 passed`, preprocessing `106 passed`, and whitespace all passed. The
  shared changed-set also contained pre-existing parallel IR/Joint/NMR files;
  none are in this task's allowlist.
- Exact SAXS matrix exited `0`: `574 passed, 6 warnings in 459.23s`.
  Warnings were existing Arial glyph and EDF geometry-header warnings.
- `git diff --check` exited `0`.
- Storage report and clean were dry-run only: `30` artifacts, `0` eligible
  bytes, `5` zero-byte legacy entries classified eligible, `7` process-
  referenced entries, `18` younger-than-retention entries, and `0` removed.
  `test_storage.py --apply` was not executed.
- The explicit allowlist checkpoint is created after these results; its commit
  hash is reported in the handoff.

## Known limitations

This task covers only the legacy temperature Figure projection. Structural
frame-count mismatches still fail closed, and the modern temperature provider,
static/strain providers, detector/orientation paths, analysis quality, physical
gates, AI/rescue, publication roles, and human scientific/release review are
unchanged.

## Implementation plan

1. Add a RED regression at the legacy temperature Figure provider boundary for
   one fully unplottable frame.
2. Keep a full-length cleaned-frame slot list, omit only unavailable slots from
   Figure sources, and preserve original source indices in recipe evidence.
3. Run focused provider/consumer tests, the structured verifier, and the exact
   SAXS matrix; inspect the diff and run storage report/clean dry-runs.
4. Record actual evidence and create one explicit allowlist checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_temperature_partial_red'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k unplottable

$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_legacy_temperature_partial_green'
python -m pytest -q tests/test_saxs_temperature_figure_provider.py

python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md --changed --types
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName })
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The SAXS matrix counts as evidence only with a final pytest summary and exit
code `0`. Storage commands remain dry-run; `test_storage.py --apply` is not
part of this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `docs/agent/tasks/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md`
- `docs/superpowers/specs/2026-07-29-saxs-legacy-temperature-figure-partial-frame-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md`
- `docs/acceptance/2026-07-29-saxs-legacy-temperature-figure-partial-frame.md`

## Pre-existing workspace changes

The modified IR/Joint/NMR/scientific-review files, `current-state.md`, staged
or parallel memory work, GUI/editor/release files, `.superpowers/`, and all
pytest/storage/scratch directories are outside this checkpoint and must remain
untouched.
