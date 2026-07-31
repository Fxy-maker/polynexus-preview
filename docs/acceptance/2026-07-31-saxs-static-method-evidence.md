---
kind: acceptance
status: accepted-automated
date: 2026-07-31
title: SAXS static method evidence diagnostic Figure
---

# SAXS Static Method Evidence Diagnostic Figure Acceptance

## Scope

The static SAXS Figure provider now projects existing per-frame Porod, Kratky,
invariant, and lamellar `MetricEvidence` into
`saxs.static.method_evidence`. Each method retains a nullable audit source with
frame index, value, source path, level, and reason codes. A finite plot source
is emitted only when that method has at least one finite existing pair; an
audit-only method never creates an empty renderer source.

The Figure remains diagnostic and does not recalculate, reclassify, repair,
interpolate, promote, or invoke AI/rescue behavior.

## Evidence

- TDD RED: `1 failed, 1 passed, 3 deselected`; the missing Figure definition
  caused the expected `StopIteration`.
- Focused GREEN: `2 passed, 3 deselected`.
- Static Figure/figure-evidence/publication regression initially exposed one
  v2 fallback caused by empty plot sources; after the fail-closed fix the final
  matrix was `54 passed in 58.98s`.
- Task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md --changed --types`
  exited `0`; task/memory checks, Ruff, compile, type baseline, quality
  `297 passed`, preprocessing `106 passed`, and whitespace passed.
- Exact SAXS matrix:
  `python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Sort-Object FullName | Select-Object -ExpandProperty FullName) -o addopts=`
  exited `0` with `667 passed, 6 warnings in 467.96s`.
- Warnings are existing Arial CJK glyph warnings and existing SAXS geometry
  default warnings; they did not fail the matrix.
- `git diff --check` passed during the focused verification sequence.
- Storage report and dry-run cleanup both exited `0`: `62` artifacts,
  `eligible_bytes=0`, emergency pressure was reported as `true`, and
  `removed=0`. Ten legacy paths were listed as emergency-eligible but had
  zero eligible bytes; no test directory or real data was deleted or moved.
  `test_storage.py --apply` was not run.

## Release boundaries

This is automated static evidence projection only. It does not authorize
publication, scientific interpretation of method agreement, sequence rescue,
2D/strain consumers, AI execution, GUI review, or full/boundary release sign-
off.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_static.py`
- `tests/test_saxs_static_figure_panels.py`
- `docs/superpowers/specs/2026-07-31-saxs-static-method-evidence-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-static-method-evidence.md`
- `docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md`
- `docs/acceptance/2026-07-31-saxs-static-method-evidence.md`
