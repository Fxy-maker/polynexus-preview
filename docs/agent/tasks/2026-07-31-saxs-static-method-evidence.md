---
task_id: 2026-07-31-saxs-static-method-evidence
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Expose static 1D method evidence as a diagnostic Figure
---

# SAXS static method evidence diagnostic Figure

## Goal

Add an auditable static SAXS Figure projection for existing Porod, Kratky,
invariant, and lamellar per-frame `MetricEvidence`.

## Non-goals

- No changes to the four metric algorithms or their physical checks.
- No new thresholds, quality reclassification, frame rescue, interpolation,
  source repair, publication promotion, AI invocation, or GUI changes.
- No changes to the parallel SAXS EDF metadata-quality files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_static.py`: static diagnostic Figure
  projection.
- `tests/test_saxs_static_figure_panels.py`: focused Figure contract coverage.
- Existing Figure validation, V2 adapter, evidence attachment, Manifest, and
  Export contracts are read-only consumers.

## Implementation plan

1. Add RED tests for four existing method-evidence mappings, including missing
   values, non-finite values, and provenance fields.
2. Add a diagnostic-only Figure with detached nullable audit data and finite
   plot data for each supported method.
3. Run focused GREEN, structured verification, exact SAXS verification,
   storage dry-run, diff checks, and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] `saxs.static.method_evidence` is emitted only when existing supported
  per-frame metric evidence exists.
- [x] Four method audit sources preserve nullable values, frame index, source
  path, level, and reason codes.
- [x] Each emitted plot source contains only finite existing pairs; methods
  with no finite pair remain audit-only rather than producing an empty source.
- [x] The Figure is diagnostic, strict JSON-safe, v2-valid, and detached from
  mutable input values.
- [x] Existing static Figure tests pass unchanged when no evidence is supplied.

## Verification

The focused RED/GREEN, complete static-provider regression, structured
verifier, exact SAXS matrix, storage dry-run, and diff check are required. A
pytest result counts only when it has a complete summary and exit code `0`.

The structured check is:

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md --changed --types
```

The exact SAXS matrix also requires a complete pytest summary and exit code
`0`. `test_storage.py --apply` is not authorized for this task.

## Verification commands

```powershell
python -m pytest -q tests/test_saxs_static_figure_panels.py -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md --changed --types
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Sort-Object FullName | Select-Object -ExpandProperty FullName) -o addopts=
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

## Evidence

- TDD RED: `1 failed, 1 passed, 3 deselected`; the missing Figure definition
  caused the expected `StopIteration`.
- Focused GREEN: `2 passed, 3 deselected`.
- Static Figure/figure-evidence/publication regression: `54 passed in 58.98s`.
  The first run exposed an empty-renderer-source V2 fallback; the final run
  passed after keeping audit-only methods free of empty plot sources.
- Task verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md --changed --types`
  exited `0`; quality `297 passed`, preprocessing `106 passed`, Ruff,
  compile, type baseline, task/memory, and whitespace checks passed.
- Exact SAXS matrix exited `0`: `667 passed, 6 warnings in 467.96s`.
- Storage report and dry-run clean both exited `0`: `62` artifacts,
  `eligible_bytes=0`, `emergency=true`, `removed=0`, and no apply was run.
- `git diff --check` passed.

The checkpoint hash is recorded after the final allowlist audit. No push,
merge, or data cleanup apply was performed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_static.py`
- `tests/test_saxs_static_figure_panels.py`
- `docs/superpowers/specs/2026-07-31-saxs-static-method-evidence-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-static-method-evidence.md`
- `docs/agent/tasks/2026-07-31-saxs-static-method-evidence.md`
- `docs/acceptance/2026-07-31-saxs-static-method-evidence.md`

## Known limitations

This task projects existing evidence only. Scientific interpretation of method
agreement, sequence rescue, 2D evidence, and human publication authorization
remain separate review gates.
