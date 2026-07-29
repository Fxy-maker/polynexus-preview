---
task_id: 2026-07-29-saxs-1d-review-static-strain-binding
kind: scientific-cross-module
status: completed
date: 2026-07-29
title: Bind SAXS 1D reviewer evidence to static and strain Figures
---

# SAXS 1D reviewer evidence: static and strain

## Goal

Extend the existing `saxs.1d` reviewer evidence binding from temperature to
static and strain Figure provenance without changing scientific or publication
decisions.

## Non-goals

- No new thresholds, fitting rules, quality levels, or physical gates.
- No interpolation, frame repair, source guessing, or reviewer inference.
- No automatic role promotion, AI/rescue execution, or result mutation.
- No `saxs.2d`, GUI review-hint, Workbench text, Manifest, Export, or storage
  deletion changes.

## Affected boundaries

- Existing static and strain `attach_saxs_figure_evidence()` calls.
- Generic SAXS provider mode guard for static/strain only.
- Focused regression tests, task evidence, and durable memory.

## Acceptance criteria

- [x] Static accepted matching review appears as detached strict-JSON evidence.
- [x] Strain accepted matching review appears as detached strict-JSON evidence.
- [x] Missing, invalid, pending, wrong-scope, and partial-source records stay
      fail-closed.
- [x] Existing static/strain Figure roles and source ordering are unchanged.
- [x] Temperature behavior remains covered by the prior task without a second
      projection implementation.
- [x] TDD RED/GREEN, exact SAXS, structured verification, diff, storage dry-run,
      and explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add static and strain RED tests to the existing review-binding regression.
2. Pass the configured review through static and strain provider attachment
   calls and guard the generic provider path by mode.
3. Run focused regressions, the exact SAXS matrix, structured verifier, diff,
   and storage dry-run; record exact results.
4. Create one explicit allowlist checkpoint and leave parallel workspace files
   untouched.

## Verification

```powershell
python scripts/verify.py --task docs/agent/tasks/2026-07-29-saxs-1d-review-static-strain-binding.md --changed --types
$saxsTests = Get-ChildItem tests -Filter 'test_saxs_*.py' | Select-Object -ExpandProperty FullName
python -m pytest -q $saxsTests
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

The complete SAXS matrix is counted only from a final pytest summary and exit
code `0`; old timeout or unrelated full/boundary output is not evidence.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_static.py`
- `polynexus/core/saxs_engine/figure_strain.py`
- `polynexus/core/saxs_engine/figure_provider.py`
- `tests/test_saxs_1d_review_evidence_binding.py`
- `docs/superpowers/specs/2026-07-29-saxs-1d-review-static-strain-binding-design.md`
- `docs/superpowers/plans/2026-07-29-saxs-1d-review-static-strain-binding.md`
- `docs/agent/tasks/2026-07-29-saxs-1d-review-static-strain-binding.md`
- `docs/agent/memory/active-work.md`

## Evidence

- TDD RED was `2 failed, 5 passed`; the failures were the intended missing
  static/strain `scientific_review` handoff. GREEN was `7 passed`.
- Focused static/strain/review/Workbench matrix passed `60 passed in 7.30s`.
- Task-scoped verifier exited `0`: quality `290`, preprocessing `106`, Ruff,
  compile, type baseline, memory/task, and whitespace checks passed.
- Fresh exact SAXS matrix exited `0`: `582 passed, 6 warnings in 392.47s`.
- `git diff --check` exited `0`.
- Storage report/clean remained dry-run: `45` artifacts, `0` eligible bytes,
  `0` removed; no `test_storage.py --apply` was run.

## Current limitations

This task only binds the existing `saxs.1d` reviewer snapshot to static and
strain Figure provenance. It does not change analysis, quality levels,
physical gates, AI/rescue, publication roles, Workbench, Manifest, Export, or
the separate `saxs.2d` binding. Human scientific review and release approval
remain open.
