---
kind: task
status: completed
date: 2026-07-29
title: Guard SAXS ProcessedProfile projection against dirty numeric tokens
---

# SAXS ProcessedProfile dirty-input guard

## Goal

Keep the read-only processed-profile projection usable when individual q,
intensity, or derived-layer tokens cannot be converted to floats, while making
the degradation explicit.

## Non-goals

- Do not change SAXS analysis algorithms, quality gates, physical thresholds,
  evidence levels, rescue, AI behavior, or publication roles.
- Do not delete, sort, interpolate, pad, infer, or copy observations.
- Do not alter caller-owned arrays, real datasets, generated outputs, GUI/editor
  work, or parallel task files.

## Affected boundaries

- `polynexus/core/saxs_engine/processed_profile.py`: canonical read-only
  projection and layer diagnostics.
- `polynexus/core/saxs.py`: payload-to-projection q/raw boundary.
- `tests/test_saxs_processed_profile.py`: focused regression coverage.
- Task/spec/plan/acceptance and `docs/agent/memory/active-work.md`: durable
  evidence only.

## Implementation plan

1. Add RED tests for malformed tokens in every processed-profile numeric layer,
   q/raw payload conversion, position preservation, diagnostics, status, and
   input immutability.
2. Add one private elementwise numeric coercion helper and use it in the
   canonical projection plus the payload q/raw boundary.
3. Run the focused GREEN tests, exact SAXS matrix, structured verifier, diff
   check, and test-storage dry-run; record exact summaries or limitations.
4. Update durable evidence and create one explicit allowlist checkpoint without
   touching the existing parallel worktree changes.

## Verification

```powershell
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_processed_profile_dirty_focus'
python -m pytest -q tests/test_saxs_processed_profile.py
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-processed-profile-dirty-input-guard.md --changed --types
git diff --check
python scripts/test_storage.py report --json
```

The exact SAXS matrix uses an external basetemp and its result is recorded only
when pytest provides a final summary and exit code. The authoritative rerun
used `D:\PolyNexus_saxs_processed_profile_dirty_saxs_matrix_current` and
returned `531 passed, 6 warnings in 205.58s`, exit code `0`.

## Acceptance criteria

- [x] Every processed numeric layer tolerates malformed tokens without raising.
- [x] Failed conversions remain `NaN` at their original positions and preserve
      array shape/length.
- [x] `diagnostics["invalid_numeric_values"]` records each affected layer and
      its count.
- [x] Any invalid token sets `quality_status="WARN"`; clean input remains
      `"OK"`.
- [x] Payload projection tolerates dirty q/raw and optional layers without
      mutating input or changing existing length diagnostics.
- [x] Focused tests, SAXS matrix, structured verification, diff check, and an
      explicit allowlist checkpoint are recorded.

## Verification evidence

- TDD RED: `2 failed, 3 passed in 0.70s`; both failures reproduced the existing
  whole-array conversion exceptions for dirty projection data.
- TDD GREEN: `5 passed in 0.13s`; the clean projection and static publication
  regressions remained green.
- Focused Ruff and compile checks passed before the structured verifier.
- Structured verifier passed with exit code `0`: task/memory checks, Ruff,
  compile, type baseline, quality `287 passed in 6.55s`, preprocessing `106
  passed in 1.73s`, and whitespace all passed.
- Earlier SAXS matrix attempt: the PowerShell-expanded `test_saxs_*.py`
  command reached the `184` second tool timeout (`exit 124`) without a pytest
  final summary; it is not counted as evidence. The child process was checked
  afterward and was no longer running.
- Authoritative SAXS matrix rerun: all `tests/test_saxs_*.py` files returned
  `531 passed, 6 warnings in 205.58s`, exit code `0`, using the external
  basetemp above.
- Latest `python scripts/test_storage.py report --json`: dry-run, `566`
  artifacts, `340` eligible, `226` protected, `0` removed; C: `306`
  artifacts, `298` eligible, `108754786772` eligible bytes. The cleanup
  command was also dry-run; no test directory was deleted or moved, and
  `--apply` was not run.
- `git diff --check` passed through the structured verifier. The explicit
  allowlist checkpoint was created; its final commit hash is reported in the
  handoff. No push or merge was performed.

## Known limitations

This change only hardens the read-only processed-profile projection. `NaN`
observations remain explicit and are not repaired; downstream analysis and its
existing physical/quality gates decide applicability. Scientific review,
AI/rescue acceptance, publication authorization, and GUI review remain outside
this task.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/processed_profile.py`
- `polynexus/core/saxs.py`
- `tests/test_saxs_processed_profile.py`
- `docs/agent/tasks/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
- `docs/superpowers/specs/2026-07-29-saxs-processed-profile-dirty-input-guard-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
- `docs/acceptance/2026-07-29-saxs-processed-profile-dirty-input-guard.md`
- `docs/agent/memory/active-work.md`

## Pre-existing workspace changes

The modified `docs/agent/memory/current-state.md`, `.superpowers/`, historical
pytest/storage directories, GUI/editor drafts, and all other untracked or
parallel files remain untouched and outside this checkpoint.
