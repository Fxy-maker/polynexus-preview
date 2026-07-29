---
kind: task
status: completed
date: 2026-07-29
title: Keep SAXS dirty processed profiles exportable
---

# SAXS export dirty-profile guard

## Goal

Prevent malformed q/I tokens from making the canonical SAXS profile bundle
export fail, while preserving explicit invalid positions and diagnostics.

## Non-goals

- Do not change analysis algorithms, physical thresholds, quality levels,
  rescue/AI behavior, Figure/Manifest contracts, or publication roles.
- Do not delete, sort, interpolate, pad, infer, or repair observations.
- Do not mutate caller-owned arrays, real datasets, scratch, or parallel files.

## Affected boundaries

- `polynexus/core/saxs_export_bundle.py`: canonical/fallback profile CSV export.
- `tests/test_saxs_export_bundle.py`: dirty export regression.
- Task/spec/plan/acceptance and `docs/agent/memory/active-work.md`: evidence.

## Implementation plan

1. Add a RED regression with dirty parallel q/I lists and a canonical
   `ProcessedProfile` containing explicit `NaN` positions.
2. Prefer canonical q in profile items and use existing elementwise coercion for
   export fallback values.
3. Run focused export, SAXS, structured verifier, diff, and storage dry-run
   checks, then create the explicit checkpoint.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_export_dirty_focus'
python -m pytest -q tests/test_saxs_export_bundle.py -k dirty_profile_export
python -m pytest -q tests/test_saxs_export_bundle.py tests/test_saxs_processed_profile.py --basetemp=D:\PolyNexus_saxs_export_dirty_consumers
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-export-dirty-profile-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The exact `tests/test_saxs_*.py` matrix is required when bounded execution
permits; a timeout or missing pytest summary is not a pass.

## Acceptance criteria

- [x] Dirty canonical q/I profiles export with status `ok`.
- [x] CSV keeps all original positions and renders invalid values as empty
      cells rather than dropping rows.
- [x] `provenance.json` retains `quality_status="WARN"` and
      `diagnostics["invalid_numeric_values"]`.
- [x] Clean profile exports remain unchanged and caller inputs are not mutated.
- [x] Focused/SAXS/structured verification and an explicit checkpoint are
      recorded.

## Verification evidence

- TDD RED: `1 failed, 11 deselected`; the failure was the expected export
  status `failed` from whole-array dirty q conversion.
- TDD GREEN: `1 passed, 11 deselected in 0.36s`.
- Export/processed-profile consumer matrix: `17 passed in 0.66s`.
- Fresh real SAXS published-run replay (`-k saxs`) returned `3 passed, 12
  deselected in 81.40s`, exit code `0`, using an external basetemp. Static,
  temperature, and strain lifecycle transport remained green after the export
  change; this is transport evidence, not scientific approval.
- Structured verifier exited `0`: task/memory, Ruff, compile, type baseline,
  quality `287 passed`, preprocessing `106 passed`, and whitespace all passed.
- Exact SAXS matrix: the PowerShell-expanded `test_saxs_*.py` command reached
  the `304` second tool timeout with no pytest final summary (`exit 124`). The
  current run's pytest child was identified as PID `43276` and terminated;
  this matrix is not claimed as passed.
- Test-storage report: dry-run mode, `572` artifacts, `42` eligible, `530`
  protected, and `0` removed. No data was deleted or moved and `--apply` was
  not executed.
- `git diff --check` passed through the structured verifier. The explicit
  allowlist checkpoint was created; its final commit hash is reported in the
  handoff. No push or merge was performed.

## Known limitations

Export now preserves dirty projection positions as empty CSV cells and keeps
the warning diagnostics in JSON provenance, but it does not make the data
scientifically valid. The bounded SAXS matrix had no final summary, so no fresh
full SAXS pass is attributed to this task. Analysis, rescue/AI, physical gates,
and publication approval remain unchanged.

## Explicit changed-file allowlist

- `polynexus/core/saxs_export_bundle.py`
- `tests/test_saxs_export_bundle.py`
- `docs/agent/tasks/2026-07-29-saxs-export-dirty-profile-guard.md`
- `docs/superpowers/specs/2026-07-29-saxs-export-dirty-profile-guard-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-export-dirty-profile-guard.md`
- `docs/acceptance/2026-07-29-saxs-export-dirty-profile-guard.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, `.superpowers/`, historical
pytest/storage directories, GUI/editor drafts, and other parallel files remain
outside this checkpoint.
