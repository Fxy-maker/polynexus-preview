---
task_id: 2026-07-31-saxs-workbench-review-downstream-propagation
kind: cross-module-scientific-evidence
status: completed
date: 2026-07-31
title: Preserve SAXS Workbench scientific review through Figure/Manifest/Export
---

# SAXS Workbench Review Downstream Propagation

## Goal

Ensure a review saved on the current SAXS `AnalysisResult` is visible to newly
constructed Figure provenance, persisted Figure/Manifest documents, and SAXS
Export quality evidence through one source-linked, fail-closed adapter.

## Non-goals

- No SAXS calculation, quality grade, physical gate, threshold, rescue, AI,
  publication role, History write, or scientific decision change.
- No interpolation, frame repair, source inference, scope inference, or
  existing-file rewrite.
- No edits to real datasets, generated outputs, scratch directories, or
  parallel memory/worktree files.
- No `scripts/test_storage.py --apply`.

## Affected boundaries

- `polynexus/core/saxs_engine/figure_evidence.py`: read-only result-first
  review payload resolution used by Figure and Export consumers.
- `tests/test_saxs_figure_evidence_binding.py`: Figure recipe and persisted
  Manifest evidence regression.
- `tests/test_saxs_export_bundle.py`: Export quality evidence regression.
- This task's spec, plan, and acceptance note only.

## Acceptance criteria

- [x] A valid accepted review attached to current result metadata reaches a
  newly built Figure recipe with `reason == "review_accepted"`.
- [x] The same detached evidence reaches the persisted FigurePipeline
  document without changing publication role.
- [x] The same detached evidence reaches Export `quality_evidence.json`.
- [x] Config-only legacy callers continue to work.
- [x] Scope/source mismatch and non-accepted statuses remain fail-closed.
- [x] TDD RED is observed before production code; GREEN and structured
  verification have complete summaries and actual exit codes.
- [x] A single explicit allowlist checkpoint is created; parallel files remain
  untouched.

## Implementation plan

1. Add Figure/Manifest and Export regressions using result metadata with no
   config review field.
2. Run them and retain the expected RED failure.
3. Add the result-first/config-fallback resolver in the shared consumer
   adapter.
4. Run focused tests, the SAXS consumer matrix, structured verification, diff
   check, and storage report/clean dry-runs.
5. Review the disjoint diff and checkpoint only the explicit allowlist.

## Explicit changed-file allowlist

- `polynexus/core/saxs_engine/figure_evidence.py`
- `tests/test_saxs_figure_evidence_binding.py`
- `tests/test_saxs_export_bundle.py`
- `docs/superpowers/specs/2026-07-31-saxs-workbench-review-downstream-propagation-design.md`
- `docs/superpowers/plans/2026-07-31-saxs-workbench-review-downstream-propagation.md`
- `docs/agent/tasks/2026-07-31-saxs-workbench-review-downstream-propagation.md`
- `docs/acceptance/2026-07-31-saxs-workbench-review-downstream-propagation.md`

The existing parallel changes in `docs/agent/memory/`, `pytest.ini`,
`.superpowers/`, tests scratch, and D: test-storage directories are expressly
outside this checkpoint.

## Verification

The task verification commands are:

```powershell
python -m pytest -q tests/test_saxs_figure_evidence_binding.py tests/test_saxs_export_bundle.py tests/test_scientific_review_workbench.py tests/test_saxs_workbench_figure_contracts.py tests/test_saxs_figure_document.py -o addopts= --basetemp=D:\PolyNexus-test-runs\saxs-workbench-review-consumers-20260731
python scripts/verify.py --task docs/agent/tasks/2026-07-31-saxs-workbench-review-downstream-propagation.md --changed --types
python scripts/test_storage.py report --json
python scripts/test_storage.py clean --older-than-hours 24 --json
git diff --check
```

The RED/GREEN cycle and structured verifier are recorded below. A timeout,
setup error, crash, or pytest run without a complete summary is recorded as
incomplete rather than pass evidence.

## Evidence

- RED Figure: `2 failed, 31 deselected in 1.07s`, both new assertions failed
  because the config-only consumer omitted result metadata review.
- RED Export: `1 failed, 13 deselected in 0.32s`, the new assertion failed
  because `quality_evidence.json` omitted result metadata review.
- GREEN focused tests: `3 passed, 51 deselected in 2.73s` after preserving the
  explicit empty-config `review_missing` projection.
- Consumer regression: `86 passed, 4 warnings in 16.10s` before the resolver
  compatibility correction; final focused review/evidence slice is
  `71 passed in 9.95s` and includes the restored temperature/strain missing
  review behavior.
- Structured verifier with C: external `POLYNEXUS_TEST_ROOT`,
  `RUFF_CACHE_DIR`, and `PYTHONPYCACHEPREFIX`: exit code `0`; task/memory,
  Ruff, compile, type baseline, whitespace, quality `297 passed`, and
  preprocessing `106 passed` all passed. The same verifier first failed on D:
  cache/pyc writes with `OSError: [Errno 28] No space left on device`; that
  limitation was removed by using C: only for new verification artifacts.
- Fresh full SAXS matrix on C: had a complete summary of `4 failed, 652
  passed, 6 warnings in 444.43s`; the two review failures were the explicit
  empty-config compatibility case and were fixed afterward. The two remaining
  failures were pre-existing GUI confirmation routes unable to open the
  repository SampleDB because D: had zero free bytes (`sqlite3.OperationalError:
  disk I/O error`). This matrix is therefore not claimed as passed.
- Storage report/clean both exited `0` in `dry-run` mode. The final inventory
  reported `50` artifacts, `1,368,544,565` bytes, and `12` emergency-eligible
  entries (`7,873` emergency-eligible bytes while the parallel pytest process
  was active). No `--apply` was run and no directory was removed.
- `git diff --check` exited `0` during the structured verifier.
- The explicit seven-file allowlist checkpoint was created by
  `scripts/auto_commit.py`; the final amended commit hash is reported in the
  handoff.

## Known limitations

The current D: volume remains full and must be handled under the repository's
explicit storage policy before GUI routes that write the default SampleDB can
be re-run. No automatic cleanup was performed in this task. Human scientific
review and publication approval remain outside automated evidence transport.
