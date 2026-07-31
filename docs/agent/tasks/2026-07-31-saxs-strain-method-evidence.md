---
task_id: 2026-07-31-saxs-strain-method-evidence
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Expose strain 1D method evidence as a diagnostic Figure
---

# SAXS strain method evidence diagnostic Figure

## Goal

Add a diagnostic strain SAXS Figure that projects existing per-frame Porod,
Kratky, invariant, and lamellar `MetricEvidence` without changing scientific
authority.

## Non-goals

- No changes to metric algorithms, strain phase inference, thresholds, quality
  levels, physical gates, rescue, AI, or publication semantics.
- No interpolation, padding, frame fabrication, source repair, or frame
  reordering.
- No detector, orientation, EDF, GUI, Manifest schema, Export, or parallel
  worktree changes.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: diagnostic projection.
- `tests/test_saxs_strain_method_evidence.py`: focused Figure contract tests.
- Existing Figure validation, V2 adapter, evidence attachment, Manifest, and
  Export contracts are read-only consumers.

## Implementation plan

1. Add RED tests for four strain method mappings, missing/non-finite values,
   frame identity, source paths, and V2-safe renderer behavior.
2. Add a diagnostic-only strain Figure using existing frame conditions and
   detached nullable audit sources; omit renderer sources with fewer than two
   finite pairs.
3. Run focused GREEN, structured verification, exact SAXS verification,
   storage dry-run, diff checks, and create one explicit allowlist checkpoint.

## Acceptance criteria

- [x] `saxs.strain.method_evidence` is emitted only when supported existing
  per-frame metric evidence exists.
- [x] Four audit sources preserve nullable values, strain, frame index, source
  path, level, and reason codes.
- [x] Emitted plot sources contain only finite existing pairs and have at least
  two points; audit-only methods do not create empty renderers.
- [x] The Figure is diagnostic, strict JSON-safe, V2-valid when renderable,
  and detached from mutable input evidence.
- [x] Existing strain Figure tests pass unchanged when no evidence is supplied.

## Verification

The focused RED/GREEN, strain provider/evidence regression, structured
verifier, exact SAXS matrix, storage dry-run, and diff check are required. A
pytest result counts only with a complete final summary and exit code `0`.

```powershell
python -m pytest -q tests/test_saxs_strain_method_evidence.py -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-strain-method-evidence.md --changed --types
python -m pytest -q (Get-ChildItem -Path tests -Filter 'test_saxs_*.py' | Sort-Object FullName | Select-Object -ExpandProperty FullName) -o addopts=
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
git diff --check
```

`test_storage.py --apply` is not authorized. Full/boundary release verification
and human scientific review remain separate gates.

## Evidence

- TDD RED: `1 failed, 1 passed`; the expected failure was the missing
  `saxs.strain.method_evidence` definition.
- Focused GREEN: `2 passed in 0.41s`.
- Strain/evidence regression: `50 passed in 14.20s`.
- Structured verifier:
  `python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-strain-method-evidence.md --changed --types`
  exited `0`; Ruff, compile, type baseline, quality `297 passed`,
  preprocessing `106 passed`, memory/task, and whitespace checks passed.
- Exact SAXS matrix exited `0`: `669 passed, 6 warnings in 532.41s`.
- Storage report exited `0` with `64` artifacts and `eligible_bytes=0` while
  the matrix was active. The subsequent clean dry-run exited `0` with
  `Eligible: 7873 bytes`, `Cleanup failures: 0`, and `removed=0` after the
  process released its references. No `--apply` was run.
- `git diff --check` passed through the structured verifier.

The checkpoint hash is recorded after the final allowlist audit. No push,
merge, directory deletion, or scientific publication approval was performed.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_strain_method_evidence.py`
- `docs/superpowers/specs/2026-07-31-saxs-strain-method-evidence-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-strain-method-evidence.md`
- `docs/agent/tasks/2026-07-31-saxs-strain-method-evidence.md`
- `docs/acceptance/2026-07-31-saxs-strain-method-evidence.md`

## Known limitations

This task projects existing strain evidence only. It does not establish
method agreement, detector calibration, orientation meaning, AI rescue, or
publication authorization.
