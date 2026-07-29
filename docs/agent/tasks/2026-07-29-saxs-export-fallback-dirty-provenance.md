---
kind: task
status: completed
date: 2026-07-29
title: Preserve dirty diagnostics in SAXS export fallback
---

# SAXS export fallback dirty-provenance

## Goal

Make legacy SAXS export fallback profiles retain explicit q/I conversion
diagnostics when no canonical `ProcessedProfile` is available.

## Non-goals

- Do not change analysis output, `DataQualityReport`, scientific levels,
  physical thresholds, rescue/AI behavior, or publication roles.
- Do not mutate analysis arrays or existing diagnostics.
- Do not delete, sort, interpolate, pad, infer, or repair observations.
- Do not edit real data, `current-state.md`, GUI/editor files, or scratch.

## Affected boundaries

- `polynexus/core/saxs_export_bundle.py`: fallback profile provenance.
- `tests/test_saxs_export_bundle.py`: fallback dirty regression.
- Task/spec/plan/acceptance and `docs/agent/memory/active-work.md`.

## Implementation plan

1. Write RED for legacy analysis fallback with dirty q/raw arrays.
2. Merge elementwise conversion counts into a detached export diagnostics map
   and set profile `WARN` only for newly observed conversion failures.
3. Run focused export, exact SAXS, structured verifier, diff, and storage
   dry-run checks; record bounded limitations and create the checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_export_fallback_dirty_focus'
python -m pytest -q tests/test_saxs_export_bundle.py -k fallback_dirty_provenance
python -m pytest -q tests/test_saxs_export_bundle.py tests/test_saxs_processed_profile.py --basetemp=D:\PolyNexus_saxs_export_fallback_dirty_consumers
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-export-fallback-dirty-provenance.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The exact `test_saxs_*.py` matrix is attempted with an external basetemp; no
summary or a timeout is recorded as a limitation, never as a pass.

## Acceptance criteria

- [x] Fallback dirty q/raw export succeeds without mutating inputs.
- [x] CSV keeps positions and invalid cells empty.
- [x] Fallback provenance records `quality_status="WARN"` and
      `diagnostics["invalid_numeric_values"]` for conversion failures.
- [x] Clean fallback profile provenance remains unchanged.
- [x] Focused/structured verification and explicit checkpoint are recorded.

## Verification evidence

- TDD RED: `1 failed, 12 deselected`; the fallback bundle succeeded but lacked
  the expected `WARN` and invalid-value diagnostics.
- TDD GREEN: `2 passed, 11 deselected in 0.26s`.
- Export/processed-profile consumer matrix: `18 passed in 0.53s`.
- Exact SAXS matrix: `533 passed, 6 warnings in 295.48s`, exit code `0`. The
  warnings are existing Arial glyph and EDF geometry-header warnings.
- Structured verifier exited `0`: task/memory, Ruff, compile, type baseline,
  quality `287 passed`, preprocessing `106 passed`, and whitespace all passed.
- Test-storage report: dry-run mode, `282` artifacts, `40` eligible, `242`
  protected, and `0` removed. No data was deleted or moved; `--apply` was not
  executed.
- `git diff --check` passed. The explicit allowlist checkpoint was created; its
  final commit hash is reported in the handoff. No push or merge was performed.

## Known limitations

Fallback provenance makes conversion failures auditable but does not make the
curve scientifically valid. No analysis, quality gate, physical threshold,
rescue/AI behavior, or publication decision changed. Human scientific, GUI,
and release review remain separate from this automated export evidence.

## Explicit changed-file allowlist

- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- `docs/agent/tasks/2026-07-29-saxs-export-fallback-dirty-provenance.md`
- `docs/superpowers/specs/2026-07-29-saxs-export-fallback-dirty-provenance-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-export-fallback-dirty-provenance.md`
- `docs/acceptance/2026-07-29-saxs-export-fallback-dirty-provenance.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, historical pytest/storage
directories, `.superpowers/`, GUI/editor drafts, and other parallel files stay
outside this checkpoint.
