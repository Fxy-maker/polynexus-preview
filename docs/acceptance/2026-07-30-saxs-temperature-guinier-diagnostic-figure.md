# SAXS Temperature Guinier Diagnostic Figure Acceptance

## Scope

The temperature SAXS Figure provider now emits a dedicated
`saxs.series.temperature.guinier` diagnostic definition when the existing
`TempSeriesResult` contains `Rg_array`. The figure is an evidence review
surface only. It does not recalculate Guinier, change quality levels, infer a
phase transition, interpolate missing frames, or promote a publication role.

## Evidence

- TDD RED:
  `python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "guinier_diagnostic" -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-red`
  -> `1 failed, 15 deselected`, with the expected `StopIteration` for the
  missing Figure definition.
- Focused GREEN:
  `python -m pytest -q tests/test_saxs_temperature_figure_provider.py -k "guinier_diagnostic or temperature_provider" -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-green3`
  -> `6 passed, 10 deselected`.
- Full temperature provider regression:
  `python -m pytest -q tests/test_saxs_temperature_figure_provider.py -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-focused`
  -> `16 passed`.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-temperature-guinier-diagnostic-figure.md --changed --types`
  -> task/memory checks, Ruff, compile, type baseline, quality `294`,
  preprocessing `106`, and whitespace passed; exit code `0`.
- Exact SAXS matrix:
  `python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Sort-Object FullName | Select-Object -ExpandProperty FullName) -o addopts= --basetemp=D:\PolyNexus-test-runs\pytest\saxs-temperature-guinier-diagnostic-saxs-matrix`
  -> `649 passed, 6 warnings in 543.62s (0:09:03)`, exit code `0`.
- Storage report/dry-run:
  `report --json` found `62` artifacts, total `15,806,654,463` bytes,
  `eligible_bytes=0`, and no emergency pressure. `clean --older-than-hours
  24` remained dry-run; no deletion or migration occurred and `--apply` was
  not run.
- `git diff --check` passed.

## Release Boundaries

This records automated Figure-contract evidence only. Full/boundary release,
restarted-GUI review, real-detector scientific interpretation, and final
publication authorization remain separate open gates.
