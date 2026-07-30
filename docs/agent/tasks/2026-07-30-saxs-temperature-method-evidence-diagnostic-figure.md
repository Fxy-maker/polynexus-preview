---
task_id: 2026-07-30-saxs-temperature-method-evidence-diagnostic-figure
kind: scientific-cross-module
status: completed
date: 2026-07-30
title: Expose temperature 1D method evidence as a diagnostic Figure
---

# SAXS temperature method evidence diagnostic Figure

## Goal

Expose existing Porod, Kratky, invariant, and lamellar per-frame evidence in a
temperature diagnostic Figure while preserving every existing quality and
physical boundary.

## Non-goals

- No changes to metric calculations, q/I values, quality levels, thresholds,
  physical gates, rescue, AI, or publication roles.
- No interpolation, frame fabrication, source-index repair, sorting, or new
  scientific classification.
- No changes to production analysis, GUI event logic, real datasets, generated
  outputs, or test storage.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_provider.py`: portable temperature summary
  Figure projection.
- `tests/test_saxs_temperature_figure_provider.py`: focused Figure contract
  coverage.
- Existing Figure validation, V2 adapter, and evidence attachment contracts,
  read-only.

## Implementation plan

1. Add RED tests for all four existing method evidence mappings, including
   missing values and provenance fields.
2. Add a diagnostic-only Figure with detached nullable audit data and finite
   plot data for each supported method.
3. Run focused GREEN, structured verification, exact SAXS verification,
   storage dry-run, diff checks, and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] All four methods are exposed only from existing per-frame evidence.
- [x] Missing values remain explicit and are not interpolated or copied.
- [x] Frame order, temperature, source index, level, and reason codes remain
      auditable.
- [x] The Figure is always diagnostic and strict JSON/V2 valid.
- [x] Verification evidence and the explicit allowlist checkpoint are recorded.

## Verification

The focused RED/GREEN, complete temperature-provider regression, structured
verifier, exact SAXS matrix, storage dry-run, and diff check are required. A
pytest result counts only when it has a complete summary and exit code `0`.

The structured check is `python scripts/verify.py --task
docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md
--changed --types`.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "method_evidence" -o addopts=
python -m pytest -q tests/test_saxs_temperature_figure_provider.py -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The exact SAXS matrix requires a complete pytest summary and exit code `0`.
`test_storage.py --apply` is not authorized for this task.

## Evidence

- TDD RED: `1 failed, 1 passed, 16 deselected`; the expected failure was the
  missing `saxs.series.temperature.method_evidence` definition.
- Focused GREEN: `2 passed, 16 deselected`.
- Temperature Figure provider regression: `18 passed`.
- Structured verifier exited `0`: task/memory checks, Ruff, compile, type
  baseline, quality `296`, preprocessing `106`, and whitespace passed.
- Exact SAXS matrix exited `0`: `651 passed, 6 warnings` in `602.27s`.
- Storage report/clean remained dry-run only: `71` artifacts,
  `16,289,827,301` total bytes, `eligible_bytes=0`, no emergency pressure,
  and `removed=0`. Two paths were protected by a running process; no
  `test_storage.py --apply` was run.
- `git diff --check` passed.

The explicit allowlist checkpoint is the commit created after this final
allowlist audit. Full/boundary release verification, production temperature
figure composition, human scientific review, restarted-GUI review, and final
publication authorization remain open.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_temperature_figure_provider.py`
- `docs/superpowers/specs/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`
- `docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`
- `docs/acceptance/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md`
- `docs/agent/memory/active-work.md`

## Current limitations

This task covers the portable temperature Figure provider only. Production
temperature figure composition, static/strain/2D method-evidence consumers,
human scientific review, restarted-GUI review, and full release gates remain
separate follow-up boundaries.
