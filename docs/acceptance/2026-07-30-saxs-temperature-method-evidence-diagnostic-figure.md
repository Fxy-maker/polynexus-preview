# SAXS Temperature Method Evidence Diagnostic Figure Acceptance

## Scope

The portable temperature SAXS Figure provider now emits
`saxs.series.temperature.method_evidence` when existing per-frame Porod,
Kratky, invariant, or lamellar evidence is present. It keeps a nullable audit
source for each supported method and a separate finite-value renderer source.
The Figure is always diagnostic and does not recalculate or reclassify any
scientific result.

## Evidence

- TDD RED: `1 failed, 1 passed, 16 deselected`; the expected missing Figure
  definition caused the failure.
- Focused GREEN: `2 passed, 16 deselected`.
- Full temperature Figure provider: `18 passed`.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-temperature-method-evidence-diagnostic-figure.md --changed --types`
  exited `0`; task/memory checks, Ruff, compile, type baseline, quality `296`,
  preprocessing `106`, and whitespace passed.
- Exact SAXS matrix:
  `python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Sort-Object FullName | Select-Object -ExpandProperty FullName) -o addopts= --basetemp=D:/PolyNexus-test-runs/pytest/saxs-temperature-method-evidence-saxs-matrix`
  exited `0` with `651 passed, 6 warnings in 602.27s`.
- Storage report/clean:
  `71` artifacts, `16,289,827,301` total bytes, `eligible_bytes=0`, no
  emergency pressure, and `removed=0`; both commands were non-destructive
  dry-runs and `test_storage.py --apply` was not run.
- `git diff --check` passed.
- Explicit allowlist checkpoint: `b994a91`; no push or merge was performed.

## Release Boundaries

This is automated evidence-projection acceptance only. Production temperature
figure composition, static/strain/2D method-evidence consumers, full/boundary
release verification, human scientific interpretation, restarted-GUI review,
and final publication authorization remain separate open gates.
