---
kind: task
status: completed
date: 2026-07-28
title: Continue SAXS condition recovery after invalid path candidates
---

# SAXS condition path-candidate recovery

## Goal

Make path-based SAXS condition recovery continue through all directory
components when an earlier component matches a pattern but fails numeric
conversion or its validator, so a later valid condition directory is still
published with its provenance metadata.

## Root-cause evidence

The existing failing tests construct a path below a pytest basetemp directory.
The `temp_directory_label` pattern first matches the ancestor name
`...basetemp_20260730`, captures an out-of-range value, and then stops scanning
the path. The later `temperature_180` component is never considered. The
scanner already copies `recover_condition_axis()`'s source, source key, and
confidence into `ExperimentCondition.metadata`; the missing metadata is a
downstream symptom of the unresolved recovery result.

## Non-goals

- Do not change condition precedence: context and header still outrank paths.
- Do not change pattern order, validators, numeric semantics, confidence
  values, unresolved keys, grouping, or condition labels.
- Do not parse generated output trees, edit GUI code, modify real datasets, or
  introduce inferred/scientific values.

## Affected boundaries

- `polynexus/core/saxs_engine/io.py`: path pattern candidate iteration.
- `tests/test_saxs_condition_recovery.py`: existing directory-source and
  metadata regressions.
- this task's design, plan, acceptance, and durable active-work memory.

## Implementation plan

1. Reproduce the directory-source and metadata regressions under an external
   basetemp and record the unresolved path result.
2. Iterate each path component for path-search patterns, continuing after
   conversion or validation rejects a candidate while preserving the existing
   first-valid pattern contract.
3. Run focused tests, the exact SAXS matrix, structured verification, diff and
   storage checks, then create the explicit allowlist checkpoint.

## Acceptance criteria

- [x] A valid later directory component wins after an invalid earlier match.
- [x] The recovered result reports `path_directory`, the pattern name, and
  confidence `0.72` without changing the label or condition value.
- [x] `scan_experiment_dir()` retains the recovered source metadata.
- [x] Context/header precedence and existing filename/legacy behavior remain
  unchanged.
- [x] TDD RED/GREEN, focused SAXS matrix, structured verification, diff, and
  storage dry-run evidence are recorded, followed by an explicit allowlist
  checkpoint.

## Verification commands

```powershell
$env:POLYNEXUS_TEST_ROOT='D:\PolyNexus_saxs_condition_path_recovery'
$env:PYTEST_ADDOPTS='-o addopts= --basetemp=D:\PolyNexus_saxs_condition_path_recovery_basetemp'
python -m pytest -q tests/test_saxs_condition_recovery.py
python -m pytest -q tests/test_saxs_*.py
python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-condition-path-candidate-recovery.md --changed --types
git diff --check
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24
```

No full/boundary result is attributed to this task unless a fresh command
returns a pytest summary and exit code `0`.

## Verification

The focused condition tests and the fresh sorted SAXS matrix returned exit code
`0`. The required structured command is:

`python scripts/verify.py --task docs/agent/tasks/2026-07-28-saxs-condition-path-candidate-recovery.md --changed --types`

Test-storage cleanup remains dry-run unless explicitly authorized; no real
datasets or source files are deleted.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/io.py`
- `docs/agent/tasks/2026-07-28-saxs-condition-path-candidate-recovery.md`
- `docs/superpowers/specs/2026-07-28-saxs-condition-path-candidate-recovery-design.md`
- `docs/superpowers/plans/2026-07-28-saxs-condition-path-candidate-recovery.md`
- `docs/acceptance/2026-07-28-saxs-condition-path-candidate-recovery.md`
- `docs/agent/memory/active-work.md`

Pre-existing tests, `current-state.md`, GUI/editor drafts, `.superpowers/`, and
external test-output directories remain outside this task.

## Verification evidence

- TDD RED: the two directory-source/metadata regressions reported
  `unresolved` under the pytest basetemp parent.
- Focused GREEN: `5 passed in 0.29s`.
- Exact sorted SAXS recheck: `518 passed, 6 warnings in 201.93s`, exit code
  `0`.
- Warnings were the existing Arial CJK glyph and SAXS geometry-header fallback
  warnings.
- `python scripts/verify.py --task ... --types` passed: Pyright reported `0`
  errors/warnings/informations; quality `287`, preprocessing `106`, compile,
  whitespace, task, and memory checks passed.
- The prescribed `--changed --types` command exited `1` on ten pre-existing
  Ruff findings in `io.py` (`E402`, `E741`, `F401`). A targeted Ruff run with
  those baseline rules ignored and `py_compile` both passed; no unrelated
  lint cleanup was added to this task.
- Storage report: `530` artifacts, `202` eligible, `328` protected, `0`
  removed. Cleanup dry-run: `0` removed; no `--apply` was run.

## Checkpoint

The explicit changed-file allowlist is the one above. Structured verification,
diff check, storage report/dry-run, and the local checkpoint are recorded in
the handoff. No push, merge, deployment, data deletion, or
scientific/publication approval is part of this task.
