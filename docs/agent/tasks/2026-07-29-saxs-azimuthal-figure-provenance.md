---
kind: task
status: completed
date: 2026-07-29
title: Explain partial SAXS azimuthal Figure recovery
---

# SAXS azimuthal Figure projection provenance

## Goal

Make partial azimuthal chi/I Figure recovery explicit without changing
orientation analysis or scientific evidence semantics.

## Non-goals

- No change to `analyze_anisotropy()`, Herman metrics, axis detection, detector
  quality, masks, saturation, geometry, thresholds, or publication roles.
- No interpolation, padding, value replacement, frame fabrication, AI call, or
  rescue decision.
- No edits to real data, generated outputs, scratch, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_strain.py`: azimuthal Figure recipe only.
- `tests/test_saxs_figure_evidence_binding.py`: focused chi/I regression.

## Acceptance criteria

- [x] Mixed finite/non-finite aligned chi/I pairs record input, retained, and
  non-finite counts with `partial_nonfinite` status.
- [x] Fully finite pairs record `complete` status.
- [x] Counts are keyed by existing frame index, detached, and strict JSON-safe.
- [x] Empty/all-invalid traces remain omitted with no fabricated evidence.
- [x] Existing orientation and Figure consumer tests remain green.
- [x] Structured, SAXS, storage, diff, and allowlist evidence is recorded.

## Implementation plan

1. Add the mixed chi/I provenance regression and run it RED. [x]
2. Add deterministic count metadata to the existing azimuthal Figure recipe. [x]
3. Run focused and structured verification, then fresh SAXS and storage
   dry-runs. [x]
4. Create one explicit allowlist checkpoint without touching parallel changes. [x]

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_azimuthal_provenance_focus'
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_publication_pack_upgrade.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-azimuthal-figure-provenance.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The SAXS matrix uses an external basetemp and a PowerShell-expanded file list;
only a fresh pytest summary with exit code `0` counts as passing. Do not run
`test_storage.py --apply`.

## Evidence recorded

- TDD RED: the mixed-pair regression failed with `KeyError:
  'azimuthal_projection_quality'`; the clean-pair regression failed at the
  same missing recipe field.
- Focused GREEN and Figure/orientation matrix: `59 passed`.
- Structured verifier: quality `287 passed`, preprocessing `106 passed`;
  Ruff, compile, task/memory, and whitespace checks passed.
- Fresh SAXS matrix: `545 passed, 6 warnings` in `289.88s`, exit code `0`.
- Independent current-thread recheck with an external D: basetemp: `545
  passed, 6 warnings in 344.71s`, exit code `0`.
- Storage report/clean dry-run: `350 artifacts`; latest clean JSON reported
  `57 eligible`, `9 referenced by a running process`, and `284 younger than
  retention`; all artifacts had `removed=false`. No `--apply` command ran.
- Scope/diff audit: the implementation and test changes are limited to the
  explicit allowlist below; pre-existing parallel files remain untouched.

## Scientific boundary

The provenance describes only the finite-pair projection used to build the
azimuthal Figure data source. It is not a detector-wide quality assessment,
orientation validity decision, publication approval, interpolation/rescue
decision, or substitute for existing SAXS physical gates.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-29-saxs-azimuthal-figure-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-azimuthal-figure-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-azimuthal-figure-provenance.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, `tests/test_test_storage.py`,
historical pytest/storage directories, `.superpowers/`, and all other parallel
or untracked files remain outside this checkpoint.
