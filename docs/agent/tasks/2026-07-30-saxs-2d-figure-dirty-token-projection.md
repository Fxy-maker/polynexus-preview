---
kind: task
status: completed
date: 2026-07-30
title: Recover malformed tokens in SAXS 2D Figure projections
---

# SAXS 2D Figure dirty-token projection

## Goal

Make detector pixels and azimuthal chi/I Figure projections recoverable when
individual source tokens are malformed, while preserving existing physical
and publication semantics.

## Non-goals

- No changes to detector quality reports, anisotropy/orientation analysis,
  masks, saturation, geometry, thresholds, or physical gates.
- No interpolation, padding, replacement, reordering, frame fabrication,
  AI call, or rescue decision.
- No changes to the existing `complete`/`partial_nonfinite` provenance
  contract except that malformed tokens are counted as non-finite after
  elementwise projection.
- No edits to real datasets, generated outputs, scratch, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_detector.py`: shared static/temperature
  detector-image projection.
- `polynexus/core/saxs_engine/figure_strain.py`: strain detector and
  azimuthal chi/I projections.
- `tests/test_saxs_detector_figure_modes.py`: malformed detector token
  regression through the shared detector provider.
- `tests/test_saxs_figure_evidence_binding.py`: malformed detector and
  azimuthal token regressions through the strain provider.

## Acceptance criteria

- [x] A malformed sampled detector pixel is omitted while other finite pixels
  and their coordinates remain available.
- [x] A malformed chi or intensity token omits only its aligned pair.
- [x] Existing sampled/pair counts report malformed tokens as non-finite and
  preserve `partial_nonfinite`.
- [x] All-invalid and malformed-shape inputs retain their existing fail-closed
  behavior.
- [x] Existing analysis results, physical metrics, quality levels, roles, and
  strict JSON serialization remain unchanged.
- [x] Focused, structured, SAXS, storage dry-run, diff, and allowlist evidence
  is recorded before checkpoint.

## Implementation plan

1. Add detector and azimuthal malformed-token regressions and confirm RED.
2. Route detector pixels and azimuthal chi/I through the existing elementwise
   numeric projection helper, then confirm GREEN without changing filters or
   provenance fields.
3. Run focused, structured, SAXS, storage, diff, and allowlist verification.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_2d_dirty_token_focus'
python -m pytest -q tests/test_saxs_detector_figure_modes.py tests/test_saxs_figure_evidence_binding.py
python scripts/verify.py --task docs/agent/tasks/2026-07-30-saxs-2d-figure-dirty-token-projection.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The fresh SAXS matrix must use an external basetemp and counts as passing only
with a fresh pytest summary and exit code `0`. `test_storage.py --apply` is not
permitted.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_detector.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `tests/test_saxs_detector_figure_modes.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `docs/agent/tasks/2026-07-30-saxs-2d-figure-dirty-token-projection.md`
- `docs/superpowers/specs/2026-07-30-saxs-2d-figure-dirty-token-projection-design.md`
- `docs/superpowers/plans/2026-07-30-saxs-2d-figure-dirty-token-projection.md`
- `docs/acceptance/2026-07-30-saxs-2d-figure-dirty-token-projection.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, existing checkpoint files,
historical pytest/storage directories, `.superpowers/`, `tests/_tmp_phase3/`,
and all other untracked or parallel files remain outside this task checkpoint.

## Verification evidence

- TDD RED: `3 failed, 5 passed, 33 deselected` on the new malformed-token
  selector; failures were the expected whole-array conversion boundary.
- Focused GREEN: `41 passed in 12.96s`.
- Structured verifier: exit `0`; task/memory checks, Ruff, compile, type
  baseline, quality `290 passed`, preprocessing `106 passed`, whitespace, and
  `git diff --check` passed.
- Fresh SAXS matrix: `593 passed, 6 warnings in 392.11s (0:06:32)`, exit code
  `0`. Warnings are the existing Arial glyph and EDF geometry-header warnings.
- Storage remained dry-run only: `54` artifacts, `14367454080` bytes,
  `eligible_bytes=0`; the final clean report showed `Eligible: 0 bytes` and
  `Cleanup failures: 0`. No `test_storage.py --apply` ran and no directories
  were removed or migrated.
- The latest post-`765bda3` full/boundary attempt remains a historical
  `1504.1s` timeout with no final summary; it is not attributed to this task.
- Explicit allowlist implementation checkpoint: `d480ac3`; no push or merge
  was performed.
