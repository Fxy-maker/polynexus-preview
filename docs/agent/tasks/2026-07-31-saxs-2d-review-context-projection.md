---
task_id: 2026-07-31-saxs-2d-review-context-projection
kind: scientific-cross-module
status: completed
date: 2026-07-31
title: Project SAXS 2D detector/orientation reviewer context
---

# SAXS 2D reviewer context projection

## Goal

Expose existing 2D detector, geometry/mask, beam-center, orientation, gate,
and scientific-review evidence as one detached DTO for review consumers.

## Non-goals

- no new q/I or detector processing;
- no geometry, mask, beam-center, orientation, or physical threshold;
- no interpolation, imputation, frame repair, source inference, AI call,
  candidate execution, rerun, or publication authorization;
- no change to Figure/Manifest/Export/History semantics;
- no edits to real data, generated outputs, storage, scratch, or parallel
  memory/worktree files.

## Affected boundaries

- `polynexus/core/saxs_engine/saxs_2d_review_context.py`: pure DTO adapter;
- `polynexus/core/saxs_engine/__init__.py`: public export;
- `polynexus/gui/result_table_models.py`: defaulted presentation field;
- `polynexus/gui/saxs_results_table_service.py`: DTO consumption only;
- `tests/test_saxs_2d_review_context.py`: focused contract and consumer tests.

## Acceptance criteria

- [ ] Complete existing detector/orientation evidence is projected without
  recalculation and remains strict JSON-safe and detached.
- [ ] Geometry, mask, and beam-center states preserve existing provenance and
  missing/invalid status without fabricated values.
- [ ] Existing quality/physical gate evidence is visible as summary evidence,
  with `Diagnostic`, `Unusable`, and `not_assessed` states retained.
- [ ] Scientific review is projected with expected scope `saxs.2d` and
  fail-closed missing, invalid, scope-mismatch, and source-mismatch reasons.
- [ ] q/I arrays, detector pixels, source paths, and unknown raw fields never
  enter the DTO.
- [ ] Workbench presentation carries the DTO without changing existing text,
  rows, risk ordering, or review persistence.
- [ ] TDD RED/GREEN, focused/SAXS/task verification, diff check, storage
  dry-run, and an explicit allowlist checkpoint are recorded.

## Implementation plan

1. Add RED tests for complete 2D projection, fail-closed missing/invalid
   evidence, review scope/source matching, raw-data exclusion, and Workbench
   DTO compatibility.
2. Implement the pure core adapter with fixed allowlists and reuse the existing
   scientific-review decision contract.
3. Export the adapter and attach its detached result to the defaulted Workbench
   presentation field without changing existing text or table behavior.
4. Run the focused tests, the complete SAXS matrix, the structured verifier,
   storage dry-runs, and the explicit allowlist checkpoint.

## Verification

```powershell
python -m pytest -q tests/test_saxs_2d_review_context.py tests/test_saxs_2d_detector_orientation_evidence.py tests/test_saxs_2d_evidence_propagation.py tests/test_saxs_2d_review_evidence_binding.py tests/test_saxs_2d_review_consumer_propagation.py tests/test_saxs_workbench_detector_provenance_audit.py -o addopts=
python -m pytest -q (Get-ChildItem tests -Filter 'test_saxs_*.py' | ForEach-Object { $_.FullName }) -o addopts=
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-2d-review-context-projection.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The SAXS matrix and verifier require a complete summary and exit code `0`.
Storage commands are dry-run only; `test_storage.py --apply` is not allowed.

## Verification policy

Only complete pytest summaries with exit code `0` count as pass evidence. A
timeout, collection error, crash, or live process without a summary is recorded
as incomplete. `scripts/test_storage.py report` and dry-run `clean` are
allowed; `test_storage.py --apply` is not part of this task.

## Evidence

- TDD RED: collection failed with `ModuleNotFoundError` for the not-yet-created
  `polynexus.core.saxs_engine.saxs_2d_review_context` module.
- Initial GREEN exposed two implementation defects: direct mappings did not
  expose top-level review/audit fields, and invalid serialized review records
  could raise during detached projection. Both were fixed at the adapter
  boundary; the tests were kept strict. The `saxs.1d` mismatch fixture was
  completed with its existing required decision keys.
- Core GREEN: `6 passed in 0.26s`, exit code `0`.
- Workbench plus adjacent review regression: `31 passed in 2.97s`, exit code
  `0`.
- Targeted Ruff and compile checks passed; adjacent 2D detector/orientation,
  propagation, review-binding, consumer, Workbench audit, and new-context
  regression passed `58 passed in 3.45s`, exit code `0`.
- Fresh SAXS file matrix: `700 passed, 6 warnings in 591.30s`, exit code `0`.
  Warnings are existing font glyph and EDF-header geometry fallback warnings;
  no test failure occurred.
- Task-scoped structured verifier exited `0`: task-check and memory check,
  Ruff, compile, type baseline, whitespace, quality `297 passed`, and
  preprocessing `106 passed` all passed.
- Final storage report and dry-run clean exited `0`: `142` artifacts,
  `28,835,126,572` total bytes, `15,743,185,346` eligible bytes,
  `0` emergency-eligible bytes, and `0` failures. No artifact was removed and
  no `test_storage.py --apply` was executed.
- `git diff --check` exited `0`. The pre-existing shared full/boundary process
  remains outside this task; its intermediate state is not evidence.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/saxs_2d_review_context.py`
- `polynexus/core/saxs_engine/__init__.py`
- `polynexus/gui/result_table_models.py`
- `polynexus/gui/saxs_results_table_service.py`
- `tests/test_saxs_2d_review_context.py`
- `docs/superpowers/specs/2026-07-31-saxs-2d-review-context-projection-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-2d-review-context-projection.md`
- `docs/agent/tasks/2026-07-31-saxs-2d-review-context-projection.md`

Parallel `docs/agent/memory/`, `pytest.ini`, scratch, test-storage, real-data,
and generated-output changes remain outside this checkpoint.
